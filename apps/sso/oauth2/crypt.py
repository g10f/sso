# -*- coding: utf-8 -*-
import json
import time
import os
import base64

from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA

from django.conf import settings
from django.core.signing import BadSignature


import logging
logger = logging.getLogger(__name__)

SUPPORTED_SCOPES = ['openid', 'profile', 'email', '']
DEFAULT_SCOPES = ['profile']
CLOCK_SKEW_SECS = 300    # 5 minutes in seconds
AUTH_TOKEN_LIFETIME_SECS = 300    # 5 minutes in seconds
MAX_TOKEN_LIFETIME_SECS = 86400    # 1 day in seconds

class PrivateKey(object):
    def __init__(self):  
        if not hasattr(settings, 'PRIVATE_KEY_FILE_ID'):
            self.key_id = 'f1aafae7b7764055926078b32fe81e5b'
            private_key_file = os.path.join(settings.DIRNAME, 'cert', '%s.key' % self.key_id)
            if not os.path.exists(private_key_file):
                raise Exception("private_key_file %s does not exist" % private_key_file)
        
        self.private_key_file = private_key_file        
    
    @property
    def rsa(self):
        if not hasattr(self, '_rsa'):
            with open(self.private_key_file, 'r') as f:
                self._rsa = RSA.importKey(f.read())            
        return self._rsa
    
    @property
    def cert(self):
        cert_file = os.path.join(settings.DIRNAME, 'cert', '%s.crt' % self.key_id)
        with open(cert_file, 'r') as f:
            return f.read()
        
    @property
    def pub_key(self):
        cert_file = os.path.join(settings.DIRNAME, 'cert', '%s.pub' % self.key_id)
        with open(cert_file, 'r') as f:
            return f.read()

    @property
    def id(self):
        return self.key_id

    @property
    def public_rsa(self):
        cert_file = os.path.join(settings.DIRNAME, 'cert', '%s.pub' % self.key_id)        
        with open(cert_file, 'r') as f:
            return RSA.importKey(f.read())
        
    def sign(self, message):
        return  PKCS1_v1_5.new(self.rsa).sign(SHA256.new(message))
    
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
    if not "iat" in claim_set:
        claim_set["iat"] = int(time.time())  # add  issued at time 

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

    if (len(segments) != 3):
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
