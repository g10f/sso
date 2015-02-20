# -*- coding: utf-8 -*-
import json
import time
import base64

from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA

from django.conf import settings
from django.core.signing import BadSignature


import logging
logger = logging.getLogger(__name__)

# SUPPORTED_SCOPES = ['openid', 'profile', 'email', '']
# DEFAULT_SCOPES = ['profile']
CLOCK_SKEW_SECS = 300    # 5 minutes in seconds
AUTH_TOKEN_LIFETIME_SECS = 300    # 5 minutes in seconds
MAX_TOKEN_LIFETIME_SECS = 86400    # 1 day in seconds
MAX_AGE = 3600  # one hour

class PrivateKey(object):
    
    @property
    def rsa(self):
        if not hasattr(self, '_rsa'):
            self._rsa = RSA.importKey(settings.CERTS['default']['private_key'])            
        return self._rsa
    
    @property
    def cert(self):
        return settings.CERTS['default']['certificate']
        
    @property
    def pub_key(self):
        return settings.CERTS['default']['public_key']

    @property
    def id(self):
        return settings.CERTS['default']['uuid']

    @property
    def public_rsa(self):
        return RSA.importKey(self.pub_key)
        
    def sign(self, message):
        return PKCS1_v1_5.new(self.rsa).sign(SHA256.new(message))
    
    def verify(self, message, signature):
        return PKCS1_v1_5.new(self.rsa).verify(SHA256.new(message), signature)  
        
key = PrivateKey()

def cert():
    return key.cert()


def pub_key():
    return key.pub_key()


def _urlsafe_b64encode(raw_bytes):
    return base64.urlsafe_b64encode(raw_bytes).rstrip('=')


def _urlsafe_b64decode(b64string):
    # Guard against unicode strings, which base64 can't handle.
    b64string = b64string.encode('ascii')
    padded = b64string + '=' * (4 - len(b64string) % 4)
    return base64.urlsafe_b64decode(padded)


def _json_encode(data):
    return json.dumps(data, separators=(',', ':'))


def make_jwt(claim_set):
    """Make a signed JWT.

    See http://self-issued.info/docs/draft-jones-json-web-token.html.

    Args:
        claim_set: dict, Dictionary of data to convert to JSON and then sign.

    Returns:
        string, The JWT for the claim_set.
    """
    header = {"typ": "JWT", "alg": "RS256"}  # JSON Web token with RSA SHA-256 algorithm
    if "iat" not in claim_set:
        claim_set["iat"] = int(time.time())  # add  issued at time
    if "exp" not in claim_set:
        claim_set["exp"] = int(time.time()) + MAX_AGE  # add  issued at time

    segments = [
        _urlsafe_b64encode(_json_encode(header)),
        _urlsafe_b64encode(_json_encode(claim_set)),
    ]
    signing_input = '.'.join(segments)    
    signature = key.sign(signing_input)
    segments.append(_urlsafe_b64encode(signature))
    logger.debug(str(segments))
    return '.'.join(segments)


def loads_jwt(jwt):
    """
    Reverse of make_jwt(), raises BadSignature if signature fails.
    """
    segments = jwt.split('.')

    if len(segments) != 3:
        raise BadSignature('Wrong number of segments in token: %s' % jwt)
    signed = '%s.%s' % (segments[0], segments[1])

    try:
        signature = _urlsafe_b64decode(segments[2])
    except Exception as e:
        raise BadSignature('%s. Can\'t b64decode signature: %s' % (str(e), segments[2]))

    # Parse token.
    json_body = _urlsafe_b64decode(segments[1])
    try:
        parsed = json.loads(json_body)
    except Exception as e:
        raise BadSignature('%s. Can\'t parse token: %s' % (str(e), json_body))
    
    # Check signature.
    if not key.verify(signed, signature):
        raise BadSignature('Invalid token signature: %s' % jwt)

    # Check creation timestamp.
    iat = parsed.get('iat')
    if iat is None:
        raise BadSignature('No iat field in token: %s' % json_body)
    earliest = iat - CLOCK_SKEW_SECS

    # Check expiration timestamp.
    now = long(time.time())
    exp = parsed.get('exp')
    if exp is None:
        raise BadSignature('No exp field in token: %s' % json_body)
    if exp >= now + MAX_TOKEN_LIFETIME_SECS:
        raise BadSignature('exp field too far in future: %s' % json_body)
    latest = exp + CLOCK_SKEW_SECS

    if now < earliest:
        raise BadSignature('Token used too early, %d < %d: %s' % (now, earliest, json_body))
    if now > latest:
        raise BadSignature('Token used too late, %d > %d: %s' % (now, latest, json_body))

    return parsed
