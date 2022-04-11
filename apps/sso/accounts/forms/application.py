import logging
import uuid

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils.translation import gettext_lazy as _
from sso.forms import bootstrap, BaseForm, BaseTabularInlineForm
from ..models import ApplicationRole, Application, ApplicationAdmin, User, Role
from ...oauth2.models import Client
from ...registration import default_username_generator
from ...utils.translation import mark_safe_lazy

logger = logging.getLogger(__name__)

ALLOWED_CLIENT_TYPES = [
    ('web', _('Confidential client')),  # response_type=code grant_type=authorization_code or refresh_token
    ('native', _('Public client')),
    # response_type=code  grant_type=authorization_code or refresh_token redirect_uris=http://localhost or
    #  urn:ietf:wg:oauth:2.0:oob
    ('service', _('Service account')),  # grant_type=client_credentials
]

ALLOWED_SCOPES = [
    ('openid', 'openid'),
    ('profile', 'profile'),
    ('email', 'email'),
    ('role', 'role'),
    ('role_profile', 'role_profile'),
    ('offline_access', 'offline_access'),
    ('address', 'address'),
    ('phone', 'phone'),
    ('picture', 'picture'),
    ('events', 'events'),
    ('users', 'users'),
]


def add_app_admin_group(user):
    try:
        app_admin_group = Group.objects.get(name='AppAdmin')
        if app_admin_group not in user.groups.all():
            user.groups.add(app_admin_group)
    except ObjectDoesNotExist:
        logger.warning("AppAdmin does not exist.")


class ApplicationForm(BaseForm):
    class Meta:
        model = Application
        fields = ('title', 'url', 'notes', 'is_active', 'is_internal')
        widgets = {
            'title': bootstrap.TextInput(attrs={'size': 50}),
            'notes': bootstrap.Textarea(attrs={'rows': '5'}),
            'url': bootstrap.TextInput(attrs={'size': 50}),
            'is_active': bootstrap.CheckboxInput(),
            'is_internal': bootstrap.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')  # remove custom user keyword
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        create_admin = False
        if self.instance.pk is None:
            create_admin = True
        self.instance = super().save(commit=commit)
        if create_admin:
            ApplicationAdmin.objects.create(application=self.instance, admin=self.user)
            add_app_admin_group(user=self.user)
        return self.instance


class ApplicationRoleForm(BaseTabularInlineForm):
    role = forms.ModelChoiceField(queryset=Role.objects.filter(is_active=True), widget=bootstrap.Select())

    class Meta:
        model = ApplicationRole
        fields = (
            'role',
            'is_inheritable_by_org_admin',
            'is_inheritable_by_global_admin',
            'is_organisation_related',
        )
        widgets = {
            'is_inheritable_by_org_admin': bootstrap.CheckboxInput(),
            'is_inheritable_by_global_admin': bootstrap.CheckboxInput(),
            'is_organisation_related': bootstrap.CheckboxInput(),
        }


class ApplicationAdminForm(BaseTabularInlineForm):
    admin_email = forms.CharField(max_length=254, label=_('Email'), widget=bootstrap.TextInput(attrs={'size': 50}))
    name = bootstrap.ReadOnlyField(label=_('Name'), initial='')

    form_text = _("Application Admin ")

    class Meta:
        model = ApplicationAdmin
        fields = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            admin = self.instance.admin
            self.fields['admin_email'].initial = admin.primary_email()
            self.fields['name'].initial = "%s %s" % (admin.first_name, admin.last_name)
        except ObjectDoesNotExist:
            pass

    def clean_admin_email(self):
        admin_email = self.cleaned_data['admin_email']
        if not get_user_model().objects.filter(useremail__email=admin_email).exists():
            msg = _('The user does not exists')
            raise ValidationError(msg)

        return admin_email

    def save(self, commit=True):
        if 'admin_email' in self.changed_data:
            admin_email = self.cleaned_data['admin_email']
            admin = get_user_model().objects.get(useremail__email=admin_email)
            self.instance.admin = admin
            add_app_admin_group(user=admin)
        instance = super().save(commit)
        return instance


class ClientForm(BaseForm):
    codename = 'app_admin_access_all_users'
    can_access_all_users = forms.BooleanField(label=_('Can access all users'), required=False, widget=bootstrap.CheckboxInput())
    type = forms.ChoiceField(label=_('Type'), help_text=mark_safe_lazy(_(
        "Confidential or public client for <a href='https://openid.net/specs/openid-connect-core-1_0.html#CodeFlowSteps'>authorisation code flow</a> or service account client "
        "with <a href='https://datatracker.ietf.org/doc/html/rfc6749#section-4.4'>client credentials grant</a>.")),
                             required=True, choices=ALLOWED_CLIENT_TYPES, widget=bootstrap.Select())
    uuid = forms.UUIDField(label=_('Client ID'), required=True, initial=uuid.uuid4, widget=bootstrap.TextInput(attrs={'readonly': True}))
    scopes = forms.MultipleChoiceField(label=_('Scopes'), required=False, initial=['openid'], choices=ALLOWED_SCOPES, widget=bootstrap.Select2Multiple())

    class Meta:
        model = Client
        fields = ('application', 'uuid', 'client_secret', 'name', 'type', 'redirect_uris', 'post_logout_redirect_uris', 'notes', 'is_active', 'scopes')
        widgets = {
            'application': bootstrap.HiddenInput(),
            'name': bootstrap.TextInput(attrs={'size': 50}),
            'client_secret': bootstrap.TextInput(attrs={'readonly': True}),
            'notes': bootstrap.Textarea(attrs={'rows': '3'}),
            'redirect_uris': bootstrap.Textarea(attrs={'rows': '3'}),
            'post_logout_redirect_uris': bootstrap.Textarea(attrs={'rows': '3'}),
            'is_active': bootstrap.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')  # remove custom user keyword
        # initialize scopes
        if kwargs.get('instance'):
            instance = kwargs['instance']
            if instance.scopes:
                kwargs['initial']['scopes'] = instance.scopes.split()
            if instance.user and instance.user.has_perm(f'accounts.{self.codename}'):
                kwargs['initial']['can_access_all_users'] = True

        super().__init__(*args, **kwargs)

    def clean_scopes(self):
        scopes = self.cleaned_data['scopes']
        return ' '.join(scopes)

    def clean(self):
        cleaned_data = super().clean()
        client_type = cleaned_data.get("type")
        client_secret = cleaned_data.get("client_secret")
        redirect_uris = cleaned_data.get("redirect_uris")
        if client_type in ['web', 'service']:
            if not client_secret:
                self.add_error('client_secret', ValidationError("A client secret is required for this client type."))
        if client_type == "native":
            cleaned_data['client_secret'] = ''
        if client_type in ['web', 'native']:
            if not redirect_uris:
                self.add_error('redirect_uris', ValidationError("A redirect uri is required for this client type."))
        else:
            cleaned_data['redirect_uris'] = ''
            cleaned_data['post_logout_redirect_uris'] = ''
        return self.cleaned_data

    def save(self, commit=True):
        instance = super().save(commit)
        user = instance.user
        can_access_all_users = self.cleaned_data['can_access_all_users']

        # service clients need a user associated with
        if self.instance.type == 'service':
            if user is None:
                first_name = instance.name
                last_name = "Service"
                username = default_username_generator(first_name, last_name)
                user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name, is_service=True)
                instance.user = user
                instance.save()

            # modify the service account permission to access all users
            # only if the current user has access to all users
            if self.user.is_global_user_admin or self.user.is_global_app_user_admin:
                if user.has_perm(f'accounts.{self.codename}') != can_access_all_users:
                    content_type = ContentType.objects.get_for_model(User)
                    permission = Permission.objects.get(codename=self.codename, content_type=content_type)
                    if can_access_all_users:
                        user.user_permissions.add(permission)
                    else:
                        user.user_permissions.remove(permission)
        else:
            if user is not None:
                if Client.objects.filter(user=user).exclude(pk=instance.pk).count() == 0:
                    user.delete()
                else:
                    instance.user = None
                    instance.save()

        return instance
