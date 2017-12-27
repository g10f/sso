from django import forms

BLANK_CHOICE_DASH = [("", "---------")]

default_app_config = 'sso.forms.apps.FormsConfig'


class BaseForm(forms.ModelForm):
    """
    @property
    def media(self):
        media = super(BaseForm, self).media
        js = ['inlines.js']
        return forms.Media(js=['js/%s' % url for url in js]) + media
    """
    def save(self, commit=True):
        if self.has_changed():
            return super(BaseForm, self).save(commit)
        else:
            return self.instance

    def opts(self):
        # we need the model verbose_name in the html form
        return self._meta.model._meta


class BaseTabularInlineForm(BaseForm):    
    def template(self):
        return 'edit_inline/tabular.html'


class BaseStackedInlineForm(BaseForm):
    def template(self):
        return 'edit_inline/stacked.html'
