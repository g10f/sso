import logging
from urllib.parse import urlunsplit

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template import loader
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, FormView
from django.views.generic.detail import SingleObjectTemplateResponseMixin
from django.views.generic.edit import ProcessFormView, ModelFormMixin
from sso.access_requests.views import get_user_admins
from sso.accounts.forms import OrganisationChangeForm, OrganisationChangeAcceptForm
from sso.accounts.models import OrganisationChange
from sso.accounts.views.filter import OrganisationChangeCountryFilter, OrganisationChangeAdminRegionFilter, \
    UserSearchFilter2
from sso.auth.decorators import admin_login_required
from sso.oauth2.models import allowed_hosts
from sso.organisations.models import is_validation_period_active
from sso.signals import user_organisation_change_request
from sso.utils.url import get_safe_redirect_uri
from sso.views import main
from sso.views.generic import ListView

logger = logging.getLogger(__name__)


class OrganisationChangeDetailView(DetailView):
    model = OrganisationChange

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.user != self.request.user:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Insert the redirect_uri into the context dict.
        """
        context = {}
        redirect_uri = get_safe_redirect_uri(self.request, allowed_hosts())
        if redirect_uri:
            context['redirect_uri'] = redirect_uri

        update_url = urlunsplit(
            ('', '', reverse('accounts:organisationchange_me'), self.request.GET.urlencode(safe='/'), ''))
        context['update_url'] = update_url

        # enable brand specific modification
        admins = get_user_admins(sender=self.__class__, organisations=[self.object.organisation])
        context.update({'site_name': settings.SSO_SITE_NAME, 'admins': admins})

        context.update(kwargs)
        return super().get_context_data(**context)


class OrganisationChangeUpdateView(SingleObjectTemplateResponseMixin, ModelFormMixin, ProcessFormView):
    """
    like BaseUpdateView, but
    - self.object is initialized from the current user (self.request.user.organisationchange)
      so that add new and update is handled
    - redirect_uri is saved
    - form user is initialized with current user
    """
    model = OrganisationChange
    form_class = OrganisationChangeForm
    template_name_suffix = '_form'

    def get_initial(self):
        initial = super().get_initial()
        initial['user'] = self.request.user
        return initial

    @method_decorator(login_required)
    @method_decorator(user_passes_test(lambda u: not u.is_center))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Insert the redirect_uri into the context dict.
        """
        context = {}
        redirect_uri = get_safe_redirect_uri(self.request, allowed_hosts())
        if redirect_uri:
            context['redirect_uri'] = redirect_uri

        context.update(kwargs)
        return super().get_context_data(**context)

    def cancel(self, request, *args, **kwargs):
        success_url = self.get_success_url()
        self.object.cancel(self.request.user)
        return HttpResponseRedirect(success_url)

    def get_object(self, queryset=None):
        try:
            return OrganisationChange.open.get(user=self.request.user)
        except ObjectDoesNotExist:
            return None

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if '_cancel' in self.request.POST:
            return self.cancel(request, *args, **kwargs)
        else:
            return super().post(request, *args, **kwargs)

    def get_success_url(self):
        if '_continue' in self.request.POST:
            success_url = self.request.path
        elif '_cancel' in self.request.POST:
            success_url = reverse('accounts:profile')
        else:
            if is_validation_period_active(self.object.organisation):
                success_url = reverse('accounts:organisationchange_detail', args=[self.object.pk])
            else:
                success_url = reverse('accounts:profile')

        # save exiting get parameters (i.e. redirect_uri)
        return urlunsplit(('', '', success_url, self.request.GET.urlencode(safe='/'), ''))

    def form_valid(self, form):
        user = self.request.user
        form.instance.user = user
        form.instance.original_organisation = user.organisations.first()

        response = super().form_valid(form)
        if 'organisation' in form.changed_data:
            # enable brand specific modification
            user_organisation_change_request.send_robust(sender=self.__class__, organisation_change=form.instance)

        return response


class OrganisationChangeAcceptView(FormView):
    form_class = OrganisationChangeAcceptForm
    success_url = reverse_lazy('accounts:organisationchange_list')
    template_name = 'accounts/organisationchange_accept.html'

    @method_decorator(admin_login_required)
    @method_decorator(permission_required('accounts.change_user'))
    def dispatch(self, request, *args, **kwargs):
        self.organisationchange = get_object_or_404(OrganisationChange, pk=self.kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organisationchange'] = self.organisationchange
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organisationchange'] = self.organisationchange
        return kwargs

    def form_valid(self, form):
        if '_delete' in self.request.POST:
            self.organisationchange.deny(self.request.user)
            msg = _('Denied organisation change.')
            messages.add_message(self.request, level=messages.WARNING, message=msg, fail_silently=True)
            return HttpResponseRedirect(self.get_success_url())
        else:
            self.organisationchange.verify(self.request.user)
            user = self.organisationchange.user
            # email user
            site_name = settings.SSO_SITE_NAME
            domain = settings.SSO_DOMAIN
            use_https = settings.SSO_USE_HTTPS
            c = {
                'site_name': site_name,
                'protocol': use_https and 'https' or 'http',
                'domain': domain,
                'first_name': user.get_full_name(),
                'organisation_name': self.organisationchange.organisation,
                'organisation_admin': self.request.user.get_full_name(),
            }
            subject = loader.render_to_string('accounts/email/organisationchange_accepted_email_subject.txt', c)
            # Email subject *must not* contain newlines
            subject = ''.join(subject.splitlines())
            message = loader.render_to_string('accounts/email/organisationchange_accepted_email.txt', c)
            html_message = None  # loader.render_to_string(html_email_template_name, c)
            user.email_user(subject, message, reply_to=['self.request.user.primary_email()'],
                            html_message=html_message)

            # display success message
            msg = _('Successfully changed the organisation.')
            messages.add_message(self.request, level=messages.SUCCESS, message=msg, fail_silently=True)
            return HttpResponseRedirect(reverse('accounts:update_user', args=(user.uuid.hex,)))


class ToOrganisationHeader(object):
    verbose_name = _('to organisation')
    sortable = True
    ordering_field = 'organisation'


class FromOrganisationHeader(object):
    verbose_name = _('from organisation')
    sortable = True
    ordering_field = 'user__organisations'


class OrganisationChangeList(ListView):
    template_name = 'accounts/organisationchange_list.html'
    model = OrganisationChange
    IS_ACTIVE_CHOICES = (('1', _('Active Users')), ('2', _('Inactive Users')))

    @property
    def list_display(self):
        return ['user', FromOrganisationHeader(), ToOrganisationHeader(), 'message', _('primary email'),
                'last_modified', 'comment']

    @method_decorator(admin_login_required)
    @method_decorator(permission_required('accounts.change_user'))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user

        qs = OrganisationChange.open.all()
        qs = user.filter_administrable_organisationchanges(qs)

        self.cl = main.ChangeList(self.request, self.model, self.list_display, default_ordering=['-last_modified'])
        # apply filters
        qs = UserSearchFilter2().apply(self, qs)
        qs = OrganisationChangeCountryFilter().apply(self, qs)
        qs = OrganisationChangeAdminRegionFilter().apply(self, qs)

        # Set ordering.
        ordering = self.cl.get_ordering(self.request, qs)
        qs = qs.order_by(*ordering).distinct()
        return qs

    def get_context_data(self, **kwargs):
        user = self.request.user
        headers = list(self.cl.result_headers())
        num_sorted_fields = 0
        for h in headers:
            if h['sortable'] and h['sorted']:
                num_sorted_fields += 1

        countries = user.get_administrable_user_countries()
        country_filter = OrganisationChangeCountryFilter().get(self, countries)

        admin_regions = user.get_administrable_user_regions()
        admin_region_filter = OrganisationChangeAdminRegionFilter().get(self, admin_regions)
        filters = [country_filter, admin_region_filter]

        context = {
            'result_headers': headers,
            'num_sorted_fields': num_sorted_fields,
            'search_var': main.SEARCH_VAR,
            'page_var': main.PAGE_VAR,
            'query': self.request.GET.get(main.SEARCH_VAR, ''),
            'cl': self.cl,
            'filters': filters,
        }
        context.update(kwargs)
        return super().get_context_data(**context)
