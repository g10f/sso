import logging

from django import forms
from django.utils.translation import ugettext_lazy as _
from sso.forms import bootstrap

logger = logging.getLogger(__name__)


class SendMailForm(forms.Form):
    subject = forms.CharField(label=_("Subject"), required=True, max_length=1024, widget=bootstrap.TextInput())
    message = forms.CharField(label=_("Message"), required=True, max_length=4096,
                              widget=bootstrap.Textarea(attrs={'cols': 40, 'rows': 20}))

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        self.instance = kwargs.pop('instance')
        super().__init__(*args, **kwargs)
