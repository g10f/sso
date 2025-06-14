import json
import logging
from datetime import timedelta
from functools import lru_cache
from urllib.parse import urlunsplit

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import permission_required, user_passes_test
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.db.models.expressions import F
from django.forms import inlineformset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.html import format_html
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _
from django.views.generic import DeleteView
from l10n.models import Country
from sso.accounts.email import send_account_created_email
from sso.accounts.forms import UserEmailForm, AppAdminUserProfileForm, CenterProfileForm
from sso.accounts.models import User, UserEmail, RoleProfile
from sso.auth.decorators import admin_login_required
from sso.forms.helpers import ChangedDataList, log_change, ErrorList, get_media_errors_and_active_form
from sso.oauth2.models import allowed_hosts
from sso.organisations.models import Organisation, is_validation_period_active
from sso.utils.url import get_safe_redirect_uri
from sso.views import main
from sso.views.generic import ListView
from sso.views.main import OrderByWithNulls
from .filter import AdminRegionFilter, ApplicationRoleFilter, CenterFilter, CountryFilter, IsActiveFilter, \
    RoleProfileFilter, UserSearchFilter

logger = logging.getLogger(__name__)


def get_usernotes_and_accessible_created_by_users(user, admin_user):
    usernote_set = user.usernote_set.all().order_by('-last_modified')
    # get the list of all users in the created_by_user field, to which the current user has
    # admin rights. If the current user has admin rights then a link to the user form is generated,
    # otherwise only the name is displayed
    created_by_user_pk_list = usernote_set.values_list('created_by_user__pk', flat=True)
    created_by_user_set = User.objects.filter(pk__in=created_by_user_pk_list).only('pk')
    accessible_created_by_users = admin_user.filter_administrable_users(created_by_user_set).only('pk')
    return usernote_set, accessible_created_by_users


class UserDeleteView(DeleteView):
    slug_field = slug_url_kwarg = 'uuid'
    model = get_user_model()
    success_url = reverse_lazy('accounts:user_list')

    @method_decorator(admin_login_required)
    @method_decorator(permission_required('accounts.delete_user', raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        # additionally check if the user is admin of the user
        if not request.user.has_user_access(kwargs.get('uuid')):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cancel_url'] = reverse('accounts:update_user', args=[self.object.uuid.hex])
        # the user is initialized from the ViewClass with the user to delete
        # so reinitialize it with the request user
        context['user'] = self.request.user
        return context


class LastLogin(object):
    verbose_name = _('last login')
    sortable = True
    ordering_field = OrderByWithNulls(F('last_login'))

    def __str__(self):
        return 'last_login'


class OrganisationField(object):
    verbose_name = _('organisation')
    sortable = True
    ordering_field = 'organisations'

    def __str__(self):
        return 'organisation'


class ValidUntil(object):
    verbose_name = _('valid until')
    sortable = True
    ordering_field = OrderByWithNulls(F('valid_until'))

    def __str__(self):
        return 'valid_until'

class UserList(ListView):
    template_name = 'accounts/application/user_list.html'
    model = get_user_model()
    IS_ACTIVE_CHOICES = (('1', _('Active Users')), ('2', _('Inactive Users')))

    @method_decorator(admin_login_required)
    @method_decorator(user_passes_test(lambda u: u.is_user_admin))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    @property
    def list_display(self):
        if settings.SSO_VALIDATION_PERIOD_IS_ACTIVE:
            return ['username', 'picture', 'last_name', _('primary email'), OrganisationField(), LastLogin(),
                    'date_joined', ValidUntil()]
        else:
            return ['username', 'picture', 'last_name', _('primary email'), OrganisationField(), LastLogin(),
                    'date_joined']

    def get_queryset(self):
        """
        Get the list of items for this view. This must be an iterable, and may
        be a queryset (in which qs-specific behavior will be enabled).
        """
        user = self.request.user

        qs = super().get_queryset().only('uuid', 'last_login', 'username', 'first_name', 'last_name',
                                         'date_joined', 'picture', 'valid_until') \
            .prefetch_related('useremail_set', 'organisations', 'role_profiles', 'application_roles')
        # exclude user who were not activated, this users must first be activated on the registration page
        qs = qs.exclude(registrationprofile__isnull=False, last_login__isnull=True, is_active=False)
        qs = user.filter_administrable_users(qs)

        self.cl = main.ChangeList(self.request, self.model, self.list_display,
                                  default_ordering=[OrderByWithNulls(F('last_login'), descending=True)])
        # apply filters
        qs = UserSearchFilter().apply(self, qs)
        qs = CountryFilter().apply(self, qs)
        qs = AdminRegionFilter().apply(self, qs)
        qs = CenterFilter().apply(self, qs)
        qs = ApplicationRoleFilter().apply(self, qs)
        qs = RoleProfileFilter().apply(self, qs)
        qs = IsActiveFilter().apply(self, qs)

        # Set ordering.
        ordering = self.cl.get_ordering(self.request, qs)
        qs = qs.order_by(*ordering).distinct()
        return qs

    def get_filters(self):
        user = self.request.user
        # .filter(organisation__user__isnull=False) causes performance degration
        user_countries = user.get_administrable_user_countries()
        countries = [user_country.country for user_country in user_countries]
        country_filter = CountryFilter().get(self, countries)

        application_roles = user.get_administrable_application_roles()
        role_profiles = user.get_administrable_role_profiles()
        admin_regions = user.get_administrable_user_regions()

        if self.country:
            centers = user.get_administrable_user_organisations().filter(
                organisation_country__country=self.country)
            admin_regions = admin_regions.filter(organisation_country__country=self.country)
        else:
            centers = user.get_administrable_user_organisations()

        if self.admin_region:
            centers = centers.filter(admin_region=self.admin_region)

        if self.center:
            application_roles = application_roles.filter(user__organisations__in=[self.center]).distinct()
            role_profiles = role_profiles.filter(user__organisations__in=[self.center]).distinct()
        else:
            if self.country or self.admin_region:
                # when there is no center selected
                # only filter roles and profiles by center if at least country or region is selected
                application_roles = application_roles.filter(user__organisations__in=centers).distinct()
                role_profiles = role_profiles.filter(user__organisations__in=centers).distinct()

        admin_region_filter = AdminRegionFilter().get(self, admin_regions)
        center_filter = CenterFilter().get(self, centers)
        application_role_filter = ApplicationRoleFilter().get(self, application_roles)
        role_profile_filter = RoleProfileFilter().get(self, role_profiles)

        filters = []
        if len(countries) > 1:
            filters += [country_filter]
        if len(admin_regions) > 1:
            filters += [admin_region_filter]
        if len(centers) > 1:
            filters += [center_filter]

        filters += [role_profile_filter, application_role_filter]
        if user.is_user_admin:
            filters += [IsActiveFilter().get(self)]
        cache_dict = {
            "user": user.id,
            "q": self.request.GET.get(main.SEARCH_VAR, ''),
            "country": "" if self.country is None else self.country.id,
            "admin_region": "" if self.admin_region is None else self.admin_region.id,
            "center": "" if self.center is None else self.center.id,
            "role_profile": "" if self.role_profile is None else self.role_profile.id,
            "app_role": "" if self.app_role is None else self.app_role.id,
            "is_active": "" if self.is_active is None else self.is_active.pk,
        }
        filters_cache_key = hash(json.dumps(cache_dict, sort_keys=True))
        return filters, filters_cache_key

    def get_context_data(self, **kwargs):
        headers = list(self.cl.result_headers())
        num_sorted_fields = 0
        for h in headers:
            if h['sortable'] and h['sorted']:
                num_sorted_fields += 1

        filters, filters_cache_key = self.get_filters()

        context = {
            'result_headers': headers,
            'num_sorted_fields': num_sorted_fields,
            'search_var': main.SEARCH_VAR,
            'page_var': main.PAGE_VAR,
            'query': self.request.GET.get(main.SEARCH_VAR, ''),
            'cl': self.cl,
            'filters': filters,
            'filters_cache_key': filters_cache_key,
            'is_active': self.is_active,
            'sso_validation_period_is_active': settings.SSO_VALIDATION_PERIOD_IS_ACTIVE
        }
        context.update(kwargs)
        return super().get_context_data(**context)


class AppAdminUserList(ListView):
    template_name = 'accounts/application/app_admin_user_list.html'
    model = get_user_model()

    @method_decorator(admin_login_required)
    @method_decorator(user_passes_test(lambda u: u.is_app_user_admin()))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    @property
    def list_display(self):
        return ['username', 'picture', 'last_name', _('primary email'), OrganisationField(), LastLogin(),
                'date_joined']

    def get_queryset(self):
        """
        Get the list of items for this view. This must be an iterable, and may
        be a queryset (in which qs-specific behavior will be enabled).
        """
        user = self.request.user

        qs = super().get_queryset().only('uuid', 'last_login', 'username', 'first_name',
                                         'last_name', 'date_joined',
                                         'picture', 'valid_until') \
            .prefetch_related('useremail_set', 'organisations')
        qs = user.filter_administrable_app_admin_users(qs)

        self.cl = main.ChangeList(self.request, self.model, self.list_display,
                                  default_ordering=[OrderByWithNulls(F('last_login'), descending=True)])
        # apply filters
        qs = UserSearchFilter().apply(self, qs)
        qs = CountryFilter().apply(self, qs)
        qs = AdminRegionFilter().apply(self, qs)
        qs = CenterFilter().apply(self, qs)
        qs = ApplicationRoleFilter().apply(self, qs)
        qs = RoleProfileFilter().apply(self, qs)
        qs = IsActiveFilter().apply(self, qs)

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

        user_countries = user.get_administrable_app_admin_user_countries()  # .filter(organisation__user__isnull=False)
        countries = Country.objects.filter(organisationcountry__in=user_countries)
        country_filter = CountryFilter().get(self, countries)

        centers = Organisation.objects.none()
        application_roles = user.get_administrable_app_admin_application_roles()
        role_profiles = user.get_administrable_app_admin_role_profiles()
        admin_regions = user.get_administrable_app_admin_user_regions()

        if self.country:
            centers = user.get_administrable_app_admin_user_organisations().filter(
                organisation_country__country=self.country)
            if self.admin_region:
                centers = centers.filter(admin_region=self.admin_region)
            if self.center:
                application_roles = application_roles.filter(user__organisations__in=[self.center]).distinct()
                role_profiles = role_profiles.filter(user__organisations__in=[self.center]).distinct()
            else:
                application_roles = application_roles.filter(user__organisations__in=centers).distinct()
                role_profiles = role_profiles.filter(user__organisations__in=centers).distinct()

        admin_region_filter = AdminRegionFilter().get(self, admin_regions)
        center_filter = CenterFilter().get(self, centers)
        application_role_filter = ApplicationRoleFilter().get(self, application_roles)
        role_profile_filter = RoleProfileFilter().get(self, role_profiles)

        filters = [country_filter, admin_region_filter, center_filter, role_profile_filter, application_role_filter]

        context = {
            'result_headers': headers,
            'num_sorted_fields': num_sorted_fields,
            'search_var': main.SEARCH_VAR,
            'page_var': main.PAGE_VAR,
            'query': self.request.GET.get(main.SEARCH_VAR, ''),
            'cl': self.cl,
            'filters': filters
        }
        context.update(kwargs)
        return super().get_context_data(**context)


@lru_cache()
def get_default_admin_update_user_form_class():
    admin_update_user_form_class = import_string(settings.SSO_ADMIN_UPDATE_USER_FORM)
    return admin_update_user_form_class


@lru_cache()
def get_default_admin_add_user_form_class():
    admin_add_user_form_class = import_string(settings.SSO_ADMIN_ADD_USER_FORM)
    return admin_add_user_form_class


@lru_cache()
def get_default_user_self_registration_form_class():
    user_self_registration_form_class = import_string(settings.SSO_SELF_REGISTRATION_FORM)
    return user_self_registration_form_class


@admin_login_required
@permission_required('accounts.add_user', raise_exception=True)
def add_user(request, template='accounts/application/add_user_form.html'):
    redirect_uri = get_safe_redirect_uri(request, allowed_hosts())
    if request.method == 'POST':
        form = get_default_admin_add_user_form_class()(request, request.POST)
        if form.is_valid():
            user = form.save()
            send_account_created_email(user, request)
            if redirect_uri:
                success_url = redirect_uri
            else:
                success_url = urlunsplit(('', '', reverse('accounts:add_user_done', args=[user.uuid.hex]),
                                          request.GET.urlencode(safe='/'), ''))
            return HttpResponseRedirect(success_url)
    else:
        initial = {}
        default_role_profile = User.get_default_role_profile()
        if default_role_profile:
            initial['role_profiles'] = [default_role_profile.id]
        organisations = request.user.get_administrable_user_organisations()
        if len(organisations) == 1:
            initial['organisations'] = organisations[0]
        form = get_default_admin_add_user_form_class()(request, initial=initial)

    data = {'form': form, 'redirect_uri': redirect_uri, 'title': _('Add user')}
    return render(request, template, data)


@admin_login_required
@permission_required('accounts.add_user', raise_exception=True)
def add_user_done(request, uuid, template='accounts/application/add_user_done.html'):
    new_user = get_user_model().objects.get(uuid=uuid)
    redirect_uri = get_safe_redirect_uri(request, allowed_hosts())
    data = {'new_user': new_user, 'redirect_uri': redirect_uri, 'title': _('Add user')}
    return render(request, template, data)


def _update_standard_user(request, user, template='accounts/application/update_user_form.html'):
    if user.useremail_set.count() == 0:
        useremail_extra = 1
    else:
        useremail_extra = 0

    UserEmailInlineFormSet = inlineformset_factory(User, UserEmail, UserEmailForm, extra=useremail_extra,
                                                   max_num=UserEmail.MAX_EMAIL_ADRESSES)

    if request.method == 'POST':
        form = get_default_admin_update_user_form_class()(request.POST, instance=user, request=request)
        user_email_inline_formset = UserEmailInlineFormSet(request.POST, instance=user)

        if form.is_valid() and user_email_inline_formset.is_valid():
            formsets = [user_email_inline_formset]
            changed_data_list = ChangedDataList(form, formsets)

            activate = None
            if "_deactivate" in request.POST:
                activate = False
                changed_data_list.append("deactivated")
            elif "_activate" in request.POST:
                activate = True
                changed_data_list.append("activated")

            remove_org = "_remove_org" in request.POST
            if remove_org:
                changed_data_list.append("\"removed from organisation\"")
            extend_validity = "_extend_validity" in request.POST
            if extend_validity:
                changed_data_list.append("\"extended validity\"")

            make_member = "_make_member" in request.POST
            if extend_validity:
                changed_data_list.append("\"made to member\"")

            user = form.save(extend_validity, activate=activate, remove_org=remove_org, make_member=make_member)
            user_email_inline_formset.save()

            if not user.useremail_set.exists():
                msg = _('The account %(username)s has no email address!') % {'username': force_str(user)}
                messages.add_message(request, level=messages.ERROR, message=msg, fail_silently=True)
            else:
                user.ensure_single_primary_email()

            change_message = changed_data_list.change_message()
            log_change(request, user, change_message)

            msg_dict = {'name': force_str(get_user_model()._meta.verbose_name), 'obj': force_str(user)}
            msg = ''
            success_url = reverse('accounts:user_list') + "?" + request.GET.urlencode()
            if "_addanother" in request.POST:
                msg = format_html(_('The {name} "{obj}" was saved successfully. You may add another {name} below.'), **msg_dict)
                success_url = reverse('accounts:add_user')
            elif "_continue" in request.POST:
                msg = format_html(_('The {name} "{obj}" was saved successfully. You may edit it again below.'), **msg_dict)
                success_url = reverse('accounts:update_user', args=[user.uuid.hex])
            elif "_resend_invitation" in request.POST:
                send_account_created_email(user, request)
                msg = _('The %(name)s "%(obj)s" was saved successfully and the invitation email was resend.') % msg_dict
                success_url = reverse('accounts:update_user', args=[user.uuid.hex])
            elif "_deactivate" in request.POST:
                success_url = reverse('accounts:update_user', args=[user.uuid.hex])
            elif "_activate" in request.POST:
                msg = _('The %(name)s "%(obj)s" was activated successfully.') % msg_dict
                success_url = reverse('accounts:update_user', args=[user.uuid.hex])
            elif "_remove_org" in request.POST:
                msg = _('The %(name)s "%(obj)s" was removed from the organisation successfully.') % msg_dict
            elif "disable_otp" in request.POST:
                if not request.user.has_perm("accounts.reset_user_2fa"):
                    raise PermissionDenied
                user.sso_auth_profile.is_otp_enabled = False
                user.sso_auth_profile.save()
                msg = format_html(_('For {name} "{obj}" 2fa was disabled.'), **msg_dict)
            else:
                msg = format_html(_('The {name} "{obj}" was saved successfully.'), **msg_dict)
            if msg:
                messages.add_message(request, level=messages.SUCCESS, message=msg, fail_silently=True)
            return HttpResponseRedirect(success_url)

    else:
        user_email_inline_formset = UserEmailInlineFormSet(instance=user)
        form = get_default_admin_update_user_form_class()(instance=user, request=request)

    formsets = [user_email_inline_formset]

    media, errors, active = get_media_errors_and_active_form(form, formsets)

    user_email_inline_formset.forms += [user_email_inline_formset.empty_form]

    if (user.last_login is None) or (user.last_login - user.date_joined) < timedelta(seconds=1):
        logged_in = False
    else:
        logged_in = True
    try:
        user_organisation = user.organisations.first()
    except ObjectDoesNotExist:
        user_organisation = None

    usernote_set, accessible_created_by_users = get_usernotes_and_accessible_created_by_users(user, request.user)

    context = {'form': form, 'errors': errors, 'formsets': formsets, 'media': media, 'active': active,
               'usernotes': usernote_set,
               'editable_created_by_users': accessible_created_by_users,
               'logged_in': logged_in, 'is_validation_period_active': is_validation_period_active(user_organisation),
               'title': _('Change user')}
    return render(request, template, context)


def _update_center_account(request, user, template='accounts/application/update_center_form.html'):
    if request.method == 'POST':
        form = CenterProfileForm(request.POST, instance=user, request=request)

        if form.is_valid():
            activate = None
            if "_deactivate" in request.POST:
                activate = False
            elif "_activate" in request.POST:
                activate = True
            user = form.save(activate=activate)

            change_message = ChangedDataList(form, []).change_message()
            log_change(request, user, change_message)

            msg_dict = {'name': force_str(get_user_model()._meta.verbose_name), 'obj': force_str(user)}
            msg = ''
            success_url = reverse('accounts:user_list') + "?" + request.GET.urlencode()
            if "_addanother" in request.POST:
                msg = format_html(_('The {name} "{obj}" was saved successfully. You may add another {name} below.'), **msg_dict)
                success_url = reverse('accounts:add_user')
            elif "_continue" in request.POST:
                msg = format_html(_('The {name} "{obj}" was saved successfully. You may edit it again below.'), **msg_dict)
                success_url = reverse('accounts:update_user', args=[user.uuid.hex])
            elif "_deactivate" in request.POST:
                success_url = reverse('accounts:update_user', args=[user.uuid.hex])
            elif "_activate" in request.POST:
                msg = _('The %(name)s "%(obj)s" was activated successfully.') % msg_dict
                success_url = reverse('accounts:update_user', args=[user.uuid.hex])
            elif "disable_otp" in request.POST:
                if not request.user.has_perm("accounts.reset_user_2fa"):
                    raise PermissionDenied
                user.sso_auth_profile.is_otp_enabled = False
                user.sso_auth_profile.save()
                msg = format_html(_('For {name} "{obj}" 2fa was disabled.'), **msg_dict)
            else:
                msg = format_html(_('The {name} "{obj}" was saved successfully.'), **msg_dict)
            if msg:
                messages.add_message(request, level=messages.SUCCESS, message=msg, fail_silently=True)
            return HttpResponseRedirect(success_url)

    else:
        form = CenterProfileForm(instance=user, request=request)

    media, errors, active = get_media_errors_and_active_form(form)

    if (user.last_login is None) or (user.last_login - user.date_joined) < timedelta(seconds=1):
        logged_in = False
    else:
        logged_in = True

    usernote_set, accessible_created_by_users = get_usernotes_and_accessible_created_by_users(user, request.user)

    context = {'form': form, 'media': media, 'errors': errors, 'active': active,
               'usernotes': usernote_set,
               'editable_created_by_users': accessible_created_by_users,
               'logged_in': logged_in, 'title': _('Change user')}
    return render(request, template, context)


@admin_login_required
@user_passes_test(lambda u: u.is_user_admin)
@permission_required('accounts.change_user', raise_exception=True)
def update_user(request, uuid):
    if not request.user.has_user_access(uuid):
        raise PermissionDenied
    user = get_object_or_404(get_user_model(), uuid=uuid)

    # we use different forms for different kind of users
    if getattr(user, 'is_center', True):
        return _update_center_account(request, user)
    else:
        return _update_standard_user(request, user)


@admin_login_required
@user_passes_test(lambda u: u.is_app_user_admin())
def app_admin_update_user(request, uuid, template='accounts/application/app_admin_update_user_form.html'):
    if not request.user.has_app_admin_user_access(uuid):
        raise PermissionDenied
    user = get_object_or_404(get_user_model(), uuid=uuid)

    if request.method == 'POST':
        form = AppAdminUserProfileForm(request.POST, instance=user, request=request)

        if form.is_valid():
            user = form.save()

            change_message = ChangedDataList(form, []).change_message()
            log_change(request, user, change_message)

            msg_dict = {'name': force_str(get_user_model()._meta.verbose_name), 'obj': force_str(user)}
            if "_continue" in request.POST:
                msg = format_html(_('The {name} "{obj}" was saved successfully. You may edit it again below.'),
                                  **msg_dict)
                success_url = reverse('accounts:app_admin_update_user', args=[user.uuid.hex])
            else:
                msg = format_html(_('The {name} "{obj}" was saved successfully.'), **msg_dict)
                success_url = reverse('accounts:app_admin_user_list') + "?" + request.GET.urlencode()
            messages.add_message(request, level=messages.SUCCESS, message=msg, fail_silently=True)
            return HttpResponseRedirect(success_url)

    else:
        form = AppAdminUserProfileForm(instance=user, request=request)

    media = form.media
    errors = ErrorList(form, [])

    context = {'form': form, 'errors': errors, 'media': media, 'title': _('Change user roles')}
    return render(request, template, context)


class RoleProfileListView(ListView):
    template_name = 'accounts/application/roleprofile_list.html'
    model = RoleProfile

    @property
    def list_display(self):
        return ['name', 'order']

    @method_decorator(admin_login_required)
    @method_decorator(user_passes_test(lambda u: u.is_user_admin or u.is_app_user_admin()))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        self.cl = main.ChangeList(self.request, self.model, self.list_display,
                                  default_ordering=[OrderByWithNulls(F('order'), descending=True)])
        qs = self.request.user.get_administrable_role_profiles()
        # Set ordering.
        ordering = self.cl.get_ordering(self.request, qs)
        qs = qs.order_by(*ordering).distinct()
        return qs

    def get_context_data(self, **kwargs):
        headers = list(self.cl.result_headers())
        num_sorted_fields = 0
        for h in headers:
            if h['sortable'] and h['sorted']:
                num_sorted_fields += 1

        context = {
            'result_headers': headers,
            'num_sorted_fields': num_sorted_fields,
            'cl': self.cl,
        }
        context.update(kwargs)
        return super().get_context_data(**context)
