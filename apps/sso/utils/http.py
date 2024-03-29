import json
from urllib.parse import urlparse

from django.core.exceptions import DisallowedRedirect

from django.http import HttpResponse
# from django.test.client import JSON_CONTENT_TYPE_RE
from django.utils.encoding import iri_to_uri


def get_request_param(request, name, default=None):
    return request.POST.get(name, request.GET.get(name, default))


def parse_json(request, **extra):
    # if not JSON_CONTENT_TYPE_RE.match(request.content_type):
    #     raise ValueError(
    #         'Content-Type header is "{0}", not "application/json"'
    #         .format(request.content_type)
    #     )
    body =  request.body.decode()
    data = body if body else "{}"
    return json.loads(data, **extra)


class HttpPostLogoutRedirect(HttpResponse):
    # same as HttpResponseRedirect, but without checking the scheme, beause we have custom registered schemes
    status_code = 302

    def __init__(self, redirect_to, allowed_schemes=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self['Location'] = iri_to_uri(redirect_to)
        if allowed_schemes is not None:
            parsed = urlparse(str(redirect_to))
            if parsed.scheme and parsed.scheme not in allowed_schemes:
                raise DisallowedRedirect("Unsafe redirect to URL with protocol '%s'" % parsed.scheme)

    url = property(lambda self: self['Location'])

    def __repr__(self):
        return '<%(cls)s status_code=%(status_code)d%(content_type)s, url="%(url)s">' % {
            'cls': self.__class__.__name__,
            'status_code': self.status_code,
            'content_type': self._content_type_for_repr,
            'url': self.url,
        }


"""
Descriptive HTTP status codes, for code readability.

See RFC 2616 - http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html
And RFC 6585 - http://tools.ietf.org/html/rfc6585
"""

HTTP_100_CONTINUE = 100
HTTP_101_SWITCHING_PROTOCOLS = 101
HTTP_200_OK = 200
HTTP_201_CREATED = 201
HTTP_202_ACCEPTED = 202
HTTP_203_NON_AUTHORITATIVE_INFORMATION = 203
HTTP_204_NO_CONTENT = 204
HTTP_205_RESET_CONTENT = 205
HTTP_206_PARTIAL_CONTENT = 206
HTTP_300_MULTIPLE_CHOICES = 300
HTTP_301_MOVED_PERMANENTLY = 301
HTTP_302_FOUND = 302
HTTP_303_SEE_OTHER = 303
HTTP_304_NOT_MODIFIED = 304
HTTP_305_USE_PROXY = 305
HTTP_306_RESERVED = 306
HTTP_307_TEMPORARY_REDIRECT = 307
HTTP_400_BAD_REQUEST = 400
HTTP_401_UNAUTHORIZED = 401
HTTP_402_PAYMENT_REQUIRED = 402
HTTP_403_FORBIDDEN = 403
HTTP_404_NOT_FOUND = 404
HTTP_405_METHOD_NOT_ALLOWED = 405
HTTP_406_NOT_ACCEPTABLE = 406
HTTP_407_PROXY_AUTHENTICATION_REQUIRED = 407
HTTP_408_REQUEST_TIMEOUT = 408
HTTP_409_CONFLICT = 409
HTTP_410_GONE = 410
HTTP_411_LENGTH_REQUIRED = 411
HTTP_412_PRECONDITION_FAILED = 412
HTTP_413_REQUEST_ENTITY_TOO_LARGE = 413
HTTP_414_REQUEST_URI_TOO_LONG = 414
HTTP_415_UNSUPPORTED_MEDIA_TYPE = 415
HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE = 416
HTTP_417_EXPECTATION_FAILED = 417
HTTP_428_PRECONDITION_REQUIRED = 428
HTTP_429_TOO_MANY_REQUESTS = 429
HTTP_431_REQUEST_HEADER_FIELDS_TOO_LARGE = 431
HTTP_500_INTERNAL_SERVER_ERROR = 500
HTTP_501_NOT_IMPLEMENTED = 501
HTTP_502_BAD_GATEWAY = 502
HTTP_503_SERVICE_UNAVAILABLE = 503
HTTP_504_GATEWAY_TIMEOUT = 504
HTTP_505_HTTP_VERSION_NOT_SUPPORTED = 505
HTTP_511_NETWORK_AUTHENTICATION_REQUIRED = 511
