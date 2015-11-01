# -*- coding: utf-8 -*-
import logging
from django.utils.six.moves.urllib.parse import urlunsplit

from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.http import HttpResponseRedirect
from django.views.generic import DetailView, FormView
from django.utils.decorators import method_decorator
from django.core.urlresolvers import reverse, reverse_lazy
from django.views.generic.detail import SingleObjectTemplateResponseMixin
from django.views.generic.edit import ProcessFormView, ModelFormMixin
from sso.accounts.forms import OrganisationChangeForm, OrganisationChangeAcceptForm
from sso.accounts.models import OrganisationChange, ApplicationRole
from sso.accounts.views.filter import OrganisationChangeCountryFilter, OrganisationChangeAdminRegionFilter
from sso.auth.decorators import admin_login_required
from sso.oauth2.models import allowed_hosts
from sso.organisations.models import is_validation_period_active
from sso.utils.url import get_safe_redirect_uri
from sso.views import main
from sso.views.generic import ListView, SearchFilter

logger = logging.getLogger(__name__)


class OrganisationChangeDetailView(DetailView):
    model = OrganisationChange

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.user != self.request.user:
            raise PermissionDenied
        return super(OrganisationChangeDetailView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Insert the redirect_uri into the context dict.
        """
        context = {}
        redirect_uri = get_safe_redirect_uri(self.request, allowed_hosts())
        if redirect_uri:
            context['redirect_uri'] = redirect_uri

        update_url = urlunsplit(('', '', reverse('accounts:organisationchange_me'), self.request.GET.urlencode(safe='/'), ''))
        context['update_url'] = update_url

        context.update(kwargs)
        return super(OrganisationChangeDetailView, self).get_context_data(**context)


class OrganisationChangeUpdateView(SingleObjectTemplateResponseMixin, ModelFormMixin, ProcessFormView):
    """
    like BaseUpdateView, but
    - self.object is initialized from the current user (self.request.user.organisationchange) so that add new and update is handled
    - redirect_uri is saved
    - form user is initialized with current user is
    """
    model = OrganisationChange
    form_class = OrganisationChangeForm
    template_name_suffix = '_form'

    def get_initial(self):
        initial = super(OrganisationChangeUpdateView, self).get_initial()
        initial['user'] = self.request.user
        return initial

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(OrganisationChangeUpdateView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Insert the redirect_uri into the context dict.
        """
        context = {}
        redirect_uri = get_safe_redirect_uri(self.request, allowed_hosts())
        if redirect_uri:
            context['redirect_uri'] = redirect_uri

        context.update(kwargs)
        return super(OrganisationChangeUpdateView, self).get_context_data(**context)

    def delete(self, request, *args, **kwargs):
        success_url = self.get_success_url()
        self.object.delete()
        return HttpResponseRedirect(success_url)

    def get_object(self, queryset=None):
        try:
            return self.request.user.organisationchange
        except ObjectDoesNotExist:
            return None

    def get(self, request, *args, **kwargs):
        self.object = self.object = self.get_object()
        return super(OrganisationChangeUpdateView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.object = self.get_object()
        if '_delete' in self.request.POST:
            return self.delete(request, *args, **kwargs)
        else:
            return super(OrganisationChangeUpdateView, self).post(request, *args, **kwargs)

    def get_success_url(self):
        success_url = ''
        if '_continue' in self.request.POST:
            success_url = self.request.path
        elif '_delete' in self.request.POST:
            success_url = reverse('accounts:profile')
        else:
            if is_validation_period_active(self.object.organisation):
                success_url = reverse('accounts:organisationchange_detail', args=[self.object.pk])
            else:
                success_url = reverse('accounts:profile')

        # save exiting get parameters (i.e. redirect_uri)
        return urlunsplit(('', '', success_url, self.request.GET.urlencode(safe='/'), ''))

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super(OrganisationChangeUpdateView, self).form_valid(form)


class OrganisationChangeAcceptView(FormView):
    form_class = OrganisationChangeAcceptForm
    success_url = reverse_lazy('accounts:organisationchange_list')
    template_name = 'accounts/organisationchange_accept.html'

    @method_decorator(admin_login_required)
    @method_decorator(permission_required('accounts.change_user'))
    def dispatch(self, request, *args, **kwargs):
        self.organisationchange = get_object_or_404(OrganisationChange, pk=self.kwargs['pk'])
        return super(OrganisationChangeAcceptView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(OrganisationChangeAcceptView, self).get_context_data(**kwargs)
        context['organisationchange'] = self.organisationchange
        return context

    def form_valid(self, form):
        if '_delete' in self.request.POST:
            self.organisationchange.delete()
            msg = _('Denied organisation change.')
            messages.add_message(self.request, level=messages.WARNING, message=msg, fail_silently=True)
            return HttpResponseRedirect(self.get_success_url())
        else:
            user = self.organisationchange.user
            user.organisations = [self.organisationchange.organisation]
            user.save()
            self.organisationchange.delete()

            # remove user related permissions
            organisation_related_application_roles = ApplicationRole.objects.filter(is_organisation_related=True)
            user.application_roles.remove(*list(organisation_related_application_roles))

            msg = _('Successfully changed the organisation.')
            messages.add_message(self.request, level=messages.SUCCESS, message=msg, fail_silently=True)
            return HttpResponseRedirect(reverse('accounts:update_user', args=(user.uuid.hex,)))


class UserSearchFilter(SearchFilter):
    search_names = ['user__username__icontains', 'user__first_name__icontains', 'user__last_name__icontains', 'user__useremail__email__icontains']


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
        return ['user', FromOrganisationHeader(), ToOrganisationHeader(), 'reason', _('primary email'), 'last_modified']

    @method_decorator(admin_login_required)
    @method_decorator(permission_required('accounts.change_user'))
    def dispatch(self, request, *args, **kwargs):
        return super(OrganisationChangeList, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user

        qs = super(OrganisationChangeList, self).get_queryset().prefetch_related('user__useremail_set', 'organisation__country')
        qs = user.filter_administrable_organisationchanges(qs)

        self.cl = main.ChangeList(self.request, self.model, self.list_display, default_ordering=['-last_modified'])
        # apply filters
        qs = UserSearchFilter().apply(self, qs)
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
        filters = []
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
        return super(OrganisationChangeList, self).get_context_data(**context)
