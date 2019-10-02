from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, resolve_url
from django.template.response import TemplateResponse
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DeleteView, FormView
from sso.accounts.models import ApplicationRole
from sso.auth.decorators import admin_login_required
from sso.organisations.models import is_validation_period_active_for_user, OrganisationCountry
from sso.signals import user_registration_completed
from sso.views import main
from sso.views.generic import SearchFilter, ViewChoicesFilter, ViewQuerysetFilter, ListView
from .forms import RegistrationProfileForm, SendMailForm
from .models import RegistrationProfile, RegistrationManager, get_check_back_email_message, \
    get_access_denied_email_message, send_set_password_email
from .tokens import default_token_generator


class UserRegistrationDeleteView(DeleteView):
    model = get_user_model()
    success_url = reverse_lazy('registration:user_registration_list')

    def get_queryset(self):
        # filter the users for who the authenticated user has admin rights
        qs = super().get_queryset()
        user = self.request.user
        return user.filter_administrable_users(qs)

    @method_decorator(admin_login_required)
    @method_decorator(permission_required('registration.delete_registrationprofile', raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # remove the the key with the name registration 'user' from the context,
        # because this would overwrite the current logged in user in the template
        context.pop('user')
        context['cancel_url'] = reverse('registration:update_user_registration',
                                        args=[self.object.registrationprofile.pk])
        return context


class RegistrationSearchFilter(SearchFilter):
    search_names = ['user__username__icontains', 'user__first_name__icontains',
                    'user__last_name__icontains', 'user__useremail__email__icontains']


class CountryFilter(ViewQuerysetFilter):
    name = 'country'
    qs_name = 'user__organisations__organisation_country'
    model = OrganisationCountry
    select_text = _('Country')
    select_all_text = _('All Countries')


class CheckBackFilter(ViewChoicesFilter):
    name = 'check_back'
    choices = (('1', _('Check Back Required')), ('2', _('No Check Back Required')))
    select_text = _('check back filter')
    select_all_text = _("All")
    default = '2'

    def map_to_database(self, qs_name, value):
        return {qs_name: True if (value.pk == "1") else False}


class IsAccessDeniedFilter(ViewChoicesFilter):
    name = 'is_access_denied'
    choices = (('1', _('Access Denied')), ('2', _('Access Not Denied')))
    select_text = _('access denied filter')
    select_all_text = _("All")
    default = '2'

    def map_to_database(self, qs_name, value):
        return {qs_name: True if (value.pk == "1") else False}


class UserRegistrationList(ListView):
    template_name = 'registration/user_registration_list.html'
    model = RegistrationProfile
    list_display = ['user', _('picture'), 'email', 'center', 'date_registered', 'check_back', 'is_access_denied',
                    'comment']

    @method_decorator(admin_login_required)
    @method_decorator(permission_required('registration.change_registrationprofile', raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset() \
            .prefetch_related('user__organisations', 'user__organisations__organisation_country__country',
                              'user__useraddress_set', 'user__useraddress_set__country', 'user__useremail_set') \
            .filter(user__is_active=False, is_validated=True, user__last_login__isnull=True)

        # display only users from centers where the logged in user has admin rights
        user = self.request.user
        qs = RegistrationManager.filter_administrable_registrationprofiles(user, qs)

        # Set ordering.
        self.cl = main.ChangeList(self.request, self.model, self.list_display, default_ordering=['-date_registered'])

        # apply filters
        qs = RegistrationSearchFilter().apply(self, qs)
        qs = CountryFilter().apply(self, qs)
        qs = CheckBackFilter().apply(self, qs)
        qs = IsAccessDeniedFilter().apply(self, qs)

        ordering = self.cl.get_ordering(self.request, qs)
        qs = qs.order_by(*ordering)
        return qs

    def get_context_data(self, **kwargs):
        """
        Get the context for this view.
        """
        headers = list(self.cl.result_headers())
        num_sorted_fields = 0
        for h in headers:
            if h['sortable'] and h['sorted']:
                num_sorted_fields += 1

        # list of centers of registrations where the user has admin rights
        user_organisations = self.request.user.get_administrable_user_organisations().filter(
            user__is_active=False,
            user__registrationprofile__isnull=False,
            user__registrationprofile__is_validated=True)
        countries = OrganisationCountry.objects.filter(
            pk__in=user_organisations.values_list('organisation_country', flat=True)).prefetch_related('country')

        country_filter = CountryFilter().get(self, countries)
        check_back_filter = CheckBackFilter().get(self)
        is_access_denied_filter = IsAccessDeniedFilter().get(self)

        filters = [country_filter, check_back_filter, is_access_denied_filter]
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


@admin_login_required
@permission_required('registration.change_registrationprofile', raise_exception=True)
def update_user_registration(request, pk, template='registration/change_user_registration_form.html'):
    """
    registration admin view to activate or update user registrations
    """
    registrationprofile = get_object_or_404(RegistrationProfile, pk=pk)
    if not request.user.has_user_access(registrationprofile.user.uuid):
        raise PermissionDenied

    if request.method == 'POST':
        registrationprofile_form = RegistrationProfileForm(request.POST, instance=registrationprofile, request=request)
        if registrationprofile_form.is_valid():
            msg_dict = {'name': force_text(get_user_model()._meta.verbose_name),
                        'obj': force_text(registrationprofile)}
            action = request.POST.get("action")
            registrationprofile_form.save()
            if action == "continue":
                msg = _('The %(name)s "%(obj)s" was saved successfully. You may edit it again below.') % msg_dict
                success_url = reverse('registration:update_user_registration', args=[pk])
            elif action == "save":
                msg = _('The %(name)s "%(obj)s" was saved successfully.') % msg_dict
                success_url = reverse('registration:user_registration_list') + "?" + request.GET.urlencode()
            elif action in ["deny", "check_back"]:
                msg = _('The %(name)s "%(obj)s" was saved successfully.') % msg_dict
                success_url = reverse('registration:process_user_registration',
                                      kwargs={'pk': pk, 'action': action}) + "?" + request.GET.urlencode()
            elif action == "activate":
                msg = _('The %(name)s "%(obj)s" was saved successfully.') % msg_dict
                registrationprofile.process(action)
                send_set_password_email(registrationprofile.user, request,
                                        reply_to=[request.user.primary_email().email])
                success_url = reverse('registration:user_registration_list') + "?" + request.GET.urlencode()
            else:
                raise ValueError("Unknown action: %s" % action)

            messages.add_message(request, level=messages.SUCCESS, message=msg, fail_silently=True)
            return HttpResponseRedirect(success_url)
    else:
        registrationprofile_form = RegistrationProfileForm(instance=registrationprofile, request=request)

    app_roles_by_profile = {id for id in
                            ApplicationRole.objects.filter(roleprofile__user__id=registrationprofile.user.pk).only(
                                "id").values_list('id', flat=True)}

    data = {'form': registrationprofile_form, 'app_roles_by_profile': app_roles_by_profile,
            'media': registrationprofile_form.media, 'instance': registrationprofile, 'title': _('Edit registration')}
    return render(request, template, data)


def validation_confirm(request, uidb64=None, token=None, token_generator=default_token_generator,
                       template='registration/validation_confirm.html'):
    """
    view to confirm the email in the registration process
    """
    try:
        from django.utils.http import urlsafe_base64_decode
        uid = urlsafe_base64_decode(uidb64).decode()
        profile = RegistrationProfile.objects.get(pk=uid)
    except (ValueError, RegistrationProfile.DoesNotExist):
        profile = None

    validlink = False
    if profile is not None:
        if is_validation_period_active_for_user(profile.user):
            redirect_url = resolve_url('registration:validation_complete2')
        else:
            redirect_url = resolve_url('registration:validation_complete')

        if profile.is_validated:
            return HttpResponseRedirect(redirect_url)
        elif token_generator.check_token(profile, token):
            validlink = True

            if request.method == 'POST':
                profile.is_validated = True
                profile.save()
                profile.user.confirm_primary_email_if_no_confirmed()
                # enable brand specific modification
                user_registration_completed.send_robust(sender=None, user_registration=profile)
                return HttpResponseRedirect(redirect_url)

    context = {
        'email': profile.user.primary_email() if profile else None,
        'validlink': validlink,
    }
    return TemplateResponse(request, template, context)


class RegistrationSendMailFormView(FormView):
    email_messages = {
        'check_back': get_check_back_email_message,
        'deny': get_access_denied_email_message
    }
    action_breadcrumbs = {
        'check_back': _("Mark user for check back"),
        'deny': _("Deny user")
    }
    action_txts = {
        'check_back': _("Mark user for check back and send email"),
        'deny': _("Deny user and send email")
    }
    success_url = reverse_lazy('registration:user_registration_list')
    template_name = 'registration/process_registration.html'

    def __init__(self, form_class=SendMailForm, *args, **kwargs):
        # form_class should be a Form class, not an instance.
        self.form_class = form_class
        self.instance = None
        super().__init__(*args, **kwargs)

    @method_decorator(admin_login_required)
    @method_decorator(permission_required('accounts.change_user'))
    def dispatch(self, request, *args, **kwargs):
        self.instance = get_object_or_404(RegistrationProfile, pk=self.kwargs['pk'])
        # check if admin has access to the specific user
        if not request.user.has_user_access(self.instance.user.uuid):
            raise PermissionDenied
        self.extra_context = {'action_txt': self.action_txts[self.kwargs['action']],
                              'action_breadcrumb': self.action_breadcrumbs[self.kwargs['action']]}
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.instance
        kwargs['request'] = self.request
        return kwargs

    def get_initial(self):
        reply_to_email = self.request.user.primary_email().email
        message, subject = self.email_messages[self.kwargs['action']](self.instance.user, self.request, reply_to_email)
        return {'message': message, 'subject': subject}

    def form_valid(self, form):
        self.instance.process(self.kwargs['action'])
        message = form.cleaned_data['message']
        subject = form.cleaned_data['subject']
        self.instance.user.email_user(subject, message, reply_to=[self.request.user.primary_email().email])
        return super().form_valid(form)
