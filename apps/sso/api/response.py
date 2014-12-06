# -*- coding: utf-8 -*-
import json

from django.core.serializers.json import DjangoJSONEncoder
from django.utils.http import same_origin
from django.http import HttpResponse
from django.utils.translation import ugettext as _
from http.http_status import *  # @UnusedWildImport

import logging

logger = logging.getLogger(__name__)

class JsonHttpResponse(HttpResponse):
    def __init__(self, data="", request=None, status=None, *args, **kwargs):
        callback = ""
        if request:
            callback = request.GET.get('callback', "")
        if callback:
            status = HTTP_200_OK  # jsonp can not handle http errors
            content = u"%s(%s)" % (callback, json.dumps(data, cls=DjangoJSONEncoder))
        else:
            content = json.dumps(data, cls=DjangoJSONEncoder)
        
        super(JsonHttpResponse, self).__init__(content, status=status, content_type='application/json', *args, **kwargs)
        
        if request:
            origin = request.META.get('HTTP_ORIGIN')
            if origin and request.client:
                for redirect_uri in request.client.redirect_uris.split():
                    if same_origin(redirect_uri, origin):
                        self['Access-Control-Allow-Origin'] = origin
                        break
        
    
class HttpApiErrorResponse(JsonHttpResponse):
    status_code = 500
    
    def __init__(self, error="server_error", error_description="", error_uri="", state="", request=None, status_code=500, *args, **kwargs):
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
    
    def __init__(self, error_description=_('The request requires user authentication'), request=None, status_code=401, *args, **kwargs):
        super(HttpApiResponseNotAuthorized, self).__init__(error='not_authorized', error_description=error_description, request=request, status_code=status_code, *args, **kwargs) 
        self['Access-Control-Allow-Headers'] = 'Authorization'     
