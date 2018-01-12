# -*- coding: utf-8 -*-

import logging
from urllib.parse import urlparse

from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse
from django.utils.translation import ugettext as _
from sso.utils.http import *  # @UnusedWildImport

logger = logging.getLogger(__name__)


def same_origin(url1, url2):
    """
    from: django 1.8 (missing in 1.9.rc1)
    Checks if two URLs are 'same-origin'
    """
    PROTOCOL_TO_PORT = {
        'http': 80,
        'https': 443,
    }
    p1, p2 = urlparse(url1), urlparse(url2)
    try:
        o1 = (p1.scheme, p1.hostname, p1.port or PROTOCOL_TO_PORT[p1.scheme])
        o2 = (p2.scheme, p2.hostname, p2.port or PROTOCOL_TO_PORT[p2.scheme])
        return o1 == o2
    except (ValueError, KeyError):
        return False


class JsonHttpResponse(HttpResponse):
    def __init__(self, data=None, request=None, status=None, allow_jsonp=False, public_cors=False, *args, **kwargs):
        # for security reasons, allow jsonp only for certain resources with more or less public data
        callback = None
        if status == HTTP_401_UNAUTHORIZED:
            allow_jsonp = True  # jsonp can not handle http errors

        if allow_jsonp and request:
            callback = request.GET.get('callback', None)
        if callback:
            status = HTTP_200_OK
            content = u"%s(%s)" % (callback, json.dumps(data, cls=DjangoJSONEncoder, ensure_ascii=False))
        else:
            content = json.dumps(data, cls=DjangoJSONEncoder, ensure_ascii=False)

        super(JsonHttpResponse, self).__init__(content, status=status, content_type='application/json; charset=utf-8;',
                                               *args, **kwargs)

        if request:
            origin = request.META.get('HTTP_ORIGIN')
            if origin:
                if public_cors:
                    self['Access-Control-Allow-Origin'] = '*'
                elif request.client:
                    for redirect_uri in request.client.redirect_uris.split():
                        if same_origin(redirect_uri, origin):
                            self['Access-Control-Allow-Origin'] = origin
                            break


class HttpApiErrorResponse(JsonHttpResponse):
    status_code = 500

    def __init__(self, error="server_error", error_description="", error_uri="", state="", request=None,
                 status_code=500, *args, **kwargs):
        self.status_code = status_code
        content = {'error': error, 'code': self.status_code}

        if error_description:
            content["error_description"] = error_description
        if error_uri:
            content["error_uri"] = error_uri
        if state:
            content["state"] = state

        super(HttpApiErrorResponse, self).__init__(content, status=self.status_code, request=request, *args, **kwargs)


class HttpApiResponseNotAuthorized(HttpApiErrorResponse):
    def __init__(self, error_description=_('The request requires user authentication'), request=None, status_code=401,
                 *args, **kwargs):
        super(HttpApiResponseNotAuthorized, self).__init__(error='not_authorized', error_description=error_description,
                                                           request=request, status_code=status_code, *args, **kwargs)
        self['Access-Control-Allow-Headers'] = 'Authorization'
