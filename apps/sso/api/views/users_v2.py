import logging
from uuid import UUID

from sorl.thumbnail import get_thumbnail

from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http.response import HttpResponse
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.dateparse import parse_date
from django.utils.decorators import method_decorator
from django.utils.text import capfirst
from django.utils.translation import get_language_from_request, gettext as _
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_exempt
from l10n.models import Country
from sso.accounts.email import send_account_created_email, send_useremail_confirmation
from sso.accounts.models import UserAddress, UserPhoneNumber, User, UserEmail, ApplicationRole, Application, \
    UserAssociatedSystem, RoleProfile
from sso.api.decorators import condition, api_user_passes_test
from sso.api.response import JsonHttpResponse
from sso.api.views.generic import JsonListView, JsonDetailView
from sso.auth.utils import is_recent_auth_time
from sso.models import update_object_from_dict, map_dict2dict
from sso.organisations.models import Organisation
from sso.registration import default_username_generator
from sso.utils.parse import parse_datetime_with_timezone_support, strtobool
from sso.utils.url import absolute_url, get_base_url

logger = logging.getLogger(__name__)

"""
mapping consist of key values, where

1. the value is the name of the django object field or
2. the value is a dictionary with the name of the django object field and optional a parser and validate function

"""


def _parse_date(value):
    if value:
        return parse_date(value)
    else:
        return None


def validate_phone(value):
    """
    same as validate_phone from sso.models, except that a return True is added
    """
    from sso.models import validate_phone
    validate_phone(value)
    return True


SCOPE_MAPPING = {
    'addresses': 'address',
    'phone_numbers': 'phone'
}


def _non_empty_string(s):
    if issubclass(type(s), str):
        return len(s) > 0
    return False


# json name : {'name': obect attribute name, ... }
API_USER_MAPPING = {
    'given_name': {'name': 'first_name', 'validate': _non_empty_string},
    'family_name': {'name': 'last_name', 'validate': _non_empty_string},
    # 'email': {'name': 'email', 'validate': lambda x: len(x) > 0},
    'gender': 'gender',
    'birth_date': {'name': 'dob', 'parser': _parse_date},
    'homepage': 'homepage',
    'language': 'language',
    'uuid': 'uuid',  # this value is created in JsonDetailView.create from the url
}
API_ADDRESS_MAP = {
    'address_type': {'name': 'address_type',
                     'validate': lambda x: x in [i[0] for i in UserAddress.ADDRESSTYPE_CHOICES],
                     'default': UserAddress.ADDRESSTYPE_CHOICES[0][0]},
    'addressee': {'name': 'addressee', 'validate': _non_empty_string},
    'street_address': 'street_address',
    'city': {'name': 'city', 'validate': _non_empty_string},
    'city_native': 'city_native',
    'postal_code': 'postal_code',
    'country': {'name': 'country', 'parser': lambda iso2_code: Country.objects.get(iso2_code=iso2_code)},
    'region': 'region',
    'primary': 'primary'
}
API_PHONE_MAP = {
    'phone_type': {'name': 'phone_type', 'validate': lambda x: x in [i[0] for i in UserPhoneNumber.PHONE_CHOICES],
                   'default': UserPhoneNumber.PHONE_CHOICES[0][0]},
    'phone': {'name': 'phone', 'validate': validate_phone},
    'primary': 'primary'
}


class UserMixin(object):
    model = User

    def get_object_data(self, request, obj, details=False):
        scopes = request.scopes
        base = get_base_url(request)
        email = obj.primary_email()
        data = {
            '@id': "%s%s" % (base, reverse('api:v2_user', kwargs={'uuid': obj.uuid.hex})),
            'id': '%s' % obj.uuid.hex,
            'sub': '%s' % obj.uuid.hex,
            'is_active': obj.is_active,
            'name': '%s' % obj,
            'given_name': '%s' % obj.first_name,
            'family_name': '%s' % obj.last_name,
            'gender': obj.gender,
            'birth_date': obj.dob,
            'homepage': obj.homepage,
            'language': obj.language,
            'is_center': obj.is_center,
            'last_modified': obj.get_last_modified_deep()
        }
        if obj.valid_until:
            data['valid_until'] = obj.valid_until

        if obj.timezone:
            data['timezone'] = obj.timezone
            # data['utc_offset'] = localtime(now(), timezone(obj.timezone)).strftime('%z')

        if email is not None:
            data['email'] = email.email
            data['email_verified'] = email.confirmed

        data['picture'] = {
            '@id': "%s%s" % (base, reverse('api:v2_picture', kwargs={'uuid': obj.uuid.hex}))
        }
        if obj.picture:
            data['picture']['url'] = absolute_url(request, obj.picture.url)

        data['associated_systems'] = {
            associated_system.application.uuid.hex: {
                'userid': associated_system.userid
            } for associated_system in UserAssociatedSystem.objects.filter(user=obj)}

        if details:
            if obj.picture:
                data['picture']['30x30'] = absolute_url(request, get_thumbnail(obj.picture, "30x30", crop="center").url)
                data['picture']['60x60'] = absolute_url(request, get_thumbnail(obj.picture, "60x60", crop="center").url)
                data['picture']['120x120'] = absolute_url(request, get_thumbnail(obj.picture, "120x120", crop="center").url)
                data['picture']['240x240'] = absolute_url(request, get_thumbnail(obj.picture, "240x240", crop="center").url)
                data['picture']['480x480'] = absolute_url(request, get_thumbnail(obj.picture, "480x480", crop="center").url)

            data['organisations'] = {
                organisation.uuid.hex: {
                    'country': organisation.organisation_country.country.iso2_code,
                    'name': organisation.name,
                    '@id': "%s%s" % (base, reverse('api:v2_organisation', kwargs={'uuid': organisation.uuid.hex}))
                } if organisation.organisation_country else {
                    'name': organisation.name,
                    '@id': "%s%s" % (base, reverse('api:v2_organisation', kwargs={'uuid': organisation.uuid.hex}))
                } for organisation in obj.organisations.all().prefetch_related('organisation_country__country')
            }
            data['admin_regions'] = {
                region.uuid.hex: {
                    'country': region.organisation_country.country.iso2_code,
                    'name': region.name,
                    '@id': "%s%s" % (base, reverse('api:v2_region', kwargs={'uuid': region.uuid.hex}))
                } if region.organisation_country else {
                    'name': region.name,
                    '@id': "%s%s" % (base, reverse('api:v2_region', kwargs={'uuid': region.uuid.hex}))
                } for region in obj.admin_regions.all().prefetch_related('organisation_country__country')
            }
            data['admin_countries'] = {
                organisation_country.country.iso2_code: {
                    'code': organisation_country.country.iso2_code,
                    'name': organisation_country.country.printable_name,
                    '@id': "%s%s" % (
                        base, reverse('api:v2_country', kwargs={'iso2_code': organisation_country.country.iso2_code}))
                } for organisation_country in obj.admin_organisation_countries.all()
            }

            if 'role' in scopes:
                applications = {}
                applicationroles = obj.get_applicationroles()

                for application in obj.get_apps():
                    if not application.required_scope or application.required_scope in scopes:
                        application_data = {'order': application.order,
                                            'link': {'href': application.url, 'title': application.title,
                                                     'global_navigation': application.global_navigation}, 'roles': []}
                        for applicationrole in applicationroles:
                            if applicationrole.application == application:
                                application_data['roles'].append(applicationrole.role.name)

                        applications[application.uuid.hex] = application_data
                data['apps'] = applications

            # be carefully to assign role_profile, because there can be private / secret role_profiles
            # TODO: filter role_profiles by required_scope
            if 'role_profile' in scopes:
                data['role_profiles'] = [role_profile.uuid.hex for role_profile in obj.role_profiles.all()]

            if 'address' in scopes:
                data['addresses'] = {
                    address.uuid.hex: {
                        'address_type': address.address_type,
                        'addressee': address.addressee,
                        'street_address': address.street_address,
                        'city': address.city,
                        'city_native': address.city_native,
                        'postal_code': address.postal_code,
                        'country': address.country.iso2_code,
                        'region': address.region,
                        'primary': address.primary
                    } for address in obj.useraddress_set.all()
                }

            if 'phone' in scopes:
                data['phone_numbers'] = {
                    phone_number.uuid.hex: {
                        'phone_type': phone_number.phone_type,
                        'phone': phone_number.phone,
                        'primary': phone_number.primary
                    } for phone_number in obj.userphonenumber_set.all()
                }

            if 'profile' in scopes:
                for user_attribute in obj.userattribute_set.all():
                    data[user_attribute.name] = user_attribute.value

            if obj.has_perm("registration.change_registrationprofile"):
                count_of_registrationprofiles = obj.get_count_of_registrationprofiles()
                if settings.REGISTRATION.get('OPEN', True) or count_of_registrationprofiles > 0:
                    data['open_registrations'] = count_of_registrationprofiles

            if obj.has_perm("accounts.change_user"):
                data['open_centerchanges'] = obj.get_count_of_organisationchanges()

        return data


def get_last_modified_and_etag(request, uuid):
    if request.user.is_authenticated:
        try:
            obj = User.objects.only('last_modified').get(uuid=uuid)
            lang = get_language_from_request(request)
            last_modified = obj.get_last_modified_deep()
            etag = '"%s/%s/%s"' % (uuid, lang, last_modified)
            return last_modified, etag
        except ObjectDoesNotExist:
            return None, None
    else:
        return None, None


def get_last_modified_and_etag_for_me(request, *args, **kwargs):
    if request.user.is_authenticated:
        lang = get_language_from_request(request)
        last_modified = request.user.get_last_modified_deep()
        etag = '"%s/%s/%s"' % (request.user.uuid.hex, lang, last_modified)
        return last_modified, etag
    else:
        return None, None


def read_permission(request, obj, required_scope=None):
    """
    user is the authenticated user
    permission to read the obj data
    """
    user = request.user
    if not user.is_authenticated:
        return False, 'User not authenticated'
    if required_scope and required_scope not in request.scopes:
        return False, "%s not in scope '%s'" % (required_scope, request.scopes)

    if user.uuid == obj.uuid:
        return True, None
    else:
        if not user.has_perm('accounts.read_user'):
            return False, "User has no permission '%s" % 'accounts.read_user'
        elif not user.has_user_access(obj.uuid):
            return False, "User has no access to object"
        else:
            return True, None


def replace_permission(request, obj):
    """
    user is the authenticated user
    permission to change user the obj
    """
    user = request.user
    if user.is_authenticated:
        if user.uuid == obj.uuid:
            return True, None
        else:
            if not user.has_perm('accounts.change_user'):
                return False, "User has no permission '%s" % 'accounts.change_user'
            elif not user.has_user_access(obj.uuid):
                return False, "User has no access to object"
            else:
                return True, None
    return False, 'User not authenticated'


def create_permission(request, obj=None):
    user = request.user
    if user.has_perm('accounts.add_user'):
        return True, None
    else:
        return False, 'You have no \'accounts.add_user\' permission'


class UserDetailView(UserMixin, JsonDetailView):
    http_method_names = ['get', 'put', 'delete', 'options']  #
    create_object_with_put = True
    permissions_tests = {
        'read': read_permission,
        'replace': replace_permission,
        'delete': replace_permission,
        'create': create_permission,
    }
    operations = {
        'replace': {'@type': 'ReplaceResourceOperation', 'method': 'PUT'},
        'delete': {'@type': 'DeleteResourceOperation', 'method': 'DELETE'},
    }

    @method_decorator(csrf_exempt)  # required here because the middleware will be executed before the view function
    @method_decorator(condition(last_modified_and_etag_func=get_last_modified_and_etag))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return super().get_queryset().prefetch_related('useraddress_set', 'userphonenumber_set', 'userattribute_set',
                                                       'userassociatedsystem_set')

    def get_object_data(self, request, obj, details=True):
        return super().get_object_data(request, obj, details=details)

    def _update_user_organisation(self, data):
        request = self.request
        if 'organisations' in data:
            allowed_organisations = request.user.get_administrable_user_organisations().filter(
                uuid__in=data['organisations'].keys())
            organisations = Organisation.objects.filter(uuid__in=data['organisations'].keys())
            if len(allowed_organisations) < len(organisations):
                denied_organisations = organisations.exclude(id__in=allowed_organisations.values_list('id', flat=True))
                raise ValueError(_("You are not allowed to add users to %s.") % denied_organisations)

            self.object.set_organisations(organisations)
            self.object.save(update_fields=['last_modified', 'last_modified_by_user'])

    def _save_user_details(self, data, name, mapping, cls, update_existing=True):
        """
        first update existing objects and then delete the missing objects, before adding new,
        because of database constrains (i.e. (user, address_type) is unique)
        """

        # when there is no user detail we change nothing
        # to delete the address for example, you must send an empty addresses dictionary
        if name not in data:
            return
        scopes = self.request.scopes
        if SCOPE_MAPPING.get(name) and SCOPE_MAPPING[name] not in scopes:
            raise ValueError("required scope \"%s\" is missing in %s." % (SCOPE_MAPPING[name], scopes))

        new_object_keys = []
        changed_object_keys = []
        # update existing
        if update_existing:
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
        else:
            new_object_keys = data[name].keys()

        # add new
        for key in new_object_keys:
            value = data[name][key]
            obj_data = map_dict2dict(mapping, value, with_defaults=True)
            obj_data['uuid'] = UUID(key)
            obj_data['user'] = self.object
            cls.objects.create(**obj_data)

    def save_object_data(self, request, data):
        obj = self.object

        object_data = map_dict2dict(API_USER_MAPPING, data)
        object_data['is_active'] = True

        if 'email_verified' in data and obj.primary_email():
            email = obj.primary_email()
            if email:
                if email.confirmed != data['email_verified']:
                    email.confirmed = data['email_verified']
                    email.save(update_fields=['last_modified', 'confirmed'])
                    if email.primary and not email.confirmed:
                        # if the current email is the primary email and not confirmed
                        # check if there is another confirmed email, which we assign as the primary email
                        confirmed_email = UserEmail.objects.filter(user=obj, confirmed=True).exclude(pk=email.pk).first()
                        if confirmed_email:
                            obj.create_primary_email(confirmed_email.email)

        # if 'email' not in object_data:
        #    raise ValueError(_("E-mail value is missing"))
        # TODO: redesign email handling
        # if User.objects.by_email(object_data['email']).exclude(pk=obj.pk).exists():
        #     raise ValueError(_("A user with that email already exists."))

        update_object_from_dict(obj, object_data)

        self._update_user_organisation(data)
        self._save_user_details(data, 'addresses', API_ADDRESS_MAP, UserAddress)
        self._save_user_details(data, 'phone_numbers', API_PHONE_MAP, UserPhoneNumber)

        for app_id, associated_system in data.get('associated_systems', {}).items():
            app = Application.objects.get(uuid=app_id)
            UserAssociatedSystem.objects.update_or_create(
                user=self.object, application=app, defaults={'userid': associated_system['userid']})

    def create_object(self, request, data):
        """
        set create_object_with_put=True
        """
        if 'email' not in data:
            raise ValueError(_("E-mail value is missing"))
        try:
            User.objects.get_by_email(data['email'])
            raise ValueError(_("A user with that email address already exists."))
        except ObjectDoesNotExist:
            pass

        object_data = map_dict2dict(API_USER_MAPPING, data)

        object_data['username'] = default_username_generator(
            capfirst(object_data['first_name']), capfirst(object_data['last_name']))

        self.object = self.model(**object_data)
        self.object.set_password(get_random_string(40))
        self.object.save()

        scopes = self.request.scopes

        # create initial app roles
        applications = data.get('apps', {}).items()
        if len(applications) > 0:
            if 'role' not in scopes:
                raise ValueError("required scope \"%s\" is missing in %s." % ('role', scopes))

            initial_application_roles = []
            administrable_application_role_ids = set(
                request.user.get_administrable_application_roles().all().values_list('id', flat=True))
            for application_uuid, application_data in applications:
                application_roles = ApplicationRole.objects.filter(
                    application__uuid=application_uuid, role__name__in=application_data['roles'])
                for application_role in application_roles:
                    if application_role.id in administrable_application_role_ids:
                        initial_application_roles += [application_role]
            self.object.application_roles.set(initial_application_roles)

        # add role profiles
        initial_role_profiles = []
        if User.get_default_guest_profile():
            initial_role_profiles = [User.get_default_guest_profile()]

        if data.get('role_profiles'):
            if 'role_profile' not in scopes:
                raise ValueError("required scope \"%s\" is missing in %s." % ('role_profile', scopes))

            administrable_role_profile_ids = set(
                request.user.get_administrable_app_admin_role_profiles().all().values_list('id', flat=True))
            for profile_uuid in data.get('role_profiles'):
                role_profiles = RoleProfile.objects.filter(uuid=profile_uuid)
                for role_profile in role_profiles:
                    if role_profile.id in administrable_role_profile_ids:
                        initial_role_profiles += [role_profile]

        self.object.role_profiles.set(initial_role_profiles)

        # email
        self.object.create_primary_email(email=data['email'], confirmed=data.get('email_verified'))

        if 'organisations' in data:
            self._update_user_organisation(data)
        else:
            raise ValueError(_("Organisation is missing."))

        self._save_user_details(data, 'addresses', API_ADDRESS_MAP, UserAddress, update_existing=False)
        self._save_user_details(data, 'phone_numbers', API_PHONE_MAP, UserPhoneNumber, update_existing=False)

        for app_id, associated_system in data.get('associated_systems', {}).items():
            app = Application.objects.get(uuid=app_id)
            UserAssociatedSystem.objects.create(application=app, userid=associated_system['userid'],
                                                user=self.object)

        if strtobool(request.GET.get('send_email', 'true')):
            send_account_created_email(self.object, request)

        self.object.update_last_modified()
        return self.object

    def delete_object(self, request, obj):
        obj.is_active = False
        obj.save()


class MyDetailView(UserDetailView):
    operation = {
        'replace': {'@type': 'ReplaceResourceOperation', 'method': 'PUT'},
    }

    @method_decorator(condition(last_modified_and_etag_func=get_last_modified_and_etag_for_me))
    def dispatch(self, request, *args, **kwargs):
        return super(UserDetailView, self).dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.request.user


class VerifyEmailView(JsonDetailView):
    model = User
    http_method_names = ['get', 'post', 'options']

    permissions_tests = {
        'read': read_permission,
        'create': create_permission,
    }
    operations = {
        'create': {'@type': 'CreateResourceOperation', 'method': 'POST'}
    }

    def get_unconfirmed_primary_email(self):
        user = self.get_object()
        user_email = UserEmail.objects.filter(user=user, primary=True, confirmed=False).first()
        if not user_email:
            raise ObjectDoesNotExist("No unconfirmed primary email found.")
        return user_email

    def get_object_data(self, request, obj):
        base = get_base_url(request)
        user_email = self.get_unconfirmed_primary_email()
        data = {
            '@id': "%s%s" % (base, reverse('api:v2_verify_email', kwargs={'uuid': obj.uuid.hex})),
            'id': '%s' % user_email.uuid.hex,
            'last_modified': user_email.last_modified
        }
        return data

    def post(self, request, *args, **kwargs):
        self.check_permission('create')
        user_email = self.get_unconfirmed_primary_email()
        if not user_email:
            raise ObjectDoesNotExist(f"No unconfirmed primary email for user found.")
        send_useremail_confirmation(user_email, request)
        return JsonHttpResponse(request=request, data={"code": 200, "description": 'verification email send'})


class GlobalNavigationView(UserDetailView):
    # TODO: result is cached for different languages
    operations = {}
    permissions_tests = {
        'read': read_permission,
    }

    def render_to_json_response(self, context, allow_jsonp=True, **response_kwargs):
        # allow jsonp requests for the global navigation bar
        return super().render_to_json_response(context, allow_jsonp=allow_jsonp,
                                               **response_kwargs)

    @method_decorator(cache_control(must_revalidate=True, max_age=60 * 5))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_object_data(self, request, obj, details=False):
        applications = []
        for application in obj.get_apps():
            application_data = {
                'id': application.uuid.hex,
                'order': application.order,
                'link': {'href': application.url, 'title': application.title,
                         'global_navigation': application.global_navigation}
            }
            applications.append(application_data)

        data = {
            'id': obj.uuid.hex,
            'apps': applications,
            'more': {'href': '#', 'title': _('More')},
            'profile': {'href': absolute_url(request, reverse('accounts:profile')), 'title': obj.first_name},
            'logout': {'href': absolute_url(request, reverse('auth:logout')), 'title': _('Log out')}
        }
        if obj.picture:
            data['picture_30x30'] = {
                'href': absolute_url(request, get_thumbnail(obj.picture, "30x30", crop="center").url)}
        return data


class MyGlobalNavigationView(GlobalNavigationView):
    # TODO: result is cached for different languages
    operations = {}

    @method_decorator(condition(last_modified_and_etag_func=get_last_modified_and_etag_for_me))
    @method_decorator(cache_control(must_revalidate=True, max_age=60 * 5))
    def dispatch(self, request, *args, **kwargs):
        return super(UserDetailView, self).dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.request.user


class UserList(UserMixin, JsonListView):
    @classmethod
    def read_permission(cls, request, obj):
        user = request.user
        if not user.is_authenticated:
            return False, "Not authenticated"
        if not user.has_perm('accounts.read_user'):
            return False, "User has no permission '%s" % 'accounts.read_user'
        if 'users' not in request.scopes:
            return False, "users not in scope '%s'" % request.scopes
        if not is_recent_auth_time(request):
            return False, "session too old'"

        return True, None

    @classmethod
    def create_permission(cls, request, obj=None):
        user = request.user
        if not user.is_authenticated:
            return False, "Not authenticated"
        if not user.has_perm('accounts.add_user'):
            return False, "User has no permission '%s" % 'accounts.add_user'
        if 'users' not in request.scopes:
            return False, "users not in scope '%s'" % request.scopes
        if not is_recent_auth_time(request):
            return False, "session too old'"

        return True, None

    def get_operations(self):
        base_uri = get_base_url(self.request)
        return {
            'create': {'@type': 'CreateResourceOperation', 'method': 'PUT',
                       'template': "%s%s%s" % (base_uri, reverse('api:v2_users'), '{uuid}/')}
        }

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related('useraddress_set', 'userphonenumber_set', 'userattribute_set',
                                                     'useremail_set', 'userassociatedsystem_set').distinct()
        qs = qs.order_by('username')
        qs = self.request.user.filter_administrable_users(qs)

        for flag_name in ['is_active', 'is_center']:
            flag_value = self.request.GET.get(flag_name, None)
            if flag_value:
                flag_value = flag_value in ['True', 'true', '1', 'yes', 'Yes', 'Y', 'y']
                kwargs = {flag_name: flag_value}
                qs = qs.filter(**kwargs)

        username = self.request.GET.get('q', None)
        if username:
            qs = qs.filter(Q(first_name__icontains=username) | Q(last_name__icontains=username))

        email = self.request.GET.get('email', None)
        if email:
            qs = qs.filter(useremail__email__icontains=email)

        association_id = self.request.GET.get('association_id', None)
        if association_id:
            qs = qs.filter(organisations__association__uuid=association_id)

        country_group_id = self.request.GET.get('country_group_id', None)
        if country_group_id:
            qs = qs.filter(organisations__organisation_country__country_groups__uuid=country_group_id)

        country = self.request.GET.get('country', None)
        if country:
            qs = qs.filter(organisations__organisation_country__country__iso2_code__iexact=country)

        region_id = self.request.GET.get('region_id', None)
        if region_id:
            qs = qs.filter(organisations__admin_region__uuid=region_id)

        org_id = self.request.GET.get('org_id', None)
        if org_id:
            qs = qs.filter(organisations__uuid=org_id)

        app_uuid = self.request.GET.get('app_id', None)
        if app_uuid:
            # only allow app_id if application.required_scope is in request.scopes
            scopes = self.request.scopes
            application = Application.objects.get_by_natural_key(app_uuid)
            if application.required_scope and not application.required_scope in scopes:
                raise ValueError("required scope %s not in scopes %s" % (application.required_scope, scopes))

            q = Q(application_roles__application__uuid=app_uuid)
            q |= Q(role_profiles__application_roles__application__uuid=app_uuid)
            qs = qs.filter(q)

        app_roles = self.request.GET.getlist('app_role', None)
        if app_roles:
            scopes = self.request.scopes
            for app_role in app_roles:
                app_uuid, role = app_role.split(',')
                application = Application.objects.get_by_natural_key(app_uuid)
                if application.required_scope and not application.required_scope in scopes:
                    raise ValueError("required scope %s not in scopes %s" % (application.required_scope, scopes))

                app_role = ApplicationRole.objects.get(application=application, role__name=role)
                q = Q(application_roles=app_role)
                q |= Q(role_profiles__application_roles=app_role)
                qs = qs.filter(q)

        associated_system_uuid = self.request.GET.get('associated_system_id', None)
        if associated_system_uuid:
            q = Q(userassociatedsystem__application__uuid=associated_system_uuid)
            qs = qs.filter(q)

        modified_since = self.request.GET.get('modified_since', None)
        if modified_since:  # parse modified_since
            parsed = parse_datetime_with_timezone_support(modified_since)
            if parsed is None:
                raise ValueError("can not parse %s" % modified_since)
            qs = qs.filter(Q(last_modified__gte=parsed) | Q(useraddress__last_modified__gte=parsed) |
                           Q(userphonenumber__last_modified__gte=parsed))

        valid_until_lt = self.request.GET.get('valid_until_lt', None)
        if valid_until_lt:  # parse valid_until_less_then
            parsed = parse_datetime_with_timezone_support(valid_until_lt)
            if parsed is None:
                raise ValueError("can not parse %s" % valid_until_lt)
            qs = qs.filter(valid_until__lt=parsed)

        return qs


UserList.permissions_tests = {
    'read': UserList.read_permission,
    'create': UserList.create_permission,
}


@login_required
@api_user_passes_test(lambda u: u.is_user_admin)
@permission_required(["accounts.read_user"], raise_exception=True)
def user_emails(request):
    qs = UserEmail.objects.filter(user__is_active=True, user__last_login__isnull=False, primary=True)
    qs = request.user.filter_administrable_user_emails(qs)

    is_center = request.GET.get('is_center', None)
    if is_center in ['True', 'true', '1', 'yes', 'Yes', 'Y', 'y']:
        qs = qs.filter(user__is_center=True)
    elif is_center in ['False', 'false', '0', 'no', 'No', 'N', 'n']:
        qs = qs.filter(user__is_center=False)

    username = request.GET.get('q', None)
    if username:
        qs = qs.filter(Q(user__first_name__icontains=username) | Q(user__last_name__icontains=username))

    country_group_id = request.GET.get('country_group_id', None)
    if country_group_id:
        qs = qs.filter(user__organisations__organisation_country__country_groups__uuid=country_group_id)

    country = request.GET.get('country', None)
    if country:
        qs = qs.filter(user__organisations__organisation_country__country__iso2_code__iexact=country)

    region_id = request.GET.get('region_id', None)
    if region_id:
        qs = qs.filter(user__organisations__admin_region__uuid=region_id)

    org_id = request.GET.get('org_id', None)
    if org_id:
        if org_id.lower() == "null":
            qs = qs.filter(user__organisations__isnull=True)
        else:
            qs = qs.filter(user__organisations__uuid=org_id)

    app_uuid = request.GET.get('app_id', None)
    if app_uuid:
        qs = qs.filter(user__application_roles__application__uuid=app_uuid)

    profile_id = request.GET.get('profile_id', None)
    if profile_id:
        qs = qs.filter(user__role_profiles__uuid=profile_id)

    exclude_profile_id = request.GET.get('exclude_profile_id', None)
    if exclude_profile_id:
        qs = qs.exclude(user__role_profiles__uuid=exclude_profile_id)

    modified_since = request.GET.get('modified_since', None)
    if modified_since:  # parse modified_since
        parsed = parse_datetime_with_timezone_support(modified_since)
        if parsed is None:
            raise ValueError("can not parse %s" % modified_since)
        qs = qs.filter(Q(user__last_modified__gte=parsed) | Q(user__useraddress__last_modified__gte=parsed) |
                       Q(user__userphonenumber__last_modified__gte=parsed))

    valid_until_lt = request.GET.get('valid_until_lt', None)
    if valid_until_lt:  # parse valid_until_less_then
        parsed = parse_datetime_with_timezone_support(valid_until_lt)
        if parsed is None:
            raise ValueError("can not parse %s" % valid_until_lt)
        qs = qs.filter(user__valid_until__lt=parsed)

    email_list = []
    for user_email in qs:
        email_list.append(user_email.email + '\n')

    response = HttpResponse(content_type='text')
    response.writelines(sorted(email_list))
    return response
