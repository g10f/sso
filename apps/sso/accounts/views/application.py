# -*- coding: utf-8 -*-
from datetime import timedelta
import logging
from django.utils.six.moves.urllib.parse import urlunsplit

from django.db.models.expressions import F
from django.conf import settings
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.forms import inlineformset_factory
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse, reverse_lazy
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import permission_required, user_passes_test
from django.views.generic import DeleteView
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import get_object_or_404
from django.utils.encoding import force_text
from sso.oauth2.models import allowed_hosts
from sso.auth.decorators import admin_login_required
from sso.views import main
from sso.views.generic import ListView
from sso.accounts.models import User, UserEmail
from sso.accounts.email import send_account_created_email
from sso.organisations.models import Organisation, is_validation_period_active
from sso.accounts.forms import UserAddForm, UserProfileForm, UserEmailForm, AppAdminUserProfileForm
from sso.forms.helpers import ChangedDataList, log_change, ErrorList
from filter import AdminRegionFilter, ApplicationRoleFilter, CenterFilter, CountryFilter, IsActiveFilter, RoleProfileFilter, UserSearchFilter
from sso.views.main import OrderByWithNulls
from sso.utils.url import get_safe_redirect_uri


logger = logging.getLogger(__name__)
    

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
        return super(UserDeleteView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(UserDeleteView, self).get_context_data(**kwargs)
        context['cancel_url'] = reverse('accounts:update_user', args=[self.object.uuid.hex])
        # the user is initialized from the ViewClass with the user to delete
        # so reinitialize it with the request user
        context['user'] = self.request.user
        return context


def has_user_list_access(user):
    return user.is_user_admin or user.is_app_admin


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
    @method_decorator(user_passes_test(has_user_list_access))
    def dispatch(self, request, *args, **kwargs):
        return super(UserList, self).dispatch(request, *args, **kwargs)

    @property
    def list_display(self):
        if settings.SSO_VALIDATION_PERIOD_IS_ACTIVE:
            return ['username', 'picture', 'last_name', _('primary email'), OrganisationField(),LastLogin(), 'date_joined', ValidUntil()]
        else:
            return ['username', 'picture', 'last_name', _('primary email'), OrganisationField(),LastLogin(), 'date_joined']

    def get_queryset(self):
        """
        Get the list of items for this view. This must be an iterable, and may
        be a queryset (in which qs-specific behavior will be enabled).
        """
        user = self.request.user

        qs = super(UserList, self).get_queryset().only('uuid', 'last_login', 'username', 'first_name', 'last_name', 'date_joined', 'picture', 'valid_until')\
            .prefetch_related('useremail_set', 'organisations')
        qs = user.filter_administrable_users(qs)
            
        self.cl = main.ChangeList(self.request, self.model, self.list_display, default_ordering=[OrderByWithNulls(F('last_login'), descending=True)])
        # apply filters
        qs = UserSearchFilter().apply(self, qs) 
        qs = CountryFilter().apply(self, qs)
        qs = AdminRegionFilter().apply(self, qs)
        qs = CenterFilter().apply(self, qs)
        qs = ApplicationRoleFilter().apply(self, qs)
        qs = RoleProfileFilter().apply(self, qs)
        qs = IsActiveFilter().apply(self, qs, default='1')
        
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
        country_filter = CountryFilter().get(self, countries)

        centers = Organisation.objects.none()
        application_roles = user.get_administrable_application_roles()
        role_profiles = user.get_administrable_role_profiles()
        admin_regions = user.get_administrable_user_regions()

        if self.country:
            centers = user.get_administrable_user_organisations().filter(country=self.country)
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
        if user.is_user_admin:
            filters += [IsActiveFilter().get(self)]
        
        context = {
            'result_headers': headers,
            'num_sorted_fields': num_sorted_fields,
            'search_var': main.SEARCH_VAR,
            'page_var': main.PAGE_VAR,
            'query': self.request.GET.get(main.SEARCH_VAR, ''),
            'cl': self.cl,
            'filters': filters,
            'is_active': self.is_active,
            'sso_validation_period_is_active': settings.SSO_VALIDATION_PERIOD_IS_ACTIVE
        }
        context.update(kwargs)
        return super(UserList, self).get_context_data(**context)
    

@admin_login_required
@permission_required('accounts.add_user', raise_exception=True)
def add_user(request, template='accounts/application/add_user_form.html'):
    redirect_uri = get_safe_redirect_uri(request, allowed_hosts())
    if request.method == 'POST':
        form = UserAddForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()                
            send_account_created_email(user, request)
            if redirect_uri:
                success_url = redirect_uri
            else:
                success_url = urlunsplit(('', '', reverse('accounts:add_user_done', args=[user.uuid.hex]), request.GET.urlencode(safe='/'), ''))
            return HttpResponseRedirect(success_url)
    else:
        initial = {}
        default_role_profile = User.get_default_role_profile()
        if default_role_profile:
            initial['role_profiles'] = [default_role_profile.id]
        organisations = request.user.get_administrable_user_organisations()
        if len(organisations) == 1:
            initial['organisation'] = organisations[0]
        form = UserAddForm(request.user, initial=initial)

    data = {'form': form, 'redirect_uri': redirect_uri, 'title': _('Add user')}
    return render(request, template, data)


@admin_login_required
@permission_required('accounts.add_user', raise_exception=True)
def add_user_done(request, uuid, template='accounts/application/add_user_done.html'):
    new_user = get_user_model().objects.get(uuid=uuid)
    redirect_uri = get_safe_redirect_uri(request, allowed_hosts())
    data = {'new_user': new_user, 'redirect_uri': redirect_uri, 'title': _('Add user')}
    return render(request, template, data)

    
@admin_login_required
@permission_required('accounts.change_user', raise_exception=True)
def update_user(request, uuid, template='accounts/application/update_user_form.html'):
    if not request.user.has_user_access(uuid):
        raise PermissionDenied
    user = get_object_or_404(get_user_model(), uuid=uuid)

    if user.useremail_set.count() == 0:
        useremail_extra = 1
    else:
        useremail_extra = 0

    UserEmailInlineFormSet = inlineformset_factory(User, UserEmail, UserEmailForm, extra=useremail_extra, max_num=UserEmail.MAX_EMAIL_ADRESSES)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user, request=request)
        user_email_inline_formset = UserEmailInlineFormSet(request.POST, instance=user)

        if form.is_valid() and user_email_inline_formset.is_valid():
            user = form.save()
            user_email_inline_formset.save()

            if not user.useremail_set.exists():
                msg = _('The account %(username)s has no email address!') % {'username': force_text(user)}
                messages.add_message(request, level=messages.ERROR, message=msg, fail_silently=True)
            else:
                user.ensure_single_primary_email()

            formsets = [user_email_inline_formset]
            change_message = ChangedDataList(form, formsets).change_message()
            log_change(request, user, change_message)

            msg_dict = {'name': force_text(get_user_model()._meta.verbose_name), 'obj': force_text(user)}
            if "_addanother" in request.POST:
                msg = _('The %(name)s "%(obj)s" was changed successfully. You may add another %(name)s below.') % msg_dict
                success_url = reverse('accounts:add_user')
            elif "_continue" in request.POST:
                msg = _('The %(name)s "%(obj)s" was changed successfully. You may edit it again below.') % msg_dict
                success_url = reverse('accounts:update_user', args=[user.uuid.hex])
            elif "_resend_invitation" in request.POST:
                send_account_created_email(user, request)
                msg = _('The %(name)s "%(obj)s" was changed successfully and the invitation email was resend.') % msg_dict
                success_url = reverse('accounts:update_user', args=[user.uuid.hex])
            else:
                msg = _('The %(name)s "%(obj)s" was changed successfully.') % msg_dict
                success_url = reverse('accounts:user_list') + "?" + request.GET.urlencode()
            messages.add_message(request, level=messages.SUCCESS, message=msg, fail_silently=True)
            return HttpResponseRedirect(success_url)

    else:
        user_email_inline_formset = UserEmailInlineFormSet(instance=user)
        form = UserProfileForm(instance=user, request=request)

    user_email_inline_formset.forms += [user_email_inline_formset.empty_form]
    formsets = [user_email_inline_formset]

    media = form.media
    for fs in formsets:
        media = media + fs.media

    errors = ErrorList(form, formsets)
    active = ''
    if errors:
        if not form.is_valid():
            active = 'object'
        else:  # set the first formset with an error as active
            for formset in formsets:
                if not formset.is_valid():
                    active = formset.prefix
                    break

    if (user.last_login is None) or (user.last_login - user.date_joined) < timedelta(seconds=1):
        logged_in = False
    else:
        logged_in = True
    try:
        user_organisation = user.organisations.first()
    except ObjectDoesNotExist:
        user_organisation = None

    dictionary = {'form': form, 'errors': errors, 'formsets': formsets, 'media': media, 'active': active,
                  'logged_in': logged_in, 'is_validation_period_active': is_validation_period_active(user_organisation), 'title': _('Change user')}
    return render(request, template, dictionary)


@admin_login_required
@user_passes_test(has_user_list_access)
def update_user_app_roles(request, uuid, template='accounts/application/update_user_app_roles_form.html'):
    if not request.user.has_user_access(uuid):
        raise PermissionDenied
    user = get_object_or_404(get_user_model(), uuid=uuid)

    if request.method == 'POST':
        form = AppAdminUserProfileForm(request.POST, instance=user, request=request)

        if form.is_valid():
            user = form.save()

            change_message = ChangedDataList(form, []).change_message()
            log_change(request, user, change_message)

            msg_dict = {'name': force_text(get_user_model()._meta.verbose_name), 'obj': force_text(user)}
            if "_continue" in request.POST:
                msg = _('The %(name)s "%(obj)s" was changed successfully. You may edit it again below.') % msg_dict
                success_url = reverse('accounts:update_user_app_roles', args=[user.uuid.hex])
            else:
                msg = _('The %(name)s "%(obj)s" was changed successfully.') % msg_dict
                success_url = reverse('accounts:user_list') + "?" + request.GET.urlencode()
            messages.add_message(request, level=messages.SUCCESS, message=msg, fail_silently=True)
            return HttpResponseRedirect(success_url)

    else:
        form = AppAdminUserProfileForm(instance=user, request=request)

    media = form.media

    errors = ErrorList(form, [])
    active = ''

    # get the role profiles where the administrable application_roles also appear, excluding
    # the role profiles the current user has admin rights for
    application_roles = request.user.get_administrable_application_roles()
    pks = request.user.get_administrable_role_profiles().values_list('pk', flat=True)
    role_profiles = user.role_profiles.filter(application_roles__in=application_roles).exclude(pk__in=pks)
    dictionary = {'form': form, 'errors': errors, 'media': media, 'active': active,
                  'role_profiles': role_profiles,
                  'application_roles': application_roles,
                  'title': _('Change user roles')}
    return render(request, template, dictionary)
