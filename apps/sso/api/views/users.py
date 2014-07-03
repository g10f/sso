# -*- coding: utf-8 -*-
import json
import datetime

from django.views.generic import View
from django.views.decorators.vary import vary_on_headers
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import cache_control, cache_page
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils.translation import ugettext as _
from django.utils import timezone, dateparse
from django.template.defaultfilters import date
from sorl.thumbnail import get_thumbnail

from sso.accounts.models import ApplicationRole, send_account_created_email
from sso.organisations.models import Organisation
from sso.registration import default_username_generator
from http.http_status import *  # @UnusedWildImport
from sso.oauth2.decorators import client_required
from utils.url import base_url, build_url, absolute_url
from sso.api.decorators import api_user_passes_test, catch_errors
from sso.api.response import JsonHttpResponse

import logging

logger = logging.getLogger(__name__)

DEFAULT_PER_PAGE = 100
MIN_PER_PAGE = 2
MAX_PER_PAGE = 1000
FIND_EXPRESSION = "{?q,organisation__uuid,per_page,app_uuid,modified_since}"


def get_page_and_links(request, qs, find_expression=FIND_EXPRESSION):
    per_page = int(request.GET.get('per_page', DEFAULT_PER_PAGE))
    per_page = max(MIN_PER_PAGE, per_page)
    paginator = Paginator(qs, per_page)

    page = request.GET.get('page')
    try:
        page = paginator.page(page)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    page_base_url = "%s%s" % (base_url(request), request.path)
    self_url = build_url(page_base_url, request.GET)
    links = {
        'find': {'href': '%s%s' % (page_base_url, find_expression), 'templated': True},
        'self': {'href': self_url}
    }
    
    if page.has_next():
        links['next'] = {'href': build_url(self_url, {'page': page.next_page_number()})}
    if page.has_previous():
        links['prev'] = {'href': build_url(self_url, {'page': page.previous_page_number()})}
    
    return page, links


@cache_page(60 * 60)
def home(request):
    base_uri = base_url(request)
    resources = {
        "resources": {
            "http://openid.net/specs/connect/1.0/issuer": {
                "href": "%s%s" % (base_uri, "/.well-known/openid-configuration")
            },
            "http://dwbn.org/specs/api/1.0/me": {
                "href": "%s%s" % (base_uri, reverse('api:v1_users_me')),
                "hints": {
                    "docs": "https://wiki.dwbn.org"
                }
            },
            "http://dwbn.org/specs/api/1.0/my-apps": {
                "href": "%s%s" % (base_uri, reverse('api:v1_users_my_apps'))
            },
            "http://dwbn.org/specs/api/1.0/users": {
                "href-template": "%s%s%s" % (base_uri, reverse('api:v1_users'), FIND_EXPRESSION),
                "href-vars": {
                    "q": "%s/param/q" % (base_uri),
                    "organisation__uuid": "%s/param/organisation__uuid" % (base_uri),
                    "per_page": "%s/param/per_page" % (base_uri),
                    "app_uuid": "%s/param/app_uuid" % (base_uri),
                    "modified_since": "%s/param/modified_since" % (base_uri)
                }
            },
            "http://dwbn.org/specs/api/1.0/user-apps": {
                "href-template": "%s%s%s" % (base_uri, reverse('api:v1_users'), '{uuid}/apps/'),
                "href-vars": {
                    "uuid": "%s/param/uuid" % (base_uri)
                }
            },
            "http://dwbn.org/specs/api/1.0/user": {
                "href-template": "%s%s%s" % (base_uri, reverse('api:v1_users'), '{uuid}/'),
                "href-vars": {
                    "uuid": "%s/param/uuid" % (base_uri)
                }
            }
        }
    }
    return JsonHttpResponse(content=resources, request=request)

"""
@cache_page(60 * 60)
def get_index(request, find_expression=FIND_EXPRESSION):
    base_uri = base_url(request)
    self_url = "%s%s" % (base_uri, request.path)
    api = {
        'links': {
            'self': {'href': self_url, 'title': _('API base uri')},
            'token': {'href': '%s%s' % (base_uri, reverse('oauth2:token')), 'templated': False, 'title': _('oauth2 token')},
            'tokeninfo': {'href': '%s%s%s' % (base_uri, reverse('oauth2:tokeninfo'), '{?access_token,id_token}'), 'templated': True, 'title': _('get tokeninfo')},
            'certs': {'href': '%s%s' % (base_uri, reverse('oauth2:certs')), 'templated': False, 'title': _('signature certificates')},
            'users': {'href': '%s%s%s' % (base_uri, reverse('api:v1_users'), find_expression), 'templated': True, 'title': _('paginated list of all users')},
            'me': {'href': '%s%s%s' % (base_uri, reverse('api:v1_users'), 'me/'), 'templated': False, 'title': _('logged in user')},
            'user': {'href': '%s%s%s' % (base_uri, reverse('api:v1_users'), '{uuid}/'), 'templated': True, 'title': _('user identified by uuid')},
            'user_apps': {'href': '%s%s%s' % (base_uri, reverse('api:v1_users'), '{uuid}/apps/'), 'templated': True, 'title': _('apps for user identified by uuid')},
            'my_apps': {'href': '%s%s%s' % (base_uri, reverse('api:v1_users'), 'me/apps/'), 'templated': False, 'title': _('apps for logged in user')},
        }
    }
    return JsonHttpResponse(content=api, request=request)
"""

def _address_state(address):
    state = ""
    if address.state:
        if address.state.abbrev:
            state = address.state.abbrev
        else:
            state = address.state.name
    return state


def parse_datetime_with_timezone_support(value):
    parsed = dateparse.parse_datetime(value)
    
    if not parsed:  # try date format
        parsed = dateparse.parse_date(value)
        if parsed is not None:
            parsed = datetime.datetime(parsed.year, parsed.month, parsed.day)
        
    # Confirm that dt is naive before overwriting its tzinfo.
    if parsed is not None and timezone.is_naive(parsed):
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def get_userapps(user, request):
    """
    JSON data for the global navigation bar
    """
    applications = []
    for application in user.get_apps():
        application_data = {
            'uuid': application.uuid,
            'order': application.order, 
            'links': {'app': {'href': application.url, 'title': application.title, 'global_navigation': application.global_navigation}}
        }
        applications.append(application_data)
    
    userinfo = {
        'uuid': user.uuid,
        'applications': applications,
        'full_name': user.get_full_name(),
        'text': {'More': _('More'), 'Logout': _('Log out')},
        'links': {'profile': {'href': absolute_url(request, reverse('accounts:profile'))},
                  'logout': {'href': reverse('accounts:logout')}}
    }
    if user.picture:
        userinfo['links']['picture_30x30'] = {'href': absolute_url(request, get_thumbnail(user.picture, "30x30").url)}
    return userinfo


def get_userinfo(user, request, show_details=False):
    scopes = request.scopes
    base = base_url(request)
    userinfo = {
        'id': u'%s' % user.uuid,
        # 'sub': u'%s' % user.uuid,  # remove after all clients migrated to id
        'name': u'%s' % user,
        'given_name': u'%s' % user.first_name,
        'family_name': u'%s' % user.last_name,
        'email': u'%s' % user.email,
        'gender': user.gender,
        'birth_date': date(user.dob, "c"),
        'homepage': user.homepage,
        'language': user.language,
        'is_center': user.is_center,
        'organisations': {organisation.uuid: {'name': organisation.name} for organisation in user.organisations.all()},
        'links': {'self': {'href': "%s%s" % (base, reverse('api:v1_user', kwargs={'uuid': user.uuid}))},
                  'apps': {'href': "%s%s" % (base, reverse('api:v1_users_apps', kwargs={'uuid': user.uuid}))}}
    } 
    if user.picture:
        userinfo['picture'] = absolute_url(request, user.picture.url)
    if show_details:
        applications = {}
        applicationroles = user.get_applicationroles()
             
        for application in user.get_apps():
            application_data = {
                'order': application.order, 
                'links': {'app': {'href': application.url, 'title': application.title, 'global_navigation': application.global_navigation}}
            }
            application_data['roles'] = []
            for applicationrole in applicationroles:
                if applicationrole.application == application:
                    application_data['roles'].append(applicationrole.role.name)
            
            applications[application.uuid] = application_data
        userinfo['applications'] = applications
        
        if 'address' in scopes:
            userinfo['addresses'] = {
                address.uuid: {
                    'address_type': address.address_type,
                    'addressee': address.addressee,
                    'street_address': address.street_address,
                    'city': address.city,
                    'postal_code': address.postal_code,
                    'country': address.country.iso2_code,
                    'state': _address_state(address),
                    'primary': address.primary
                } for address in user.useraddress_set.all()
            }
        
        if 'phone' in scopes:
            userinfo['phone_numbers'] = {
                phone_number.uuid: {
                    'phone_type': phone_number.phone_type,
                    'phone': phone_number.phone,
                    'primary': phone_number.primary
                } for phone_number in user.userphonenumber_set.all()
            }
    return userinfo          
        
    
# TODO: design api more HATEOAS like
@catch_errors
@api_user_passes_test(lambda u: u.has_perm("accounts.change_all_users"))
def get_user_list(request):
    qs = get_user_model().objects.filter(is_active=True).order_by('username').prefetch_related('organisations', 'useraddress_set', 'userphonenumber_set')
    username = request.GET.get('q', None)
    if username:
        qs = qs.filter(username__icontains=username)
    organisation__uuid = request.GET.get('organisation__uuid', None)
    if organisation__uuid:
        qs = qs.filter(organisations__uuid=organisation__uuid)
    app_uuid = request.GET.get('app_uuid', None)
    if app_uuid:
        qs = qs.filter(application_roles__application__uuid=app_uuid)
    modified_since = request.GET.get('modified_since', None)
    if modified_since:  # parse modified_since
        parsed = parse_datetime_with_timezone_support(modified_since)
        if parsed is None:
            raise ValueError("can not parse %s" % modified_since)  # TODO: distinguish between client and server error in exception handling
        # TODO: take into account last_modified of addresses and phone numbers            
        qs = qs.filter(last_modified__gte=parsed)

    page, links = get_page_and_links(request, qs)
    userinfo = {
        'collection': {
            user.uuid: get_userinfo(user, request, show_details=False) for user in page
        },
        'links': links
    }
    return JsonHttpResponse(request=request, content=userinfo)
        

class UserDetailView(View):
    # used for global navigation bar
    is_apps_only = False
    
    @method_decorator(csrf_exempt)
    @method_decorator(catch_errors)  
    def dispatch(self, request, *args, **kwargs):
        return super(UserDetailView, self).dispatch(request, *args, **kwargs)
    
    def options(self, request, *args, **kwargs):
        """
        check for cors Preflight Request
        See http://www.html5rocks.com/static/images/cors_server_flowchart.png
        """
        # origin is mandatory
        origin = self.request.META.get('HTTP_ORIGIN')
        if not origin:
            return super(UserDetailView, self).options(request, *args, **kwargs)
        
        # ACCESS_CONTROL_REQUEST_METHOD is optional
        acrm = self.request.META.get('HTTP_ACCESS_CONTROL_REQUEST_METHOD')  
        if acrm:
            if acrm not in self._allowed_methods():
                logger.warning('ACCESS_CONTROL_REQUEST_METHOD %s not allowed' % acrm)
                return super(UserDetailView, self).options(request, *args, **kwargs)
        
            response = HttpResponse()
            response['Access-Control-Allow-Methods'] = ', '.join(self._allowed_methods())
            response['Access-Control-Allow-Headers'] = 'Authorization'
            response['Access-Control-Max-Age'] = 60 * 60
        else:
            #  expose headers to client (optional)
            response = HttpResponse()
            response['Access-Control-Expose-Headers'] = 'Authorization'
            
        response['Access-Control-Allow-Origin'] = '*'        
        return response        
        
    @method_decorator(api_user_passes_test(lambda u: u.is_authenticated()))   
    @method_decorator(vary_on_headers('Access-Control-Allow-Origin', 'Authorization'))
    @method_decorator(cache_control(must_revalidate=True, max_age=60 * 5)) 
    def get(self, request, uuid='me', *args, **kwargs):        
        if uuid == 'me':
            selected_user = request.user
        else:
            selected_user = get_object_or_404(get_user_model(), uuid=uuid)
        
        if self.is_apps_only:
            userinfo = get_userapps(selected_user, request)
        else:
            userinfo = get_userinfo(selected_user, request, show_details=True)
        
        return JsonHttpResponse(content=userinfo, request=request)

    @method_decorator(client_required(['68bfae12a58541548def243e223053fb']))
    @method_decorator(api_user_passes_test(lambda u: u.is_authenticated()))
    @transaction.atomic
    def put(self, request, uuid, *args, **kwargs):
        userinfo = json.loads(request.body)
        user = None
        try:
            user = get_user_model().objects.get(uuid=uuid)
        except ObjectDoesNotExist: 
            pass
        
        first_name = userinfo['given_name']
        last_name = userinfo['family_name']
        email = userinfo['email']
        
        organisations = Organisation.objects.filter(uuid__in=userinfo['organisations'].keys())
        
        if user:
            user.organisations = organisations
            user.is_active = True
            user.save()                          
        else:
            # new user            
            username = default_username_generator(first_name, last_name)
            user = get_user_model()(first_name=first_name, last_name=last_name, email=email, username=username)
            user.set_password("")                            
            
            application_roles = []
            for application_uuid, application_data in userinfo.get('applications', {}).items():
                application_roles += ApplicationRole.objects.filter(application__uuid=application_uuid, 
                                                                    role__name__in=application_data['roles'])
            
            user.uuid = uuid
            user.save()

            user.application_roles = application_roles
            user.organisations = organisations
            user.add_default_roles()
            
            send_account_created_email(user, request)
        
        userinfo = get_userinfo(user, request, show_details=True)
        return JsonHttpResponse(content=userinfo, request=request)

    @method_decorator(client_required(['68bfae12a58541548def243e223053fb']))
    @method_decorator(api_user_passes_test(lambda u: u.is_authenticated()))   
    @transaction.atomic   
    def delete(self, request, uuid, *args, **kwargs):
        try:
            self.object = get_user_model().objects.get(uuid=uuid)
            self.object.is_active = False
            self.object.save()      
        except ObjectDoesNotExist: 
            pass

        return HttpResponse(status=HTTP_204_NO_CONTENT)
