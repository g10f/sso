import logging
from urllib.parse import urlunsplit

from django import forms
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils.encoding import force_text
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from sso.forms.helpers import ErrorList
from sso.views import main

logger = logging.getLogger(__name__)


class BaseFilter(object):
    template_name = 'include/_list_filter2.html'
    name = 'name'
    qs_name = None
    select_text = 'Select Choice'
    select_all_text = 'All Choices'
    all_remove = ''
    remove = 'p'
    default = None

    def map_to_database(self, qs_name, value):
        """
        Returns the value for the database query
        """
        return {qs_name: value}

    def get_value_from_query_param(self, view, default):
        return view.request.GET.get(self.name, default)

    def get_filter_list(self):
        raise NotImplemented

    def apply(self, view, qs):
        """
        filter the queryset with the selected value from the HTTP query parameter
        """
        value = self.get_value_from_query_param(view, self.default)
        if value:
            if self.qs_name is None:
                qs_name = self.name
            else:
                qs_name = self.qs_name
            qs = qs.filter(**self.map_to_database(qs_name, value))
        setattr(view, self.name, value)
        return qs

    def get(self, view):
        """
        create a dictionary with all required data for the HTML template
        """
        filter_list = self.get_filter_list()

        if len(filter_list) == 1:
            setattr(view, self.name, filter_list[0])
            filter_list = None

        return {
            'selected': getattr(view, self.name), 'list': filter_list, 'select_text': self.select_text,
            'select_all_text': self.select_all_text,
            'param_name': self.name, 'all_remove': self.all_remove, 'remove': self.remove,
            'template_name': self.template_name
        }


class ViewButtonFilter(BaseFilter):
    template_name = 'include/_list_filter_button.html'

    def get(self, view):
        """
        create a dictionary with all required data for the HTML template
        """
        value = getattr(view, self.name, None)
        if value is not None:
            return {
                'value': value, 'select_text': self.select_text, 'param_name': self.name, 'remove': self.remove,
                'template_name': self.template_name
            }
        else:
            return None


class ViewQuerysetFilter(BaseFilter):
    model = None
    filter_list = None
    style = ""

    def get_value_from_query_param(self, view, default):
        value = view.request.GET.get(self.name, default)
        if value:
            try:
                return self.model.objects.get(pk=value)
            except ObjectDoesNotExist:
                # return empty object
                return self.model()
        else:
            return None

    def get(self, view, filter_list=None):
        """
        create a dictionary with all required data for the HTML template
        """
        if filter_list is None:
            if self.filter_list:
                filter_list = self.filter_list
            else:
                filter_list = self.model.objects.all()

        return {
            'selected': getattr(view, self.name), 'list': filter_list, 'select_text': self.select_text,
            'select_all_text': self.select_all_text,
            'param_name': self.name, 'all_remove': self.all_remove, 'remove': self.remove,
            'template_name': self.template_name,
            'style': self.style
        }


class ViewChoicesFilter(BaseFilter):
    choices = ()

    def map_to_database(self, qs_name, value):
        return {qs_name: value.pk}

    def get_value_from_query_param(self, view, default):
        value = view.request.GET.get(self.name, default)
        try:
            if value:
                return main.FilterItem((value, dict(self.choices)[value]))
        except KeyError:
            pass
        return None

    def get(self, view, choices=None):
        """
        create a dictionary with all required data for the HTML template
        """
        if choices is not None:
            self.choices = choices

        filter_list = [main.FilterItem(item) for item in self.choices]
        return {
            'default': self.default,
            'selected': getattr(view, self.name), 'list': filter_list, 'select_text': self.select_text,
            'select_all_text': self.select_all_text,
            'param_name': self.name, 'all_remove': self.all_remove, 'remove': self.remove,
            'template_name': self.template_name
        }


class SearchFilter(object):
    search_names = []

    def apply(self, view, qs):
        # apply search filter
        search_var = view.request.GET.get(main.SEARCH_VAR, '')
        if search_var:
            search_list = search_var.split()
            q = Q()
            for search in search_list:
                for name in self.search_names:
                    q |= Q(**{name: search})
            qs = qs.filter(q)
        return qs


class ListView(generic.ListView):
    paginate_by = 20
    page_kwarg = main.PAGE_VAR

    def get_paginate_by(self, queryset):
        try:
            return int(self.request.GET.get(main.PAGE_SIZE_VAR, self.paginate_by))
        except ValueError:
            return self.paginate_by


class FormsetsUpdateView(generic.UpdateView):
    def get_formsets(self):
        """
        returns an array of formsets (use django inlineformset_factory)
        override in subclass
        """
        raise NotImplementedError

    @property
    def media(self):
        js = ['js/formsets-1.2.js']
        return forms.Media(js=js)

    @property
    def formsets(self):
        if not hasattr(self, '_formsets'):
            self._formsets = self.get_formsets()
        return self._formsets

    @property
    def is_valid(self):
        # form_class = self.get_form_class()
        # form = self.get_form(form_class)

        if not self.form.is_valid():
            return False

        for formset in self.formsets:
            if not formset.is_valid():
                return False
        return True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        form = context.get("form")
        media = self.media + form.media
        formsets = self.formsets
        for fs in formsets:
            media = media + fs.media

        errors = ErrorList(form, formsets)
        active = ''
        if errors:
            if not form.is_valid():
                try:
                    # Hack to activate the correct tab in the HTML view
                    active = errors[0].data[0].params['active']
                except Exception:
                    active = 'object'
            else:  # set the first formset with an error as active
                for formset in formsets:
                    if not formset.is_valid():
                        active = formset.prefix
                        break

        context.update({'formsets': formsets, 'media': media, 'active': active, 'errors': errors})
        return context

    def post(self, request, *args, **kwargs):
        """
        add additionally the form class to self, because we need to check changed_data for verifying the formsets
        """
        self.object = self.get_object()
        self.form = self.get_form()
        if self.is_valid:
            # form_valid saves the form
            response = self.form_valid(self.form)

            for formset in self.formsets:
                formset.save()
            return response
        else:
            return self.form_invalid(self.form)

    def get_success_url(self):
        msg_dict = {'name': force_text(self.model._meta.verbose_name), 'obj': force_text(self.object)}
        if "_continue" in self.request.POST:
            msg = format_html(
                _('The {name} "{obj}" was changed successfully. You may edit it again below.'),
                **msg_dict)
            success_url = urlunsplit(('', '', self.request.path, self.request.GET.urlencode(safe='/'), ''))
        else:
            msg = format_html(_('The {name} "{obj}" was changed successfully.'), **msg_dict)
            success_url = super().get_success_url()

        messages.add_message(self.request, level=messages.SUCCESS, message=msg, fail_silently=True)
        return success_url
