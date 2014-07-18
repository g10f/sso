# -*- coding: utf-8 -*-
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from sso.views import main
from sso.emails.models import EmailForward, EmailAlias
from sso.views.generic import FormsetsUpdateView, ListView, ViewChoicesFilter, SearchFilter
from sso.emails.forms import AdminEmailForwardForm, EmailAliasForm, EmailForm
from sso.organisations.views import get_optional_email_inline_formset

from sso.emails.models import Email

import logging
logger = logging.getLogger(__name__)


class EmailUpdateView(FormsetsUpdateView):
    form_class = EmailForm
    model = Email
    slug_field = slug_url_kwarg = 'uuid'

    @method_decorator(login_required)
    @method_decorator(permission_required('emails.change_email', raise_exception=True))
    def dispatch(self, request, *args, **kwargs): 
        return super(EmailUpdateView, self).dispatch(request, *args, **kwargs)
    
    def get_formsets(self):
        email_forward_inline_formset = get_optional_email_inline_formset(self.request, self.object, 
                                                                         Model=EmailForward, Form=AdminEmailForwardForm, max_num=10)
        email_alias_inline_formset = get_optional_email_inline_formset(self.request, self.object, 
                                                                       Model=EmailAlias, Form=EmailAliasForm, max_num=6)
        
        formsets = []
        if email_forward_inline_formset:
            email_forward_inline_formset.forms += [email_forward_inline_formset.empty_form]
            formsets += [email_forward_inline_formset]
        if email_alias_inline_formset:
            email_alias_inline_formset.forms += [email_alias_inline_formset.empty_form]
            formsets += [email_alias_inline_formset]
        
        return formsets


class EmailTypeFilter(ViewChoicesFilter):
    name = 'email_type'
    choices = Email.EMAIL_TYPE_CHOICES
    select_text = _('Select Email Type')
    select_all_text = _("All Email Types")


class PermissionFilter(ViewChoicesFilter):
    name = 'permission'
    choices = Email.PERMISSION_CHOICES
    select_text = _('Select Permission')
    select_all_text = _("All Permissions")


class EmailSearchFilter(SearchFilter):
    search_names = ['name__icontains', 'email__icontains']


class EmailList(ListView):
    template_name = 'emails/email_list.html'
    model = Email
    list_display = ['email', 'name', 'email_type', 'permission']
        
    @method_decorator(login_required)
    @method_decorator(permission_required('emails.change_email', raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        return super(EmailList, self).dispatch(request, *args, **kwargs)
        
    def get_queryset(self):
        """
        Get the list of items for this view. This must be an iterable, and may
        be a queryset (in which qs-specific behavior will be enabled).
        """
        qs = super(EmailList, self).get_queryset()
            
        self.cl = main.ChangeList(self.request, self.model, self.list_display, default_ordering=['email'])
        
        # apply filters
        qs = EmailSearchFilter().apply(self, qs)  
        qs = EmailTypeFilter().apply(self, qs)
        qs = PermissionFilter().apply(self, qs)
        
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
        
        email_filter = EmailTypeFilter().get(self)
        permission_filter = PermissionFilter().get(self)
        filters = [email_filter, permission_filter]
        
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
        return super(EmailList, self).get_context_data(**context)
