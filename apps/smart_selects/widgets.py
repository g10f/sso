from functools import cmp_to_key

from django import forms
from django.apps import apps
from django.forms.widgets import Select
from django.urls import reverse
from django.utils import six
from django.utils.safestring import mark_safe
from smart_selects.utils import strcoll


class ChainedSelect(Select):
    def __init__(self, app_name, model_name, chain_field, model_field, show_all, auto_choose, manager=None, attrs=None,
                 *args, **kwargs):
        self.app_name = app_name
        self.model_name = model_name
        self.chain_field = chain_field
        self.model_field = model_field
        self.show_all = show_all
        self.manager = manager

        # add form-control class for bootstrap
        if attrs is None:
            attrs = {}
        css_classes = attrs.get('class', '').split()
        css_classes.append('form-control')
        attrs['class'] = ' '.join(css_classes)
        super(ChainedSelect, self).__init__(attrs, *args, **kwargs)

    # bootstrap
    def add_required(self):
        if self.is_required:
            if self.attrs is None:
                self.attrs = {}
            self.attrs['required'] = ''

    @property
    def media(self):
        js = ['js/vendor/jquery-3.1.1.min.js', 'js/smart_select.js']
        return super().media + forms.Media(js=js)

    def render(self, name, value, attrs=None, renderer=None):
        self.add_required()  # bootstrap

        if len(name.split('-')) > 1:  # formset
            chain_field = '-'.join(name.split('-')[:-1] + [self.chain_field])
        else:
            chain_field = self.chain_field

        if self.show_all:
            view_name = "chained_filter_all"
        else:
            view_name = "chained_filter"
        kwargs = {'app': self.app_name, 'model': self.model_name, 'field': self.model_field, 'value': "1"}
        if self.manager is not None:
            kwargs.update({'manager': self.manager})
        url = "/".join(reverse(view_name, kwargs=kwargs).split("/")[:-2])
        # Hacky way to getting the correct empty_label from the field instead of a hardcoded '--------'
        empty_label = list(self.choices)[0][1]

        final_choices = []

        if value:
            try:
                item = self.queryset.filter(pk=value)[0]
                try:
                    pk = getattr(item, self.model_field + "_id")
                    objects_filter = {self.model_field: pk}
                except AttributeError:
                    try:  # maybe m2m?
                        pks = getattr(item, self.model_field).all().values_list('pk', flat=True)
                        objects_filter = {self.model_field + "__in": pks}
                    except AttributeError:
                        try:  # maybe a set?
                            pks = getattr(item, self.model_field + "_set").all().values_list('pk', flat=True)
                            objects_filter = {self.model_field + "__in": pks}
                        except:  # give up
                            objects_filter = {}
                filtered = list(
                    apps.get_model(self.app_name, self.model_name).objects.filter(**objects_filter).distinct())
                sorted(filtered, key=cmp_to_key(strcoll))
                for choice in filtered:
                    final_choices.append((choice.pk, six.text_type(choice)))
            except IndexError:
                pass
        if len(final_choices) > 1:
            final_choices = [("", empty_label)] + final_choices
        if self.show_all:
            final_choices.append(("", empty_label))
            self.choices = list(self.choices)
            sorted(self.choices, key=cmp_to_key(strcoll))
            for ch in self.choices:
                if ch not in final_choices:
                    final_choices.append(ch)
        self.choices = final_choices
        final_attrs = self.build_attrs(self.attrs, attrs)
        if 'class' in final_attrs:
            final_attrs['class'] += ' chained'
        else:
            final_attrs['class'] = 'chained'
        final_attrs['name'] = name
        final_attrs['data-chainfield'] = chain_field
        final_attrs['data-url'] = url
        final_attrs['data-empty_label'] = empty_label
        output = super(ChainedSelect, self).render(name, value, final_attrs, renderer)
        return mark_safe(output)
