# -*- coding: utf-8 -*-
import hashlib
import base64
from binascii import b2a_hex
from django.contrib.auth.hashers import BasePasswordHasher, mask_hash
from django.utils.translation import ugettext_noop as _
from django.utils.crypto import constant_time_compare
from collections import OrderedDict


class OsCommerceMD5PasswordHasher(BasePasswordHasher):
    """
    The Salted MD5 password hashing algorithm (not recommended)
    """
    algorithm = "osc_md5"

    def encode(self, password, salt):
        assert password
        assert salt and '$' not in salt
        for ch in "/[<>]/":
            password = password.replace(ch, '_')
        hash = hashlib.md5(salt + password).hexdigest()  # @ReservedAssignment
        return "%s$%s$%s" % (self.algorithm, salt, hash)

    def verify(self, password, encoded):
        algorithm, salt, hash = encoded.split('$', 2)  # @ReservedAssignment
        assert algorithm == self.algorithm
        encoded_2 = self.encode(password, salt)
        return constant_time_compare(encoded, encoded_2)

    def safe_summary(self, encoded):
        algorithm, salt, hash = encoded.split('$', 2)  # @ReservedAssignment
        assert algorithm == self.algorithm
        return OrderedDict([
            (_('algorithm'), algorithm),
            (_('salt'), mask_hash(salt, show=2)),
            (_('hash'), mask_hash(hash)),
        ])


class MoinSha1PasswordHasher(BasePasswordHasher):
    """
    The SHA1 password hashing algorithm (not recommended)
    compatible with apache and moin
    """
    algorithm = "moin_sha1"

    def encode(self, password, salt):
        assert password
        password = password.encode('utf-8')
        assert isinstance(salt, str)
        hash = hashlib.new('sha1', password)  # @ReservedAssignment
        hash.update(salt)
        encoded = base64.encodestring(hash.digest() + salt).rstrip()
        return "%s$%s" % (self.algorithm, encoded)
        # return '{SSHA}' + base64.encodestring(hash.digest() + salt).rstrip()

    def verify(self, password, encoded):
        algorithm, hash = encoded.split('$', 1)  # @ReservedAssignment
        assert algorithm == self.algorithm
        # data = base64.decodestring(encoded[6:])
        data = base64.decodestring(hash)
        salt = data[20:]
        hash = hashlib.new('sha1', password.encode('utf-8'))  # @ReservedAssignment
        hash.update(salt)
        return hash.digest() == data[:20]
        
    def safe_summary(self, encoded):
        algorithm, hash = encoded.split('$', 1)  # @ReservedAssignment
        assert algorithm == self.algorithm
        data = base64.decodestring(hash)
        
        return OrderedDict([
            (_('algorithm'), self.algorithm),
            (_('salt'), mask_hash(b2a_hex(data[20:]), show=2)),
            (_('hash'), mask_hash(b2a_hex(data[:20]))),
        ])
