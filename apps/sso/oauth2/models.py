# -*- coding: utf-8 -*-
import urlparse
from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.conf import settings
# from django.contrib.auth.signals import user_logged_in
from django.http import QueryDict
from django.utils.translation import ugettext_lazy as _
from sso.accounts.models import Application
from sso.models import AbstractBaseModel
from django.utils.crypto import get_random_string, salted_hmac

import logging
logger = logging.getLogger(__name__)


def replace_query_param(url, attr, val):    
    (scheme, netloc, path, query, fragment) = urlparse.urlsplit(url)
    query_dict = QueryDict(query).copy()
    query_dict[attr] = val
    query = query_dict.urlencode()
    return urlparse.urlunsplit((scheme, netloc, path, query, fragment))


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
    query_dict = QueryDict(urlparse.urlsplit(redirect_to).query)
    if ('redirect_uri'in query_dict) and ('client_id' in query_dict):
        redirect_uri = query_dict['redirect_uri']
        try:
            client = Client.objects.get(uuid=query_dict['client_id'])
            if check_redirect_uri(client, redirect_uri):
                redirect_uri = replace_query_param(redirect_uri, 'error', 'access_denied')
                return redirect_uri
        except ObjectDoesNotExist:
            pass
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
    ('web', _('Web Application')),  # response_type=code  grant_type=authorization_code or refresh_token
    ('javascript', _('Javascript Application')),  # response_type=token
    ('native', _('Native Application')),  # response_type=code  grant_type=authorization_code or refresh_token redirect_uris=http://localhost or  urn:ietf:wg:oauth:2.0:oob
    ('service', _('Service Account')),  # grant_type=client_credentials
    ('trusted', _('Trusted Client'))  # grant_type=password
]

def get_default_secret():
    return get_random_string(30)


class Client(AbstractBaseModel):
    name = models.CharField(_("name"), max_length=255)
    application = models.ForeignKey(Application, verbose_name=_('application'), blank=True, null=True)
    redirect_uris = models.TextField(_('redirect uris'), blank=True)
    default_redirect_uri = models.CharField(_('default redirect uri'), max_length=2047, blank=True)
    client_secret = models.CharField(_('client secret'), max_length=2047, blank=True, default=get_default_secret)
    # response_type = models.CharField(max_length=255, choices=OAUTH2_RESPONSE_TYPES, help_text="Supported OAuth 2 response type in Authorization Requests")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('user'), null=True, blank=True, help_text=_("Associated user, required for Client Credentials Grant"))
    type = models.CharField(_('type'), max_length=255, choices=CLIENT_TYPES, default='web')
    # http://tools.ietf.org/html/rfc6749#section-3.3
    scopes = models.CharField(_('scopes'), max_length=512, default='openid profile email', help_text=_("Allowed space-delimited access token scopes ('openid', 'profile', 'email', 'offline_access', 'address', 'phone')"))
    
    class Meta(AbstractBaseModel.Meta):
        ordering = ['name']
        
    def __unicode__(self):
        return u"%s" % self.name
            
    @property
    def client_id(self):
        return self.uuid

    def get_session_auth_hash(self):
        key_salt = "sso.oauth2.models.Client"
        return salted_hmac(key_salt, self.client_secret).hexdigest()
        
    def get_absolute_url(self):
        return reverse('oauth2:client.details.json', args=[str(self.id)])

class AuthorizationCode(models.Model):
    """
    OAuth2 Authorization Code
    """
    client = models.ForeignKey(Client, verbose_name=_('client'))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('user'))
    code = models.CharField(_('code'), max_length=100, unique=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    redirect_uri = models.CharField(_('redirect uri'), max_length=2047, blank=True)
    is_valid = models.BooleanField(_('is valid'), default=True)
    state = models.CharField(_('client state'), max_length=2047, blank=True)
    scopes = models.CharField(_('scopes'), max_length=2047, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        get_latest_by = 'created_at'

    def __unicode__(self):
        return u'%s' % self.code


class BearerToken(models.Model):
    """
    OAuth2 Bearer Token
    """
    client = models.ForeignKey(Client, verbose_name=_('client'))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('user'))
    access_token = models.CharField(_('access token'), max_length=2048, unique=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        get_latest_by = 'created_at'

    def __unicode__(self):
        return u'%s - %s' % (self.client, self.user)


class RefreshToken(models.Model):
    """
    A RefreshToken instance represents a token that can be swapped for a new access token when it expires.
    """
    bearer_token = models.OneToOneField(BearerToken, verbose_name=_('bearer token'), related_name='refresh_token')
    token = models.CharField(_('token'), max_length=2048, unique=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    
    @property
    def user(self):
        return self.bearer_token.user
        
    def __unicode__(self):
        return self.token
