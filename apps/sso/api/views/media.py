# -*- coding: utf-8 -*-
from mimetypes import guess_extension
from django.views.decorators.csrf import csrf_exempt
from django.core.urlresolvers import reverse
from django.utils.crypto import get_random_string
from django.core.files.base import ContentFile
from django.utils.decorators import method_decorator
from django.db import transaction
from sso.api.decorators import catch_errors
from sso.api.views.generic import JsonDetailView
from sso.accounts.models import User
from sso.api.decorators import condition
from sso.api.views.users_v2 import get_permission
from utils.url import base_url, absolute_url

import logging

logger = logging.getLogger(__name__)


def get_last_modified_and_etag(request, uuid):
    obj = User.objects.get(uuid=uuid)
    last_modified = obj.last_modified
    etag = "%s/%s" % (uuid, obj.last_modified)
    return last_modified, etag       


def get_last_modified_and_etag_for_me(request, *args, **kwargs):
    if request.user.is_authenticated():
        return get_last_modified_and_etag(request, request.user.uuid)
    else:
        return None, None


def modify_permission(request, obj):
    """
    user is the authenticted user
    permission to change user the obj
    """
    if 'picture' in request.scopes:
        user = request.user
        if user.is_authenticated():
            if user.uuid == obj.uuid:
                return True
            else:
                return user.has_perm('accounts.change_user') and user.has_user_access(obj.uuid)
    return False


class UserPictureDetailView(JsonDetailView):
    model = User
    http_method_names = ['get', 'post', 'delete', 'options']  # , 'add', 'delete'
    permissions_tests = {
        'get': get_permission,
        'put': modify_permission,
        'delete': modify_permission,
    }
    operation = {
        'put': {'@type': 'CreateResourceOperation', 'method': 'POST'},
        'delete': {'@type': 'DeleteResourceOperation', 'method': 'DELETE'},
    }
            
    @method_decorator(csrf_exempt)
    @method_decorator(catch_errors)  
    @method_decorator(condition(last_modified_and_etag_func=get_last_modified_and_etag))
    def dispatch(self, request, *args, **kwargs):
        return super(UserPictureDetailView, self).dispatch(request, *args, **kwargs)       

    def get_object_data(self, request, obj):
        base = base_url(request)
        data = {
            '@id': "%s%s" % (base, reverse('api:v2_picture', kwargs={'uuid': obj.uuid})),
            'id': u'%s' % obj.uuid,
            'last_modified': obj.last_modified,
            'max_size': User.MAX_PICTURE_SIZE
        }
        if obj.picture:
            data['original'] = absolute_url(request, obj.picture.url)
        return data

    def delete_object(self, request, obj):
        obj.picture.delete(save=False)
        obj.save(update_fields=['last_modified', 'picture'])
        
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        # because we have an user object which is updated
        # and the put permission test takes an object as argument.
        # TODO: Cleanup design 
        self.check_permission('put', self.object) 
        
        content_length = int(request.META['CONTENT_LENGTH'])
        if (content_length <= 0):
            raise ValueError('content_lenght <= 0')
        if (content_length > User.MAX_PICTURE_SIZE):
            raise ValueError('content_lenght exceeds maximum of %d.' % User.MAX_PICTURE_SIZE)
        
        content_type = request.META['CONTENT_TYPE']
        if not content_type.startswith("image"):
            raise ValueError("unsupported content type %s. content type must be of type image/*" % request.META['CONTENT_TYPE'])
        
        file_ext = guess_extension(content_type)
        if not file_ext:
            raise ValueError("unsupported content type %s" % request.META['CONTENT_TYPE'])
        
        image_file_name = "%s%s" % (get_random_string(7, allowed_chars='abcdefghijklmnopqrstuvwxyz0123456789'), file_ext)
    
        # update the database at the end
        self.object.picture.delete(save=False)
        self.object.picture.save(image_file_name, ContentFile(request.body), save=False)
        self.object.save(update_fields=['last_modified', 'picture'])
        
        context = self.get_context_data(object=self.object)
        response = self.render_to_response(context, status=201)
        response['Access-Control-Allow-Origin'] = request.META.get('HTTP_ORIGIN')
        response['Location'] = self.object.picture.url
        return response
    

class MyUserPictureDetailView(UserPictureDetailView):
    
    operation = {
        'put': {'@type': 'CreateResourceOperation', 'method': 'POST'},
        'delete': {'@type': 'DeleteResourceOperation', 'method': 'DELETE'},
    }

    @method_decorator(csrf_exempt)
    @method_decorator(catch_errors)  
    @method_decorator(condition(last_modified_and_etag_func=get_last_modified_and_etag_for_me))
    def dispatch(self, request, *args, **kwargs):
        return super(UserPictureDetailView, self).dispatch(request, *args, **kwargs)       

    def get_object(self, queryset=None):
        return self.request.user
