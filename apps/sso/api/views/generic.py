# -*- coding: utf-8 -*-
import json

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http import HttpResponse, Http404
from django.db import transaction
from django.views.generic.detail import BaseDetailView
from django.views.generic.list import BaseListView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.vary import vary_on_headers
from django.forms.models import model_to_dict
from utils.url import base_url, build_url
from sso.api.decorators import catch_errors
from sso.api.response import JsonHttpResponse

import logging

logger = logging.getLogger(__name__)

def is_authenticated(request, obj=None):
    if (not request.user.is_authenticated()):
        return False, 'User not authenticated'
    else:
        return True, None

    
class PermissionMixin(object):
    """
    # the result is of type (boolean, string) where string contains the reason if the result is false
    permissions_tests = {
        'get': lambda request, obj: (True, None),
        'put': lambda request, obj: (True, None),
        'delete': lambda request, obj: (True, None),
        'add': lambda request: (True, None),
    }
    
    operation = {
        'put': {'@type': 'ReplaceResourceOperation', 'method': 'PUT'},
        'delete': {'@type': 'DeleteResourceOperation', 'method': 'DELETE'},
        'post': {'@type': 'CreateResourceOperation', 'method': 'POST'},
        'add': {'@type': 'CreateResourceOperation', 'method': 'PUT', 'template': '{id}'},
    }
    """
    
    permissions_tests = {
        'get': is_authenticated,
    }
    operation = {}
    
    def check_permission(self, method_name, obj=None, raise_exception=True):
        permission_check = self.permissions_tests.get(method_name, None)
        if permission_check:
            if method_name in ['get', 'put', 'delete']:
                is_allowed, reason = permission_check(self.request, obj)
            else:
                is_allowed, reason = permission_check(self.request)
                
            if not is_allowed and raise_exception:
                raise PermissionDenied("method '%s' not allowed, user: '%s', reason '%s'" % (method_name, self.request.user, reason))
            else:
                return is_allowed
        else:
            return True
       
    def get_operation(self):
        return self.operation

    def get_allowed_operation(self, obj=None):
        result = []
        operation = self.get_operation()
        for method_name in operation:
            if self.check_permission(method_name, obj, False):
                result.append(operation[method_name])
        return result


class JSONResponseMixin(object):
    """
    A mixin that can be used to render a JSON response.
    """
    def render_to_json_response(self, context, **response_kwargs):
        """
        Returns a JSON response
        """
        data = self.get_data(context)
        return JsonHttpResponse(data=data, request=self.request, **response_kwargs)        
    
    def get_data(self, context):
        data = self.get_object_data(self.request, context['object'])
        
        if '@id' not in data:
            # if no @id is there we use the current url as the default
            page_base_url = "%s%s" % (base_url(self.request), self.request.path)
            data['@id'] = build_url(page_base_url, self.request.GET)

        data['operation'] = self.get_allowed_operation(context['object'])
        return data
        

class JsonDetailView(JSONResponseMixin, PermissionMixin, BaseDetailView):
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'
    # supported method names from View class
    # http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options', 'trace']

    def render_to_response(self, context, **response_kwargs):
        return self.render_to_json_response(context, **response_kwargs)

    @method_decorator(csrf_exempt)
    @method_decorator(catch_errors)
    def dispatch(self, request, *args, **kwargs):
        return super(JsonDetailView, self).dispatch(request, *args, **kwargs)
        
    def options(self, request, *args, **kwargs):
        """
        check for cors Preflight Request
        See http://www.html5rocks.com/static/images/cors_server_flowchart.png
        """
        # origin is mandatory
        origin = self.request.META.get('HTTP_ORIGIN')
        if not origin:
            return super(JsonDetailView, self).options(request, *args, **kwargs)
        
        # ACCESS_CONTROL_REQUEST_METHOD is optional
        acrm = self.request.META.get('HTTP_ACCESS_CONTROL_REQUEST_METHOD')  
        if acrm:
            if acrm not in self._allowed_methods():
                logger.warning('ACCESS_CONTROL_REQUEST_METHOD %s not allowed' % acrm)
                return super(JsonDetailView, self).options(request, *args, **kwargs)
        
            response = HttpResponse()
            response['Access-Control-Allow-Methods'] = ', '.join(self._allowed_methods())
            response['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
            response['Access-Control-Max-Age'] = 60 * 60
        else:
            #  expose headers to client (optional)
            response = HttpResponse()
            response['Access-Control-Expose-Headers'] = 'Authorization'

        # Because here the client is not authenticated if the browser makes an OPTION request
        # we need Access-Control-Allow-Origin: '*'
        # later in the JsonHttpResponse we check if the origin is from some registered client and
        # set the Access-Control-Allow-Origin more restrictive
        response['Access-Control-Allow-Origin'] = '*'
        return response        

    @method_decorator(vary_on_headers('Access-Control-Allow-Origin', 'Authorization', 'Cookie'))
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()        
        # get_object is needed before check_permission
        self.check_permission('get', self.object)        
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)
    
    @transaction.atomic
    def put(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
            # get_object is needed before check_permission
            self.check_permission('put', self.object)            
            data = json.loads(request.body)
            self.save_object_data(request, data)
            status_code = 200
            self.object = self.get_object()  # update object
            context = self.get_context_data(object=self.object)
            return self.render_to_response(context, status=status_code)
        except Http404, e:
            # add isn't a http method, it is used here as a put for a new resource
            if 'add' in self.http_method_names:   
                handler = getattr(self, 'add', None)
                if handler:
                    return handler(request, *args, **kwargs)
            raise ObjectDoesNotExist(str(e))

    @transaction.atomic
    def add(self, request, *args, **kwargs):
        self.check_permission('add')
        data = json.loads(request.body)
        
        # get the new id for the object
        slug = self.kwargs.get(self.slug_url_kwarg, None)
        data[self.slug_field] = slug
        
        self.object = self.create_object(request, data)
        
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context, status=201)

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
            
            # get_object is needed before check_permission
            self.check_permission('delete', self.object)
            
            self.delete_object(request, self.object)
        except ObjectDoesNotExist:
            pass
        response = HttpResponse(status=204)
        response['Access-Control-Allow-Origin'] = self.request.META.get('HTTP_ORIGIN')
        return response
    
    def create_object(self, request, data):
        """
        custom function to transform the object into an object which can be json rendered
        """
        raise NotImplementedError
        
    def get_object_data(self, request, obj):
        """
        custom function to transform the object into an object which can be json rendered
        """
        return model_to_dict(obj)

    def save_object_data(self, request, data):
        """
        custom function to transform the object into an object which can be json rendered
        """
        raise NotImplementedError

    def delete_object(self, request, obj):
        """
        custom function to transform the object into an object which can be json rendered
        """
        raise NotImplementedError
        

class JsonListView(JSONResponseMixin, PermissionMixin, BaseListView):
    paginate_by = 100
    max_per_page = 1000
    
    @method_decorator(csrf_exempt)
    @method_decorator(catch_errors)  
    def dispatch(self, request, *args, **kwargs):
        return super(JsonListView, self).dispatch(request, *args, **kwargs)
    
    def get_paginate_by(self, queryset):
        paginate_by = int(self.request.GET.get('per_page', self.paginate_by))
        if paginate_by > self.max_per_page:
            raise ValueError("Max per page is %d" % self.max_per_page)
        return paginate_by

    def render_to_response(self, context, **response_kwargs):
        return self.render_to_json_response(context, **response_kwargs)

    def get_data(self, context):
        data = {
            'member': [self.get_object_data(self.request, obj) for obj in context['object_list']],
        }
        page_base_url = "%s%s" % (base_url(self.request), self.request.path)
        self_url = build_url(page_base_url, self.request.GET)
        data['total_items'] = context['paginator'].count
        if context['is_paginated']:
            data['items_per_page'] = context['paginator'].per_page
            
            page = context['page_obj']
            if page.has_next():
                data['next_page'] = build_url(self_url, {'page': page.next_page_number()})
            if page.has_previous():
                data['prev_page'] = build_url(self_url, {'page': page.previous_page_number()})

        data['@id'] = self_url
        data['operation'] = self.get_allowed_operation(None)
        return data

    @method_decorator(vary_on_headers('Access-Control-Allow-Origin', 'Authorization', 'Cookie'))
    def get(self, request, *args, **kwargs):
        # permission check
        self.check_permission('get')

        self.object_list = self.get_queryset()

        allow_empty = self.get_allow_empty()

        if not allow_empty:
            # When pagination is enabled and object_list is a queryset,
            # it's better to do a cheap query than to load the unpaginated
            # queryset in memory.
            if self.get_paginate_by(self.object_list) is not None and hasattr(self.object_list, 'exists'):
                is_empty = not self.object_list.exists()
            else:
                is_empty = len(self.object_list) == 0
            if is_empty:
                raise Http404(_("Empty list and '%(class_name)s.allow_empty' is False.") % {'class_name': self.__class__.__name__})
        context = self.get_context_data()
        return self.render_to_response(context)
    
    def get_object_data(self, request, obj):
        """
        custom function to transform the object into an object which can be json rendered
        """
        return model_to_dict(obj)
