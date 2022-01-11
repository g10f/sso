from django import forms
from django.conf import settings

BLANK_CHOICE_DASH = [("", "---------")]


class BaseForm(forms.ModelForm):
    def save(self, commit=True):
        # attention: a form with initial data has_unchanged if the initial data are unchanged
        if self.instance.pk is None or self.has_changed():
            return super().save(commit)
        else:
            return self.instance

    def opts(self):
        # we need the model verbose_name in the html form
        return self._meta.model._meta


class FormsetForm(BaseForm):
    @property
    def media(self):

        media = super().media
        js = ['js/formsets.js']
        return forms.Media(js=js) + media


class BaseTabularInlineForm(FormsetForm):
    def template(self):
        return 'edit_inline/tabular.html'


class BaseStackedInlineForm(FormsetForm):
    def template(self):
        return 'edit_inline/stacked.html'
