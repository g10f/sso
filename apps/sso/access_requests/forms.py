import logging

from django import forms
from django.conf import settings
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from sso.access_requests.models import AccessRequest
from sso.accounts.models import User
from sso.forms import bootstrap, BaseForm
from sso.forms.fields import Base64ImageField
from sso.organisations.models import Organisation
from sso.utils.email import send_mail
from sso.utils.translation import i18n_email_msg_and_subj

logger = logging.getLogger(__name__)


def send_user_request_extended_access(admins,
                                      access_request,
                                      message,
                                      email_template_name='access_requests/email/access_request_email.txt',
                                      subject_template_name='access_requests/email/access_request_email_subject.txt',
                                      apply_async=False):
    recipients = [force_str(admin.primary_email()) for admin in admins]
    if len(recipients) > 0:
        domain = settings.SSO_DOMAIN
        use_https = settings.SSO_USE_HTTPS
        site_name = settings.SSO_SITE_NAME
        user = access_request.user
        c = {
            'message': message,
            'protocol': use_https and 'https' or 'http',
            'domain': domain,
            'update_user_url': reverse("access_requests:extend_access_accept", args=(access_request.pk,)),
            'user': user,
            'site_name': site_name,
            'days_since_access_request': (now() - access_request.last_modified).days,
        }
        message, subject = i18n_email_msg_and_subj(c, email_template_name, subject_template_name)
        send_mail(subject, message, recipient_list=recipients, reply_to=[user.primary_email()], apply_async=apply_async)


class AccessRequestAcceptForm(forms.Form):
    """
    Form for user admins to accept an request for extended access
    """

    def __init__(self, access_request, *args, **kwargs):
        self.access_request = access_request
        super().__init__(*args, **kwargs)

    def clean(self):
        if not self.access_request.is_open:
            raise forms.ValidationError(_('Request for access was already processed'), code='not-open')

        return super().clean()


class AccessRequestForm(BaseForm):
    message = forms.CharField(label=_("Message"), widget=bootstrap.Textarea(attrs={'cols': 40, 'rows': 5}))
    picture = Base64ImageField(label=_('Your picture'), required=True, help_text=_('Please use a photo of your face.'),
                               widget=bootstrap.ClearableBase64ImageWidget(attrs={
                                   'max_file_size': User.MAX_PICTURE_SIZE,
                                   'width': User.PICTURE_WIDTH,
                                   'height': User.PICTURE_HEIGHT,
                               }))
    created = forms.BooleanField(widget=forms.HiddenInput(), required=False)
    organisation = forms.ModelChoiceField(queryset=Organisation.objects.filter(
        is_active=True, is_selectable=True, association__is_selectable=True).only(
        'id', 'location', 'name', 'organisation_country__country__iso2_code', 'association__name').prefetch_related(
        'organisation_country__country', 'association'), label=_("Organisation"), widget=bootstrap.Select2())

    class Meta:
        model = AccessRequest
        fields = ('message', 'application', 'user', 'picture', 'organisation')
        widgets = {
            'message': bootstrap.Textarea(),
            'application': forms.HiddenInput(),
            'user': forms.HiddenInput()
        }

    def __init__(self, initial=None, instance=None, *args, **kwargs):
        user = kwargs.pop('user')  # remove custom user keyword
        super().__init__(initial=initial, instance=instance, *args, **kwargs)
        if user.picture:
            del self.fields['picture']
        if user.organisations.all():
            del self.fields['organisation']

    def save(self, commit=True):
        cd = self.cleaned_data
        if 'picture' in cd:
            self.instance.user.picture = cd.get('picture')
            self.instance.user.save()
        return super().save(commit)
