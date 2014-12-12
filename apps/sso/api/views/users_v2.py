# -*- coding: utf-8 -*-
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.utils.dateparse import parse_date
from django.utils.translation import ugettext as _
from django.utils.text import capfirst
from django.db.models import Q
from sorl.thumbnail import get_thumbnail
from utils.url import base_url, absolute_url
from utils.parse import parse_datetime_with_timezone_support
from l10n.models import Country
from sso.accounts.models import UserAddress, UserPhoneNumber, User, send_account_created_email
from sso.registration import default_username_generator
from sso.models import update_object_from_dict, map_dict2dict
from sso.api.views.generic import JsonListView, JsonDetailView
from sso.api.decorators import condition

import logging

logger = logging.getLogger(__name__)

"""
mapping consist of key values, where 

1. the value is the name of the django object field or
2. the value is a dictionary with the name of the django object field and optional a parser and validate function

"""
API_USER_MAPPING = {
    'given_name': {'name': 'first_name', 'validate': lambda x: len(x) > 0},
    'family_name': {'name': 'last_name', 'validate': lambda x: len(x) > 0},
    'email': {'name': 'email', 'validate': lambda x: len(x) > 0},
    'gender': 'gender',
    'birth_date': {'name': 'dob', 'parser': parse_date},
    'homepage': 'homepage',
    'language': 'language',
}
API_ADDRESS_MAP = {
    'address_type': {'name': 'address_type', 'validate': lambda x: len(x) > 0}, 
    'addressee': {'name': 'addressee', 'validate': lambda x: len(x) > 0},
    'street_address': 'street_address',
    'city': {'name': 'city', 'validate': lambda x: len(x) > 0},
    'postal_code': 'postal_code',
    'country': {'name': 'country', 'parser': lambda iso2_code: Country.objects.get(iso2_code=iso2_code)},
    'region': 'region',
    'primary': 'primary'
}
API_PHONE_MAP = {
    'phone_type': 'phone_type',
    'phone': 'phone',
    'primary': 'primary'
}


def get_last_modified(obj):
    last_modified_list = [obj.last_modified]
    last_modified_list += [addr.last_modified for addr in obj.useraddress_set.all()]
    last_modified_list += [phone.last_modified for phone in obj.userphonenumber_set.all()]
    
    last_modified = max(last_modified_list)
    return last_modified


class UserMixin(object):
    model = User
    
    def get_object_data(self, request, obj, details=False):
        scopes = request.scopes
        base = base_url(request)
        data = {
            '@id': "%s%s" % (base, reverse('api:v2_user', kwargs={'uuid': obj.uuid})),
            'id': u'%s' % obj.uuid,
            'is_active': obj.is_active,
            'name': u'%s' % obj,
            'given_name': u'%s' % obj.first_name,
            'family_name': u'%s' % obj.last_name,
            'email': u'%s' % obj.email,
            'gender': obj.gender,
            'birth_date': obj.dob,
            'homepage': obj.homepage,
            'language': obj.language,
            'is_center': obj.is_center,
            'last_modified': get_last_modified(obj),
        } 
        if obj.picture:
            data['picture'] = {
                '@id': "%s%s" % (base, reverse('api:v2_picture', kwargs={'uuid': obj.uuid})),
                'url': absolute_url(request, obj.picture.url)
            }
        
        if details:
            data['organisations'] = {
                organisation.uuid: {
                    'country': organisation.country.iso2_code,
                    'name': organisation.name,
                    '@id': "%s%s" % (base, reverse('api:v2_organisation', kwargs={'uuid': organisation.uuid}))
                } for organisation in obj.organisations.all().prefetch_related('country')
            }
            # data['roles'] = [role.name for role in obj.get_roles_by_app(request.client.application.uuid)]

            if 'role' in scopes:
                applications = {}
                applicationroles = obj.get_applicationroles()
                     
                for application in obj.get_apps():
                    application_data = {'order': application.order,
                                        'link': {'href': application.url, 'title': application.title,
                                                 'global_navigation': application.global_navigation}, 'roles': []}
                    for applicationrole in applicationroles:
                        if applicationrole.application == application:
                            application_data['roles'].append(applicationrole.role.name)
                    
                    applications[application.uuid] = application_data
                data['apps'] = applications
            
            if 'address' in scopes:
                data['addresses'] = {
                    address.uuid: {
                        'address_type': address.address_type,
                        'addressee': address.addressee,
                        'street_address': address.street_address,
                        'city': address.city,
                        'postal_code': address.postal_code,
                        'country': address.country.iso2_code,
                        'region': address.region,
                        'primary': address.primary
                    } for address in obj.useraddress_set.all()
                }
            
            if 'phone' in scopes:
                data['phone_numbers'] = {
                    phone_number.uuid: {
                        'phone_type': phone_number.phone_type,
                        'phone': phone_number.phone,
                        'primary': phone_number.primary
                    } for phone_number in obj.userphonenumber_set.all()
                }
        return data


def get_last_modified_and_etag(request, uuid):
    if request.user.is_authenticated():
        obj = User.objects.prefetch_related('useraddress_set', 'userphonenumber_set').get(uuid=uuid)
        last_modified = get_last_modified(obj)
        etag = "%s/%s" % (uuid, last_modified)
        return last_modified, etag
    else:
        return None, None


def get_last_modified_and_etag_for_me(request, *args, **kwargs):
    if request.user.is_authenticated():
        last_modified = get_last_modified(request.user)
        etag = "%s/%s" % (request.user.uuid, last_modified)
        return last_modified, etag
    else:
        return None, None


def get_permission(request, obj):
    """
    user is the authenticted user
    permission to read the obj data
    """
    user = request.user
    if user.is_authenticated():
        if user.uuid == obj.uuid:
            return True, None
        else:
            if (not user.has_perm('accounts.read_user')):
                return False, "User has no permission '%s" % 'accounts.read_user'
            elif (not user.has_user_access(obj.uuid)):
                return False, "User has no access to object"
            else:
                return True, None
    return False, 'User not authenticated'


def put_permission(request, obj):
    """
    user is the authenticted user
    permission to change user the obj
    """
    user = request.user
    if user.is_authenticated():
        if user.uuid == obj.uuid:
            return True, None
        else:
            if (not user.has_perm('accounts.change_user')):
                return False, "User has no permission '%s" % 'accounts.change_user'
            elif (not user.has_user_access(obj.uuid)):
                return False, "User has no access to object"
            else:
                return True, None
    return False, 'User not authenticated'


class UserDetailView(UserMixin, JsonDetailView):
    http_method_names = ['get', 'put', 'options']  # , 'add', 'delete'
    permissions_tests = {
        'get': get_permission,
        'put': put_permission,
    }
    operation = {
        'put': {'@type': 'ReplaceResourceOperation', 'method': 'PUT'},
    }
    
    # TODO: performance optimisation: object gets queried twice, 
    # 1. get_last_modified_and_etag
    # 2. in View
    @method_decorator(condition(last_modified_and_etag_func=get_last_modified_and_etag))
    def dispatch(self, request, *args, **kwargs):
        return super(UserDetailView, self).dispatch(request, *args, **kwargs)       

    def get_queryset(self):
        return super(UserDetailView, self).get_queryset().prefetch_related('useraddress_set', 'userphonenumber_set')

    def get_object_data(self, request, obj):
        return super(UserDetailView, self).get_object_data(request, obj, details=True)
    
    def save_user_details(self, data, name, mapping, cls):
        """
        first update existing objects and then delete the missing objects, before adding new,
        because of database constrains (i.e. (user, address_type) is unique) 
        """

        # when there is no user detail we change nothing
        # to delete the address for example, you must send an empty addresses dictionary  
        if name not in data:
            return
        
        new_object_keys = []
        changed_object_keys = []
        # update existing
        for key, value in data[name].items():
            try:
                cls_obj = cls.objects.get(uuid=key, user=self.object)
                obj_data = map_dict2dict(mapping, value)
                update_object_from_dict(cls_obj, obj_data)
                changed_object_keys.append(key)
            except ObjectDoesNotExist:
                new_object_keys.append(key)
        # delete 
        cls.objects.filter(user=self.object).exclude(uuid__in=changed_object_keys).delete()
        
        # add new 
        for key in new_object_keys:
            value = data[name][key]
            obj_data = map_dict2dict(mapping, value)
            obj_data['uuid'] = key
            obj_data['user'] = self.object
            cls.objects.create(**obj_data)        

    def save_object_data(self, request, data):
        obj = self.object
        object_data = map_dict2dict(API_USER_MAPPING, data)
        
        if User.objects.filter(email__iexact=object_data['email']).exclude(pk=obj.pk).exists():
            raise ValueError(_("A user with that email already exists."))
        
        update_object_from_dict(obj, object_data)
        scopes = request.scopes
        if 'address' in scopes:
            self.save_user_details(data, 'addresses', API_ADDRESS_MAP, UserAddress)
        if 'phone' in scopes:
            self.save_user_details(data, 'phone_numbers', API_PHONE_MAP, UserPhoneNumber)
        
    def create_object(self, request, data):
        """
        to make add available add "add" to http_method_names 
        """
        object_data = map_dict2dict(API_USER_MAPPING, data)
        if User.objects.filter(email__iexact=object_data['email']).exists():
            raise ValueError(_("A user with that email address already exists."))
        
        if not object_data['username']:
            object_data['username'] = default_username_generator(capfirst(object_data['first_name']), capfirst(object_data['last_name']))
        
        obj = self.model(**object_data)
        obj.save()
        
        for key, value in data['addresses'].items():
            address_data = map_dict2dict(API_ADDRESS_MAP, value)
            if not address_data['address_type']:
                address_data['address_type'] = UserAddress.ADDRESSTYPE_CHOICES[0]  # home
            address = UserAddress(uuid=key, user=obj, **address_data)
            address.save()
                    
        for key, value in data['phone_numbers'].items():
            phone_data = map_dict2dict(API_PHONE_MAP, value)
            if not phone_data['phone_type']:
                phone_data['phone_type'] = UserPhoneNumber.PHONE_CHOICES[0]  # home
            phone = UserPhoneNumber(uuid=key, user=obj, **phone_data)
            phone.save()
        
        send_account_created_email(obj, request)
        return obj


class MyDetailView(UserDetailView):
    
    operation = {
        'put': {'@type': 'ReplaceResourceOperation', 'method': 'PUT'},
    }

    @method_decorator(condition(last_modified_and_etag_func=get_last_modified_and_etag_for_me))
    def dispatch(self, request, *args, **kwargs):
        return super(UserDetailView, self).dispatch(request, *args, **kwargs)       

    def get_object(self, queryset=None):
        return self.request.user
    

class GlobalNavigationView(UserDetailView):
    operation = {}
    
    @method_decorator(cache_control(must_revalidate=True, max_age=60 * 5)) 
    def get(self, request, *args, **kwargs):
        return super(GlobalNavigationView, self).get(request, *args, **kwargs)

    def get_object_data(self, request, obj, details=False):
        applications = []
        for application in obj.get_apps():
            application_data = {
                'id': application.uuid,
                'order': application.order, 
                'link': {'href': application.url, 'title': application.title, 'global_navigation': application.global_navigation}
            }
            applications.append(application_data)
        
        data = {
            'id': obj.uuid,
            'apps': applications,
            'more': {'href': '#', 'title': _('More')},
            'profile': {'href': absolute_url(request, reverse('accounts:profile')), 'title': obj.get_full_name()},
            'logout': {'href': absolute_url(request, reverse('accounts:logout')), 'title': _('Log out')}
        }
        if obj.picture:
            data['picture_30x30'] = {'href': absolute_url(request, get_thumbnail(obj.picture, "30x30", crop="center").url)}
        return data


class MyGlobalNavigationView(GlobalNavigationView):
    operation = {}

    @method_decorator(condition(last_modified_and_etag_func=get_last_modified_and_etag_for_me))
    @method_decorator(cache_control(must_revalidate=True, max_age=60 * 5)) 
    def dispatch(self, request, *args, **kwargs):
        return super(JsonDetailView, self).dispatch(request, *args, **kwargs)       

    def get_object(self, queryset=None):
        return self.request.user
    

class UserList(UserMixin, JsonListView):
    @classmethod
    def getpermission(cls, request, obj):
        user = request.user
        if (not user.has_perm('accounts.read_user')):
            return False, "User has no permission '%s" % 'accounts.read_user'
        elif ('users' not in request.scopes):
            return False, "users not in scope '%s'" % request.scopes
        else:
            return True, None

    @classmethod
    def addpermission(cls, request):
        user = request.user
        if (not user.has_perm('accounts.add_user')):
            return False, "User has no permission '%s" % 'accounts.add_user'
        elif ('users' not in request.scopes):
            return False, "users not in scope '%s'" % request.scopes
        else:
            return True, None
    
    def get_operation(self):
        base_uri = base_url(self.request)
        return {
            'add': {'@type': ' CreateResourceOperation', 'method': 'PUT', 'template': "%s%s%s" % (base_uri, reverse('api:v2_users'), '{uuid}/')}
        }

    def get_queryset(self):
        qs = super(UserList, self).get_queryset().prefetch_related('useraddress_set', 'userphonenumber_set').distinct()
        qs = qs.order_by('username')
        qs = self.request.user.filter_administrable_users(qs)
    
        is_active = self.request.GET.get('is_active', None)
        if is_active:
            is_active = is_active in ['True', 'true', '1', 'yes', 'Yes', 'Y', 'y']
            qs = qs.filter(is_active=is_active)

        username = self.request.GET.get('q', None)
        if username:
            qs = qs.filter(username__icontains=username)

        country_group_id = self.request.GET.get('country_group_id', None)
        if country_group_id:
            qs = qs.filter(organisations__country__organisationcountry__country_groups__uuid=country_group_id)
        
        country = self.request.GET.get('country', None)
        if country:
            qs = qs.filter(organisations__country__iso2_code__iexact=country)
        
        region_id = self.request.GET.get('region_id', None)
        if region_id:
            qs = qs.filter(organisations__admin_region__uuid=region_id)
        
        org_id = self.request.GET.get('org_id', None)
        if org_id:
            qs = qs.filter(organisations__uuid=org_id)
        
        app_uuid = self.request.GET.get('app_id', None)
        if app_uuid:
            qs = qs.filter(application_roles__application__uuid=app_uuid)
        
        modified_since = self.request.GET.get('modified_since', None)
        if modified_since:  # parse modified_since
            parsed = parse_datetime_with_timezone_support(modified_since)
            if parsed is None:
                raise ValueError("can not parse %s" % modified_since)
            qs = qs.filter(Q(last_modified__gte=parsed) | Q(useraddress__last_modified__gte=parsed) | Q(userphonenumber__last_modified__gte=parsed))
            
        return qs


UserList.permissions_tests = {
    'get': UserList.getpermission,
    'add': UserList.addpermission,
}
