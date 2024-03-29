import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError, PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django.views.generic.edit import UpdateView, FormView
from sso.access_requests.forms import AccessRequestForm, send_user_request_extended_access, AccessRequestAcceptForm
from sso.accounts.models import User, Application
from sso.accounts.views.filter import UserSearchFilter2
from sso.auth.decorators import admin_login_required
from sso.oauth2.models import allowed_hosts
from sso.signals import user_admins, user_access_request
from sso.utils.http import get_request_param
from sso.utils.url import get_safe_redirect_uri, update_url
from sso.views import main
from sso.views.generic import ListView
from .filter import AccessRequestCountryFilter, AccessRequestAdminRegionFilter
from .models import AccessRequest
from ..utils.email import get_email_message
from ..views.sendmail import SendMailFormView

logger = logging.getLogger(__name__)


def get_user_admins(sender, organisations):
    # enable brand specific modification
    admins = set()
    user_admins.send_robust(sender=sender, organisations=organisations, admins=admins)
    return admins


def get_comment(admins):
    comments = []
    for admin in admins:
        admin_email = force_str(admin.primary_email())
        comments.append('<a href="mailto:{email}">{name}</a>'.format(email=admin_email, name=admin.get_full_name()))
    return 'Notified Admins: ' + ', '.join(comments)


class AccountExtendAccessAcceptView(FormView):
    form_class = AccessRequestAcceptForm
    success_url = reverse_lazy('access_requests:extend_access_list')
    template_name = 'access_requests/accessrequest_accept.html'

    @method_decorator(admin_login_required)
    @method_decorator(permission_required('accounts.change_user'))
    def dispatch(self, request, *args, **kwargs):
        self.access_request = get_object_or_404(AccessRequest, pk=self.kwargs['pk'])
        # check if admin has access to the specific user
        if not request.user.has_access_request_access(self.access_request):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['access_request'] = self.access_request
        context['has_user_access'] = self.request.user.has_user_access(self.access_request.user.uuid)
        return context

    def get(self, request, *args, **kwargs):
        default_profile = User.get_default_role_profile()
        if self.access_request.is_open and default_profile in self.access_request.user.role_profiles.all():
            msg = _('The user has already the profile "%(profile)s".') % {'profile': default_profile}
            messages.add_message(self.request, level=messages.ERROR, message=msg, fail_silently=True)

        return super().get(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['access_request'] = self.access_request
        return kwargs

    def form_valid(self, form):
        user = self.access_request.user
        action = self.request.POST.get('action')
        if action == 'deny-with-email':
            success_url = reverse('access_requests:process_access_request',
                                  kwargs={'pk': self.access_request.pk,
                                          'action': 'deny'}) + "?" + self.request.GET.urlencode()
            return HttpResponseRedirect(success_url)
        elif action == 'deny':
            self.access_request.process(action, user)
            return HttpResponseRedirect(reverse('access_requests:extend_access_list'))
        else:
            self.access_request.process('verify', user)
            # email user
            message, subject = get_email_message(user, self.request, self.request.user.primary_email(),
                                                 'access_requests/email/access_request_accepted_email.txt',
                                                 'access_requests/email/access_request_accepted_email_subject.txt')
            user.email_user(subject, message, reply_to=[self.request.user.primary_email().email])
            # display success message
            msg = _('Successfully extended access.')
            messages.add_message(self.request, level=messages.SUCCESS, message=msg, fail_silently=True)
            return HttpResponseRedirect(reverse('accounts:update_user', args=(user.uuid.hex,)))


class AccountExtendAccessDoneView(TemplateView):
    template_name = 'access_requests/extend_access_thanks.html'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        try:
            # doubleclick on submit can cause to 2 open AccessRequest
            return AccessRequest.open.filter(user=self.request.user).first()
        except ObjectDoesNotExist:
            return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        redirect_uri = get_safe_redirect_uri(self.request, allowed_hosts())
        object = self.get_object()

        if object is not None:
            context['object'] = object
        context['edit_uri'] = update_url(reverse('access_requests:extend_access'), {'redirect_uri': redirect_uri})
        context['redirect_uri'] = redirect_uri
        context['site_name'] = settings.SSO_SITE_NAME
        return context


def get_application_from_request(request):
    application_uuid = get_request_param(request, 'app_id')
    if application_uuid:
        try:
            return Application.objects.get_by_natural_key(application_uuid)
        except (ObjectDoesNotExist, ValidationError):
            pass
    return None


class AccountExtendAccessView(UpdateView):
    """
    like UpdateView, but
    - self.object is initialized from the current user
      so that add new and update is handled
    - redirect_uri is saved
    - form user is initialized with current user
    """
    model = AccessRequest
    form_class = AccessRequestForm

    def get_initial(self):
        initial = super().get_initial()
        if not self.object:
            initial['user'] = self.request.user
            initial['created'] = True
            application = get_application_from_request(self.request)
            if application:
                initial['application'] = application
            message = get_request_param(self.request, 'msg')
            if message:
                initial['message'] = message
        return initial

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        default_profile = User.get_default_role_profile()
        if (not self.object or self.object.is_open) and default_profile in self.request.user.role_profiles.all():
            msg = _('You have already the profile "%(profile)s".') % {'profile': default_profile}
            messages.add_message(self.request, level=messages.ERROR, message=msg, fail_silently=True)

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Insert the redirect_uri into the context dict.
        """
        context = {
            'redirect_uri': get_safe_redirect_uri(self.request, allowed_hosts())
        }

        user = self.request.user

        # enable brand specific modification
        if user.organisations.all():
            admins = get_user_admins(sender=self.__class__, organisations=user.organisations.all())
        else:
            admins = []
        context.update({'site_name': settings.SSO_SITE_NAME, 'admins': admins})

        context.update(kwargs)
        return super().get_context_data(**context)

    def cancel(self, request, *args, **kwargs):
        success_url = self.get_success_url()
        self.object.cancel(self.request.user)
        return HttpResponseRedirect(success_url)

    def get_object(self, queryset=None):
        try:
            # doubleclick on submit can cause to 2 open AccessRequest
            return AccessRequest.open.filter(user=self.request.user).first()
        except ObjectDoesNotExist:
            return None

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if '_cancel' in self.request.POST:
            return self.cancel(request, *args, **kwargs)
        else:
            return super().post(request, *args, **kwargs)

    def get_success_url(self):
        redirect_uri = get_safe_redirect_uri(self.request, allowed_hosts())
        return update_url(reverse('access_requests:extend_access_thanks'), {'redirect_uri': redirect_uri})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = self.request.user

        if form.cleaned_data['created'] or 'message' in form.changed_data or 'organisation' in form.changed_data:
            # check if the user selected a new organisation (if he did not have one before)
            if form.instance.organisation:
                organisations = [form.instance.organisation]
            else:
                organisations = user.organisations.all()
            # enable brand specific modification
            admins = get_user_admins(sender=self.__class__, organisations=organisations)
            form.instance.comment = get_comment(admins)
            response = super().form_valid(form)
            send_user_request_extended_access(admins, form.instance, form.instance.message)
            user_access_request.send_robust(sender=self.__class__, access_request=form.instance)
        else:
            response = super().form_valid(form)

        return response


class AccessRequestList(ListView):
    template_name = 'access_requests/access_requests_list.html'
    model = AccessRequest
    IS_ACTIVE_CHOICES = (('1', _('Active Users')), ('2', _('Inactive Users')))

    @property
    def list_display(self):
        return ['user', 'message', 'application', _('primary email'), 'last_modified', 'comment']

    @method_decorator(admin_login_required)
    @method_decorator(permission_required('accounts.change_user'))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user

        qs = AccessRequest.open.all()
        qs = user.filter_administrable_access_requests(qs)

        self.cl = main.ChangeList(self.request, self.model, self.list_display, default_ordering=['-last_modified'])
        # apply filters
        qs = UserSearchFilter2().apply(self, qs)
        qs = AccessRequestCountryFilter().apply(self, qs)
        qs = AccessRequestAdminRegionFilter().apply(self, qs)

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
        country_filter = AccessRequestCountryFilter().get(self, countries)

        admin_regions = user.get_administrable_user_regions()
        admin_region_filter = AccessRequestAdminRegionFilter().get(self, admin_regions)
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


def get_extended_access_denied_email_message(
        user, request, reply_to_email,
        email_template_name='access_requests/email/access_request_denied_email.txt',
        subject_template_name='access_requests/email/access_request_denied_subject.txt'):
    return get_email_message(user, request, reply_to_email, email_template_name, subject_template_name)


class AccessRequestSendMailFormView(SendMailFormView):
    email_messages = {
        'deny': get_extended_access_denied_email_message
    }
    action_breadcrumbs = {
        'deny': _("Deny extended access")
    }
    action_txts = {
        'deny': _("Deny extended access and send email")
    }
    model = AccessRequest
    success_url = reverse_lazy('access_requests:extend_access_list')
    template_name = 'access_requests/process_access_request.html'

    def get_cancel_url(self):
        return reverse_lazy('access_requests:extend_access_accept', args=[self.instance.pk])
