import logging
from base64 import b64encode, urlsafe_b64encode
from datetime import timedelta

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509 import OID_COMMON_NAME

from django.conf import settings
from django.core.cache import cache
from django.core.management.utils import get_random_secret_key
from django.db import transaction
from django.utils.encoding import force_str
from django.utils.timezone import now
from sso.components.models import ComponentConfig, Component

logger = logging.getLogger(__name__)

_ENCODING_KEYS = {'RS256': 'PRIVATE_KEY', 'HS256': 'SECRET_KEY'}
_DECODING_KEYS = {'RS256': 'PUBLIC_KEY', 'HS256': 'SECRET_KEY'}
_CACHE_KEY_LATEST_ENCODING_KEY = "latest_encoding_key_and_kid.{0}"
_CACHE_KEY_SIGNING_CERTS = "signing_certs"
_CACHE_KEY_SIGNING_CERTS_JWKS = "signing_certs_jwks"
_CACHE_KEY_PUBLIC_KEYS = "public_keys"
_CACHE_KEY_DEFAULT_SIGNING_CERT = "default_signing_cert"


def clear_cache(algorithm=None):
    if algorithm is None:
        for algorithm in ['RS256', 'HS256']:
            clear_cache(algorithm)
    else:
        cache.delete(_CACHE_KEY_LATEST_ENCODING_KEY.format(algorithm))
        if algorithm == 'RS256':
            cache.delete(_CACHE_KEY_SIGNING_CERTS)
            cache.delete(_CACHE_KEY_SIGNING_CERTS_JWKS)
            cache.delete(_CACHE_KEY_DEFAULT_SIGNING_CERT)
            cache.delete(_CACHE_KEY_PUBLIC_KEYS)


def create_rs_key(algorithm_obj):
    # create a new private key
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    value = force_str(key.private_bytes(encoding=serialization.Encoding.PEM,
                                        format=serialization.PrivateFormat.PKCS8,
                                        encryption_algorithm=serialization.NoEncryption()))

    # get the public key
    pub_key_obj = key.public_key()
    pub_value = force_str(pub_key_obj.public_bytes(encoding=serialization.Encoding.PEM,
                                                   format=serialization.PublicFormat.SubjectPublicKeyInfo))
    ComponentConfig.objects.create(component=algorithm_obj, name=_DECODING_KEYS[algorithm_obj.name], value=pub_value)

    # create the certificate
    subject = issuer = x509.Name([x509.NameAttribute(OID_COMMON_NAME, settings.SSO_DOMAIN)])
    cert_builder = x509.CertificateBuilder().subject_name(subject).issuer_name(issuer)
    cert_builder = cert_builder.not_valid_before(algorithm_obj.created_at).not_valid_after(
        now() + timedelta(seconds=3 * settings.SSO_SIGNING_KEYS_VALIDITY_PERIOD))
    kid = algorithm_obj.uuid.hex
    cert = cert_builder.serial_number(int(kid, 16)).public_key(pub_key_obj).sign(key, hashes.SHA256())
    cert_value = force_str(cert.public_bytes(serialization.Encoding.PEM))
    ComponentConfig.objects.create(component=algorithm_obj, name='CERTIFICATE', value=cert_value)
    return value


@transaction.atomic
def create_key(algorithm, rotate=True):
    algorithm_obj = Component.objects.create(name=algorithm)
    name = _ENCODING_KEYS[algorithm]

    # create a new private key
    if algorithm == 'HS256':
        value = get_random_secret_key()
    elif algorithm == 'RS256':
        value = create_rs_key(algorithm_obj)
    else:
        raise ValueError(f'algorithm {algorithm} not supported')

    key_obj = ComponentConfig.objects.create(component=algorithm_obj, name=name, value=value)
    ComponentConfig.objects.create(component=algorithm_obj, name='ACTIVE', value='True')

    active_algos = Component.objects.filter(name=algorithm, componentconfig__name='ACTIVE', componentconfig__value='True').order_by('-created_at')
    # rotate signing keys
    if rotate:
        # if there are more than 1 ACTIVE set the 2-nd ACTIVE as the default
        if active_algos.count() > 1:
            default_algo = active_algos[1]
        else:
            default_algo = algorithm_obj

        # create new default
        ComponentConfig.objects.update_or_create(component=default_algo, name='DEFAULT', defaults={'value': 'True'})
        # and delete previous DEFAULT value
        ComponentConfig.objects.filter(component__name=algorithm, name='DEFAULT', value='True').exclude(component=default_algo).delete()

    # keep only 3 keys active
    for component in active_algos[3:]:
        ComponentConfig.objects.filter(component=component, name='ACTIVE').delete()

    # delete old inactive ḱeys
    inactive_algos = Component.objects.filter(name=algorithm).exclude(componentconfig__name='ACTIVE', componentconfig__value='True').order_by('-created_at')
    for component in inactive_algos[3:]:
        component.delete()

    clear_cache(algorithm)
    logger.info(f"Created new {algorithm} key with kid {key_obj.component.uuid.hex}")
    return key_obj


def _get_key_by_kid_and_name(kid, name):
    def get_kid_value():
        try:
            return ComponentConfig.objects.get(component__uuid=kid, name=name).value
        except ComponentConfig.DoesNotExist:
            raise ValueError(f"Key with {kid} does not exist")

    return cache.get_or_set(f"{kid}.{name}", get_kid_value, 60 * 60 * 24 * 360)  # cache for 1 Year


def get_encoding_key_by_kid(kid, algorithm):
    name = _ENCODING_KEYS[algorithm]
    return _get_key_by_kid_and_name(kid, name)


def get_decoding_key_by_kid(kid, algorithm):
    name = _DECODING_KEYS[algorithm]
    return _get_key_by_kid_and_name(kid, name)


def get_public_keys():
    algorithm = 'RS256'

    def _get_public_keys():
        return ComponentConfig.objects.filter(
            component__in=Component.objects.filter(
                name=algorithm,
                componentconfig__name='ACTIVE',
                componentconfig__value='True'),
            name=_DECODING_KEYS[algorithm]
        ).select_related('component')

    return cache.get_or_set(_CACHE_KEY_PUBLIC_KEYS, _get_public_keys, settings.SSO_SIGNING_KEYS_VALIDITY_PERIOD)


def get_default_cert():
    algorithm = 'RS256'

    def _get_default_cert():
        return ComponentConfig.objects.filter(
            component__in=Component.objects.filter(
                name=algorithm,
                componentconfig__name='DEFAULT',
                componentconfig__value='True'),
            name='CERTIFICATE').select_related('component').order_by('-component__created_at')[0]

    return cache.get_or_set(_CACHE_KEY_DEFAULT_SIGNING_CERT, _get_default_cert, settings.SSO_SIGNING_KEYS_VALIDITY_PERIOD)


def get_certs():
    algorithm = 'RS256'

    def _get_certs():
        return list(ComponentConfig.objects.filter(
            component__in=Component.objects.filter(
                name=algorithm,
                componentconfig__name='ACTIVE',
                componentconfig__value='True'),
            name='CERTIFICATE').select_related('component').order_by('-component__created_at'))

    return cache.get_or_set(_CACHE_KEY_SIGNING_CERTS, _get_certs, settings.SSO_SIGNING_KEYS_VALIDITY_PERIOD)


def get_certs_jwks():
    # get the signing certs in jwks x5c format (base64 encoded DER-format)
    # to get the cert in DER-format from this value with openssl use:
    # openssl base64 -d -A -in x5c-file -out certificate.der
    def _get_certs_jwks():
        certs = {}
        for cert in get_certs():
            c = x509.load_pem_x509_certificate(cert.value.encode())
            jwks_cert = {
                'x5t': force_str(urlsafe_b64encode(c.fingerprint(hashes.SHA1()))),
                'x5t#S256': force_str(urlsafe_b64encode(c.fingerprint(hashes.SHA256()))),
                'x5c': force_str(b64encode(x509.load_pem_x509_certificate(cert.value.encode()).public_bytes(serialization.Encoding.DER)))
            }
            certs[cert.component.uuid.hex] = jwks_cert
        return certs

    return cache.get_or_set(_CACHE_KEY_SIGNING_CERTS_JWKS, _get_certs_jwks, settings.SSO_SIGNING_KEYS_VALIDITY_PERIOD)


def get_default_encoding_key_and_kid(algorithm):
    def get_or_create_key():
        try:
            key = ComponentConfig.objects.filter(
                component__in=Component.objects.filter(
                    name=algorithm,
                    # created_at__gt=now() - timedelta(seconds=settings.SSO_SIGNING_KEYS_VALIDITY_PERIOD),
                    componentconfig__name='DEFAULT',
                    componentconfig__value='True'),
                name=_ENCODING_KEYS[algorithm]).select_related('component').latest()
        except ComponentConfig.DoesNotExist:
            key = create_key(algorithm)
        return key

    cache_key = _CACHE_KEY_LATEST_ENCODING_KEY.format(algorithm)
    key_obj = cache.get_or_set(cache_key, get_or_create_key, settings.SSO_SIGNING_KEYS_VALIDITY_PERIOD)
    return key_obj.value, key_obj.component.uuid.hex


def get_secret(kid=None):
    if kid is None:
        secret, _ = get_default_encoding_key_and_kid('HS256')
    else:
        secret = get_encoding_key_by_kid(kid, 'HS256')
    return secret
