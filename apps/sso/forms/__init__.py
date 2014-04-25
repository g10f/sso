from django import forms 

BLANK_CHOICE_DASH = [("", "---------")]

class BaseForm(forms.ModelForm):
    """
    @property
    def media(self):
        media = super(BaseForm, self).media
        js = ['inlines.js']
        return forms.Media(js=[static('js/%s' % url) for url in js]) + media
    """
    def save(self, commit=True):
        if self.has_changed():
            return super(BaseForm, self).save(commit)
        else:
            return self.instance
