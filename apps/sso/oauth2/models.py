import logging
from urllib.parse import urlparse, urlsplit, urlunsplit

from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.http import QueryDict
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.encoding import force_str
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from sso.accounts.models import Application, User, ApplicationAdmin
from sso.auth.models import Device
from sso.models import AbstractBaseModel, AbstractBaseModelManager
from sso.registration import default_username_generator

logger = logging.getLogger(__name__)


def replace_query_param(url, attr, val):
    (scheme, netloc, path, query, fragment) = urlsplit(url)
    query_dict = QueryDict(query).copy()
    query_dict[attr] = val
    query = query_dict.urlencode()
    return urlunsplit((scheme, netloc, path, query, fragment))


def check_redirect_uri(client, redirect_uri):
    if redirect_uri in client.redirect_uris.split():
        return True
    else:
        return False


def get_oauth2_cancel_url(redirect_to):
    """
    If the redirect_to parameter comes from OAuth2 it contains a redirect_uri, to
    which we want to redirect if the user cancels login
    """
    query_dict = QueryDict(urlsplit(redirect_to).query)
    if ('redirect_uri' in query_dict) and ('client_id' in query_dict):
        redirect_uri = query_dict['redirect_uri']
        try:
            client = Client.objects.get(uuid=query_dict['client_id'])
            if check_redirect_uri(client, redirect_uri):
                redirect_uri = replace_query_param(redirect_uri, 'error', 'access_denied')
                return redirect_uri
        except (ObjectDoesNotExist, ValidationError, ValueError):
            logger.warning('Invalid client_id %s', query_dict['client_id'])

    return reverse('home')


"""
OAUTH2_RESPONSE_TYPES = [
    ('code', 'Authorization code'),
    ('token', 'Access token')
]
OAUTH2_GRANT_TYPES = [
    ('authorization_code', 'Authorization Code Grant'),
    ('refresh_token', 'Refreshing an Access Token'),
    ('client_credentials', 'Client Credentials Grant'),
    ('password', 'Resource Owner Password Credentials Grant')
]
"""

CLIENT_TYPES = [
    ('web', _('Confidential client')),  # response_type=code  grant_type=authorization_code or refresh_token
    ('javascript', _('Implicit flow')),  # response_type=token
    ('native', _('Public client')),
    # response_type=code  grant_type=authorization_code or refresh_token redirect_uris=http://localhost or
    #  urn:ietf:wg:oauth:2.0:oob
    ('service', _('Service account')),  # grant_type=client_credentials
    ('trusted', _('Trusted client'))  # grant_type=password
]

# selfservice allowed types
ALLOWED_CLIENT_TYPES = [
    ('web', _('Confidential client')),  # response_type=code grant_type=authorization_code or refresh_token
    ('native', _('Public client')),
    # response_type=code  grant_type=authorization_code or refresh_token redirect_uris=http://localhost or
    #  urn:ietf:wg:oauth:2.0:oob
    ('service', _('Service account')),  # grant_type=client_credentials
]

# selfservice allowed scopes
ALLOWED_SCOPES = [
    ('openid', 'openid'),
    ('profile', 'profile'),
    ('email', 'email'),
    ('role', 'role'),
    # ('role_profile', 'role_profile'),  # there can be private role profiles
    ('offline_access', 'offline_access'),
    ('address', 'address'),
    ('phone', 'phone'),
    ('picture', 'picture'),
    ('events', 'events'),
    ('users', 'users'),
]

CLIENT_RESPONSE_TYPES = {
    'web': ['code'],
    'javascript': ["id_token token", "token", "id_token"],
    'native': ['code']
}

CONFIDENTIAL_CLIENTS = ['web', 'service', 'trusted']


def get_clients_by_response_type(response_type):
    clients = []
    client_types = dict(CLIENT_TYPES)
    for client in CLIENT_RESPONSE_TYPES:
        if response_type in CLIENT_RESPONSE_TYPES[client]:
            clients.append(force_str(client_types[client]))
    return clients


def get_default_secret():
    return get_random_string(30)


class ClientManager(AbstractBaseModelManager):
    def get_allowed_hosts(self):
        """
        all host from active client redirect_uris and default_redirect_uri are allowed
        """
        hosts = cache.get('allowed_hosts')
        if hosts is None:
            hosts = {settings.SSO_DOMAIN}
            for client in self.filter(is_active=True):
                redirect_uris = client.redirect_uris.split() + [client.default_redirect_uri]
                for redirect_uri in redirect_uris:
                    if redirect_uri:
                        netloc = urlparse(redirect_uri)[1]
                        if netloc:
                            hosts.add(netloc)
            cache.set('allowed_hosts', hosts)

        return hosts

    def get_post_logout_redirect_uris(self):
        post_logout_redirect_uris = cache.get('post_logout_redirect_uris')
        if post_logout_redirect_uris is None:
            post_logout_redirect_uris = set()
            for client in self.filter(is_active=True):
                for post_logout_redirect_uri in client.post_logout_redirect_uris.split():
                    if post_logout_redirect_uri:
                        post_logout_redirect_uris.add(post_logout_redirect_uri)
            cache.set('post_logout_redirect_uris', post_logout_redirect_uris)

        return post_logout_redirect_uris


def allowed_hosts():
    return Client.objects.get_allowed_hosts()


def post_logout_redirect_uris():
    return Client.objects.get_post_logout_redirect_uris()


class Client(AbstractBaseModel):
    access_to_all_users_permissions = ("access_all_users", "read_user")
    name = models.CharField(_("name"), max_length=255)
    application = models.ForeignKey(Application, on_delete=models.SET_NULL, verbose_name=_('application'), blank=True,
                                    null=True)
    redirect_uris = models.TextField(_('redirect uris'), help_text=_('Whitespace separated list of redirect uris.'), blank=True)
    post_logout_redirect_uris = models.TextField(
        _('post logout redirect uris'),
        help_text=mark_safe(_('Whitespace separated list of '
                              '<a href="https://openid.net/specs/openid-connect-rpinitiated-1_0.html#ClientMetadata">post logout redirect uris</a>.')),
        blank=True)
    default_redirect_uri = models.CharField(_('default redirect uri'), max_length=2047, blank=True)
    client_secret = models.CharField(_('client secret'), max_length=2047, blank=True, default=get_default_secret)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, verbose_name=_('user'), null=True,
                             blank=True, limit_choices_to={'is_service': True},
                             help_text=_("Associated user, required for Client Credentials Grant"))
    type = models.CharField(_('type'), max_length=255, choices=CLIENT_TYPES, default='web')
    # http://tools.ietf.org/html/rfc6749#section-3.3
    scopes = models.CharField(_('scopes'), max_length=512, blank=True, default='openid profile email',
                              help_text=_(
                                  "Allowed space-delimited access token scopes ('openid', 'profile', 'email', 'role', "
                                  "'role_profile', 'offline_access', 'address', 'phone', 'users', 'picture', 'events', 'tt')"
                              ))
    is_active = models.BooleanField(_('active'), default=True,
                                    help_text=_(
                                        'Designates whether this client should be treated as active. Unselect this '
                                        'instead of deleting clients.'))
    notes = models.TextField(_("Notes"), blank=True, max_length=2048)
    is_trustworthy = models.BooleanField(_("trustworthy"), default=False)
    force_using_pkce = models.BooleanField(
        _('force using PKCE'), default=False,
        help_text=mark_safe(_('Enforce Proof Key for Code Exchange <a href="https://tools.ietf.org/html/rfc7636">https://tools.ietf.org/html/rfc7636</a>')))

    objects = ClientManager()

    class Meta(AbstractBaseModel.Meta):
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def client_id(self):
        return self.uuid.hex

    def get_absolute_url(self):
        return reverse('oauth2:client.details.json', args=[str(self.id)])

    @property
    def has_supported_client_type(self):
        allowed_client_types = {x[0] for x in ALLOWED_CLIENT_TYPES}
        return self.type in allowed_client_types

    @property
    def has_supported_scope(self):
        scopes = set(self.scopes.split())
        allowed_scopes = {x[0] for x in ALLOWED_SCOPES}
        return scopes.issubset(allowed_scopes)

    def has_access(self, user, perms=None):
        if not self.has_supported_client_type or not self.has_supported_scope:
            return False
        if perms is None:
            perms = ["oauth2.change_client"]
        if not user.has_perms(perms):
            return False
        if self.has_access_to_all_users:
            # check if user has also access right to all users
            if not user.is_global_user_admin and not user.is_global_app_user_admin:
                return False
        # check if user is admin of the app
        if user.is_global_app_admin:
            return True
        else:
            return user.pk in self.application.applicationadmin_set.all().values_list('admin__pk', flat=True)

    @property
    def has_access_to_all_users(self):
        perm_list = [f'accounts.{perm}' for perm in self.access_to_all_users_permissions]
        return self.user and self.user.has_perms(perm_list)

    def set_access_to_all_users(self, access_all_users, user):
        if self.type != 'service':
            logger.warning("set_access_to_all_users is only relevant for clients of type service")
            return
        if not user.is_global_user_admin and not user.is_global_app_user_admin:
            logger.warning("set_access_to_all_users is only allowed for users with global user access")
            return
        self.ensure_service_user_exists()
        content_type = ContentType.objects.get_for_model(User)
        permissions = Permission.objects.filter(codename__in=self.access_to_all_users_permissions, content_type=content_type)
        if access_all_users:
            self.user.user_permissions.add(*permissions)
        else:
            self.user.user_permissions.remove(*permissions)

    def ensure_service_user_exists(self):
        if self.type != 'service':
            logger.warning("service user is only relevant for clients of type service")
            return
        if self.user is None:
            first_name = self.name
            last_name = "Service"
            username = default_username_generator(first_name, last_name)
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name, is_service=True)
            self.user = user
            self.save(update_fields=['user', 'last_modified'])

    def remove_service_user(self):
        if self.type == 'service':
            logger.warning("service user is required for clients of type service")
            return
        if self.user is not None:
            if Client.objects.filter(user=self.user).exclude(pk=self.pk).count() == 0:
                self.user.delete()
            else:
                self.user = None
                self.save(update_fields=['user', 'last_modified'])


class AuthorizationCode(models.Model):
    """
    OAuth2 Authorization Code
    """
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name=_('client'))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_('user'))
    otp_device = models.ForeignKey(Device, null=True, on_delete=models.SET_NULL)
    code = models.CharField(_('code'), max_length=100, unique=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    redirect_uri = models.CharField(_('redirect uri'), max_length=2047, blank=True)
    is_valid = models.BooleanField(_('is valid'), default=True)
    state = models.CharField(_('client state'), max_length=2047, blank=True)
    scopes = models.CharField(_('scopes'), max_length=2047, blank=True)
    code_challenge = models.CharField(_('code_challenge'), max_length=128, blank=True)
    code_challenge_method = models.CharField(_('code_challenge_method'), max_length=4, blank=True)
    nonce = models.CharField(_('Nonce'), max_length=2047, blank=True)

    class Meta:
        ordering = ['-created_at']
        get_latest_by = 'created_at'

    def __str__(self):
        return self.code


class BearerToken(models.Model):
    """
    OAuth2 Bearer Token
    """
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name=_('client'))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_('user'))
    access_token = models.CharField(_('access token'), max_length=2048, unique=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        get_latest_by = 'created_at'

    def __str__(self):
        return '%s - %s' % (self.client, self.user)


class RefreshToken(models.Model):
    """
    A RefreshToken instance represents a token that can be swapped for a new access token when it expires.
    """
    bearer_token = models.OneToOneField(BearerToken, on_delete=models.CASCADE, verbose_name=_('bearer token'),
                                        related_name='refresh_token')
    token = models.CharField(_('token'), max_length=2048, unique=True)
    # otp_device = models.ForeignKey(Device, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    @property
    def user(self):
        return self.bearer_token.user

    def __str__(self):
        return self.token
