from urllib.parse import urlunsplit

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.forms.models import inlineformset_factory
from django.http.response import HttpResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from sso.accounts.forms import ApplicationForm, ApplicationRoleForm, ClientForm, ApplicationAdminForm
from sso.accounts.models import Application, ApplicationRole, ApplicationAdmin, RoleProfile
from sso.oauth2.models import Client, get_default_secret
from sso.views import main
from sso.views.generic import FormsetsUpdateView, ListView, ViewChoicesFilter, SearchFilter
from sso.views.mixins import MessagesMixin


class IsActiveFilter(ViewChoicesFilter):
    name = 'is_active'
    choices = (('1', _('Active Applications')), ('2', _('Inactive Applications')))
    select_text = _('active/inactive')
    select_all_text = _("All")

    def map_to_database(self, qs_name, value):
        return {qs_name: True if (value.pk == "1") else False}


class ApplicationSearchFilter(SearchFilter):
    search_names = ['title__icontains', 'url__icontains']


class ApplicationListView(ListView):
    template_name = 'accounts/application_list.html'
    model = Application
    list_display = ['title', 'url', 'global_navigation', 'is_internal', 'is_active']

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """
        Get the list of items for this view. This must be an iterable, and may
        be a queryset (in which qs-specific behavior will be enabled).
        """
        qs = super().get_queryset()
        qs = self.request.user.filter_administrable_apps(qs)
        self.cl = main.ChangeList(self.request, self.model, self.list_display)

        # apply filters
        qs = ApplicationSearchFilter().apply(self, qs)
        qs = IsActiveFilter().apply(self, qs)

        # Set ordering.
        ordering = self.cl.get_ordering(self.request, qs)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs.distinct()

    def get_context_data(self, **kwargs):
        headers = list(self.cl.result_headers())
        num_sorted_fields = 0
        for h in headers:
            if h['sortable'] and h['sorted']:
                num_sorted_fields += 1

        filters = []
        filters.append(IsActiveFilter().get(self))

        context = {
            'result_headers': headers,
            'num_sorted_fields': num_sorted_fields,
            'search_var': main.SEARCH_VAR,
            'page_var': main.PAGE_VAR,
            'query': self.request.GET.get(main.SEARCH_VAR, ''),
            'cl': self.cl,
            'filters': filters,
            'my_applications': getattr(self, 'my_applications', '')
        }
        context.update(kwargs)
        return super().get_context_data(**context)


class ApplicationBaseView(MessagesMixin):
    model = Application
    slug_field = slug_url_kwarg = 'uuid'

    def get_context_data(self, **kwargs):
        client_list = []
        user = self.request.user
        if self.object is not None:
            perms = ["oauth2.change_client", "oauth2.delete_client"]
            for client in self.object.client_set.all():
                client.user_has_access = client.has_access(user, perms)
                client_list.append(client)

        context = {'client_list': client_list}
        context.update(kwargs)
        return super().get_context_data(**context)

    @method_decorator(permission_required('accounts.view_application', raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if 'uuid' in kwargs and not user.has_app_access(kwargs.get('uuid')):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class ApplicationDetailView(ApplicationBaseView, DetailView):
    pass


class ApplicationCreateView(ApplicationBaseView, CreateView):
    template_name_suffix = '_create_form'
    form_class = ApplicationForm

    @method_decorator(permission_required('accounts.add_application', raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        #  add user to form kwargs
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        if '_continue' in self.request.POST:
            success_url = self.request.path
            self.create_and_continue_message()
        else:
            success_url = reverse('accounts:application_detail', args=[self.object.uuid.hex])
            self.create_message()
        # save exiting get parameters (i.e. redirect_uri)
        return urlunsplit(('', '', success_url, self.request.GET.urlencode(safe='/'), ''))


class ApplicationUpdateView(ApplicationBaseView, FormsetsUpdateView):
    form_class = ApplicationForm

    @method_decorator(permission_required('accounts.change_application', raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        # add user to form kwargs
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_formsets(self):
        app_admin_error_messages = {'help_text': _("Application admins can manage the application, OIDC clients and application roles of users they have access to.")}
        ApplicationRoleInlineFormSet = inlineformset_factory(self.model, ApplicationRole, ApplicationRoleForm, extra=1)
        ApplicationAdminInlineFormSet = inlineformset_factory(self.model, ApplicationAdmin, ApplicationAdminForm, extra=1)
        if self.request.method == 'POST':
            application_role_inline_formset = ApplicationRoleInlineFormSet(self.request.POST, instance=self.object)
            application_admin_inline_formset = ApplicationAdminInlineFormSet(self.request.POST, instance=self.object, error_messages=app_admin_error_messages)
        else:
            application_role_inline_formset = ApplicationRoleInlineFormSet(instance=self.object)
            application_admin_inline_formset = ApplicationAdminInlineFormSet(instance=self.object, error_messages=app_admin_error_messages)

        formsets = [application_role_inline_formset, application_admin_inline_formset]
        return formsets

    def get_success_url(self):
        if '_continue' in self.request.POST:
            success_url = self.request.path
            self.update_and_continue_message()
        else:
            success_url = reverse('accounts:application_detail', args=[self.object.uuid.hex])
            self.update_message()
        # save exiting get parameters (i.e. redirect_uri)
        return urlunsplit(('', '', success_url, self.request.GET.urlencode(safe='/'), ''))


class ApplicationDeleteView(ApplicationBaseView, DeleteView):
    def get_success_url(self):
        self.delete_message()
        return reverse('accounts:application_list')

    @method_decorator(permission_required('accounts.delete_application', raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = {
            'role_profile_count': RoleProfile.objects.filter(application_roles__application=self.object).count(),
            'user_count': get_user_model().objects.filter(application_roles__application=self.object).count(),
            'cancel_url': reverse('accounts:application_detail', args=[self.object.uuid.hex])
        }
        context.update(kwargs)
        return super().get_context_data(**context)


@permission_required("oauth2.change_client", raise_exception=True)
def client_secret(request):
    return HttpResponse(get_default_secret())


class ClientBaseView(MessagesMixin):
    model = Client
    slug_field = slug_url_kwarg = 'uuid'

    @method_decorator(permission_required('oauth2.view_client', raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        self.object = self.get_object()
        if not self.object.has_access(user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class ClientCreateView(ClientBaseView, CreateView):
    template_name_suffix = '_create_form'
    form_class = ClientForm

    @method_decorator(permission_required('oauth2.add_client', raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        # check here for app access, because the uuid is the app uuid
        if 'uuid' in kwargs and not user.has_app_access(kwargs.get('uuid')):
            raise PermissionDenied
        return super(CreateView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        #  add user and initial to form kwargs
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['initial'] = {'application': Application.objects.get_by_natural_key(self.kwargs['uuid'])}
        return kwargs

    def get_success_url(self):
        if '_continue' in self.request.POST:
            success_url = reverse('accounts:client_update', args=[self.object.uuid.hex])
            self.update_and_continue_message()
        else:
            success_url = reverse('accounts:application_detail', args=[self.object.application.uuid.hex])
            self.update_message()
        # save exiting get parameters (i.e. redirect_uri)
        return urlunsplit(('', '', success_url, self.request.GET.urlencode(safe='/'), ''))


class ClientUpdateView(ClientBaseView, UpdateView):
    form_class = ClientForm

    @method_decorator(permission_required('oauth2.change_client', raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        # add user to form kwargs
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        if '_continue' in self.request.POST:
            self.update_and_continue_message()
            success_url = self.request.path
        else:
            self.update_message()
            success_url = reverse('accounts:application_detail', args=[self.object.application.uuid.hex])
        # save exiting get parameters (i.e. redirect_uri)
        return urlunsplit(('', '', success_url, self.request.GET.urlencode(safe='/'), ''))


class ClientDeleteView(ClientBaseView, DeleteView):
    def get_success_url(self):
        self.delete_message()
        return reverse('accounts:application_detail', args=[self.object.application.uuid.hex])

    @method_decorator(permission_required('oauth2.delete_client', raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
