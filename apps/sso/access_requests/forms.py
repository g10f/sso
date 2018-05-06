import logging

from django import forms
from django.conf import settings
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from sso.accounts.models import User
from sso.forms import bootstrap
from sso.forms.helpers import clean_base64_picture
from sso.utils.email import send_mail
from sso.utils.translation import i18n_email_msg_and_subj

logger = logging.getLogger(__name__)


def send_user_request_extended_access(admins,
                                      user,
                                      message,
                                      email_template_name='access_requests/email/access_request_email.txt',
                                      subject_template_name='access_requests/email/access_request_email_subject.txt',
                                      apply_async=False):
    recipients = [admin.primary_email() for admin in admins]
    if len(recipients) > 0:
        domain = settings.SSO_DOMAIN
        use_https = settings.SSO_USE_HTTPS
        site_name = settings.SSO_SITE_NAME
        c = {
            'message': message,
            'protocol': use_https and 'https' or 'http',
            'domain': domain,
            'update_user_url': reverse("accounts:update_user", args=(user.uuid.hex,)),
            'user': user,
            'site_name': site_name,
        }
        message, subject = i18n_email_msg_and_subj(c, email_template_name, subject_template_name)
        send_mail(subject, message, recipient_list=recipients, apply_async=apply_async)


class AccountUpgradeForm(forms.Form):
    message = forms.CharField(label=_("Message"), widget=bootstrap.Textarea(attrs={'cols': 40, 'rows': 5}))
    base64_picture = forms.CharField(label=_('Your picture'), help_text=_(
        'Please use a photo of your face. We are using it also to validate your registration.'),
                                     widget=bootstrap.HiddenInput)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')  # remove custom user keyword
        super().__init__(*args, **kwargs)
        if self.user.picture:
            del self.fields['base64_picture']

    def clean_base64_picture(self):
        base64_picture = self.cleaned_data["base64_picture"]
        return clean_base64_picture(base64_picture, User.MAX_PICTURE_SIZE)

    def send_email(self, admins):
        message = self.cleaned_data['message']
        send_user_request_extended_access(admins, self.user, message)

    def save(self):
        cd = self.cleaned_data
        if 'base64_picture' in cd:
            self.user.picture = cd.get('base64_picture')
            self.user.save()
