import logging

from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.generic import DeleteView, DetailView, CreateView
from sso.emails.forms import EmailAliasInlineForm, GroupEmailForm, EmailManagerInlineForm, EmailForwardForm
from sso.emails.models import Email, EmailForward, EmailAlias, GroupEmail, GroupEmailManager, PERM_EVERYBODY
from sso.forms.helpers import get_optional_inline_formset
from sso.views import main
from sso.views.generic import FormsetsUpdateView, ListView, ViewChoicesFilter, SearchFilter, ViewButtonFilter

logger = logging.getLogger(__name__)


class GroupEmailForwardCreateView(CreateView):
    model = EmailForward
    form_class = EmailForwardForm
    template_name_suffix = '_create_form'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_groupemail_access(self.kwargs['uuid']):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        group_email = GroupEmail.objects.get_by_natural_key(self.kwargs['uuid'])
        initial = self.initial.copy()
        initial.update({'email': group_email.email})
        return initial

    def get_success_url(self):
        return reverse('emails:groupemail_detail', args=[self.kwargs['uuid']])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['uuid'] = self.kwargs['uuid']
        return context


class GroupEmailForwardDeleteView(DeleteView):
    model = EmailForward

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_groupemail_access(self.kwargs['uuid']):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('emails:groupemail_detail', args=[self.kwargs['uuid']])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['uuid'] = self.kwargs['uuid']
        return context


class GroupEmailBaseView(object):
    model = GroupEmail
    slug_field = slug_url_kwarg = 'uuid'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = {}
        if self.object and self.request.user.is_authenticated:
            context['has_groupmail_access'] = self.request.user.has_groupemail_access(self.kwargs.get('uuid'))

        context.update(kwargs)
        return super().get_context_data(**context)


class GroupEmailDetailView(GroupEmailBaseView, DetailView):
    pass


class GroupEmailCreateView(GroupEmailBaseView, CreateView):
    form_class = GroupEmailForm
    template_name_suffix = '_create_form'

    def get_success_url(self):
        return reverse('emails:groupemail_detail', args=[self.object.uuid.hex])

    @method_decorator(login_required)
    @method_decorator(permission_required('emails.add_groupemail', raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class GroupEmailUpdateView(GroupEmailBaseView, FormsetsUpdateView):
    form_class = GroupEmailForm

    @method_decorator(login_required)
    @method_decorator(permission_required('emails.change_groupemail', raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_formsets(self):
        formsets = []
        admin_inline_formset = get_optional_inline_formset(self.request, self.object, parent_model=GroupEmail,
                                                           model=GroupEmailManager, form=EmailManagerInlineForm, max_num=10)
        email_alias_inline_formset = get_optional_inline_formset(self.request, self.object.email, Email,
                                                                 model=EmailAlias, form=EmailAliasInlineForm, max_num=6)

        if admin_inline_formset:
            formsets += [admin_inline_formset]
        if email_alias_inline_formset:
            formsets += [email_alias_inline_formset]

        return formsets


class PermissionFilter(ViewChoicesFilter):
    name = 'permission'
    qs_name = 'email__permission'
    choices = Email.PERMISSION_CHOICES
    select_text = _('Permission')
    select_all_text = _("All Permissions")


class EmailSearchFilter(SearchFilter):
    search_names = ['name__icontains', 'email__email__icontains']


class MyGroupEmailsFilter(ViewButtonFilter):
    name = 'my_emails'
    select_text = _('My Emails')

    def apply(self, view, qs, default=''):
        if not view.request.user.has_perms(["emails.change_groupemail"]):
            value = self.get_value_from_query_param(view, default)
            if value:
                qs = qs.filter(groupemailmanager__manager=view.request.user)
            setattr(view, self.name, value)
            return qs
        else:
            return qs


class IsActiveFilter(ViewChoicesFilter):
    name = 'email__is_active'
    choices = (('1', _('Active emails')), ('2', _('Inactive emails')))
    select_text = _('active/inactive')
    select_all_text = _("All")

    def map_to_database(self, qs_name, value):
        return {qs_name: True if (value.pk == "1") else False}


class GroupEmailList(ListView):
    template_name = 'emails/groupemail_list.html'
    model = GroupEmail
    list_display = ['name', 'email', 'homepage', 'permission']

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """
        Get the list of items for this view. This must be an iterable, and may
        be a queryset (in which qs-specific behavior will be enabled).
        """
        user = self.request.user
        qs = super().get_queryset().select_related()
        if not user.has_perms(["emails.change_groupemail"]):
            qs = qs.filter(Q(email__is_active=True) & (Q(groupemailmanager__manager=user) | Q(email__permission=PERM_EVERYBODY)))

        self.cl = main.ChangeList(self.request, self.model, self.list_display, default_ordering=['email'])

        # apply filters
        qs = MyGroupEmailsFilter().apply(self, qs)
        qs = EmailSearchFilter().apply(self, qs)
        qs = PermissionFilter().apply(self, qs)
        qs = IsActiveFilter().apply(self, qs)
        # Set ordering.
        ordering = self.cl.get_ordering(self.request, qs)
        qs = qs.order_by(*ordering)
        return qs.distinct()

    def get_context_data(self, **kwargs):
        headers = list(self.cl.result_headers())
        num_sorted_fields = 0
        for h in headers:
            if h['sortable'] and h['sorted']:
                num_sorted_fields += 1

        filters = []
        filters += [MyGroupEmailsFilter().get(self)]
        if self.request.user.has_perms(["emails.change_groupemail"]):
            filters += [PermissionFilter().get(self)]
        filters.append(IsActiveFilter().get(self))

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
