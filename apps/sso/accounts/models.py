# -*- coding: utf-8 -*-
from itertools import chain
import re
import logging
import uuid
from datetime import timedelta
from urlparse import urlparse

from sorl import thumbnail

from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.utils.crypto import get_random_string
from django.core import validators
from django.db import models
from django.db.models import Q
from django.conf import settings
from django.dispatch import receiver
from django.db.models import signals
from django.contrib.auth.models import Group, Permission, \
    PermissionsMixin, AbstractBaseUser, BaseUserManager
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.timezone import now
from django.utils.translation import pgettext_lazy, ugettext_lazy as _
from django.utils.text import capfirst
from l10n.models import Country
from sso.models import AbstractBaseModel, AddressMixin, PhoneNumberMixin, ensure_single_primary, get_filename
from sso.organisations.models import AdminRegion, Organisation
from sso.emails.models import GroupEmailManager
from sso.decorators import memoize
from sso.registration import default_username_generator
from sso.registration.models import RegistrationProfile
from sso.utils.loaddata import disable_for_loaddata
from current_user.models import CurrentUserField


logger = logging.getLogger(__name__)


# SUPERUSER_ROLE = 'Superuser'
# STAFF_ROLE = 'Staff'
# USER_ROLE = 'User'

DS108_EU = '35efc492b8f54f1f86df9918e8cc2b3d'
DS108_CEE = '2139dc55af8b42ec84a1ce9fd25fdf18'


class ApplicationManager(models.Manager):
    def get_by_natural_key(self, uuid):
        return self.get(uuid=uuid)


class Application(models.Model):
    order = models.IntegerField(default=0, help_text=_('Overwrites the alphabetic order.'))
    title = models.CharField(max_length=255)
    url = models.URLField(max_length=2047, blank=True)
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=True)
    global_navigation = models.BooleanField(_('global navigation'),
                                            help_text=_('Designates whether this application should be shown in the global navigation bar.'), default=True)
    is_active = models.BooleanField(_('active'), default=True, help_text=_('Designates whether this application should be provided.'))
    objects = ApplicationManager()
    
    class Meta:
        ordering = ['order', 'title']
        verbose_name = _("application")
        verbose_name_plural = _("applications")
        
    def link(self):
        if self.url:
            return u'<a href="%s">%s</a>' % (self.url, self.title)
        else:
            return ''
    link.allow_tags = True

    def natural_key(self):
        return self.uuid,

    def __unicode__(self):
        return u"%s" % self.title


class RoleManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)


class Role(models.Model):
    name = models.CharField(_("name"), unique=True, max_length=255)
    order = models.IntegerField(default=0, help_text=_('Overwrites the alphabetic order.'))
    group = models.ForeignKey(Group, blank=True, null=True, help_text=_('Associated group for SSO internal permission management.'))
    objects = RoleManager()
    
    class Meta:
        ordering = ['order', 'name']    
        verbose_name = _('role')
        verbose_name_plural = _('roles')

    def natural_key(self):
        return self.name,

    def __unicode__(self):
        return u"%s" % self.name
    

class ApplicationRoleManager(models.Manager):
    def get_by_natural_key(self, uuid, name):
        return self.get(application__uuid=uuid, role__name=name)


class ApplicationRole(models.Model):
    application = models.ForeignKey(Application)
    role = models.ForeignKey(Role)
    is_inheritable_by_org_admin = models.BooleanField(_('inheritable by organisation admin'), default=True,
                                                      help_text=_('Designates that the role can inherited by a organisation admin.'))
    is_inheritable_by_global_admin = models.BooleanField(_('inheritable by global admin'), default=True,
                                                         help_text=_('Designates that the role can inherited by a global admin.'))
    is_organisation_related = models.BooleanField(_('organisation related'), default=False,
                                                  help_text=_('Designates that the role will be deleted in case of a change of the organisation.'))

    objects = ApplicationRoleManager()
     
    class Meta:
        ordering = ['application', 'role']
        unique_together = (("application", "role"),)
        verbose_name = _('application role')
        verbose_name_plural = _('application roles')
    
    def natural_key(self):
        return self.application.natural_key(), self.role.natural_key()
    
    def __unicode__(self):
        return u"%s - %s" % (self.application, self.role)


class RoleProfile(AbstractBaseModel):
    name = models.CharField(_("name"), max_length=255)
    application_roles = models.ManyToManyField(ApplicationRole, help_text=_('Associates a group of application roles that are usually assigned together.'))
    order = models.IntegerField(default=0, help_text=_('Overwrites the alphabetic order.'))
    is_inheritable_by_org_admin = models.BooleanField(_('inheritable by organisation admin'), default=True,
                                                      help_text=_('Designates that the role profile can inherited by a organisation admin.'))
    is_inheritable_by_global_admin = models.BooleanField(_('inheritable by global admin'), default=True,
                                                         help_text=_('Designates that the role profile can inherited by a global admin.'))

    class Meta(AbstractBaseModel.Meta):
        ordering = ['order', 'name']
        verbose_name = _('role profile')
        verbose_name_plural = _('role profiles')
    
    def __unicode__(self):
        return u"%s" % self.name


class UserEmail(AbstractBaseModel):
    MAX_EMAIL_ADRESSES = 2
    email = models.EmailField(_('email address'), max_length=254, unique=True)
    confirmed = models.BooleanField(_('confirmed'), default=False)
    primary = models.BooleanField(_('primary'), default=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL)

    class Meta(AbstractBaseModel.Meta):
        verbose_name = _('email address')
        verbose_name_plural = _('email addresses')
        ordering = ['email']

    def __unicode__(self):
        return u"%s" % self.email


class UserManager(BaseUserManager):
    def _create_user(self, username, password,
                     is_staff, is_superuser, **extra_fields):
        """
        Creates and saves a User with the given username and password.
        """
        now = timezone.now()
        if not username:
            raise ValueError('The given username must be set')
        user = self.model(username=username,
                          is_staff=is_staff, is_active=True,
                          is_superuser=is_superuser, last_login=now,
                          date_joined=now, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, password=None, **extra_fields):
        return self._create_user(username, password, False, False,
                                 **extra_fields)

    def create_superuser(self, username, password, **extra_fields):
        return self._create_user(username, password, True, True,
                                 **extra_fields)

    def get_by_confirmed_or_primary_email(self, email):
        q = Q(useremail__email__iexact=email) & (Q(useremail__confirmed=True) | Q(useremail__primary=True))
        return self.filter(q).prefetch_related('useremail_set').get()

    def get_by_email(self, email):
        return self.filter(useremail__email__iexact=email).prefetch_related('useremail_set').get()


def generate_filename(instance, filename):
    return u'image/%s/%s' % (instance.uuid.hex, get_filename(filename.encode('ascii', 'replace')))


class User(AbstractBaseUser, PermissionsMixin):
    MAX_PICTURE_SIZE = 5242880  # 5 MB
    GENDER_CHOICES = [
        ('m', _('male')),
        ('f', _('female'))
    ]
    username = models.CharField(_('username'), max_length=30, unique=True, help_text=_('Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.'),
                                validators=[validators.RegexValidator(re.compile(r"^[\w.@+-]+$", flags=re.UNICODE), _('Enter a valid username.'), 'invalid')])
    first_name = models.CharField(_('first name'), max_length=30, blank=True)
    last_name = models.CharField(_('last name'), max_length=30, blank=True)
    # email = models.EmailField(_('email address'), blank=True)
    is_staff = models.BooleanField(_('staff status'), default=False, help_text=_('Designates whether the user can log into this admin site.'))
    is_active = models.BooleanField(_('active'), default=True, db_index=True, help_text=_('Designates whether this user should be treated as active. Unselect this instead of deleting accounts.'))
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    # extension
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=True)
    organisations = models.ManyToManyField(Organisation, verbose_name=_('organisations'), blank=True)
    admin_regions = models.ManyToManyField(AdminRegion, verbose_name=_('admin regions'), blank=True)
    admin_countries = models.ManyToManyField(Country, verbose_name=_('admin countries'), blank=True)
    application_roles = models.ManyToManyField(ApplicationRole, verbose_name=_('application roles'), blank=True)
    role_profiles = models.ManyToManyField(RoleProfile, verbose_name=_('role profiles'), blank=True, help_text=_('Organises a group of application roles that are usually assigned together.'))
    last_modified_by_user = CurrentUserField(verbose_name=_('last modified by'), related_name='+', on_delete=models.SET_NULL)
    last_modified = models.DateTimeField(_('last modified'), auto_now=True)
    created_by_user = models.ForeignKey('self', verbose_name=_('created by'), related_name='+', null=True, on_delete=models.SET_NULL)
    is_center = models.BooleanField(_('organisation'), default=False, help_text=_('Designates that this user is representing a organisation and not a private person.'))
    is_service = models.BooleanField(_('service'), default=False, help_text=_('Designates that this user is representing a service account and not a person.'))
    is_subscriber = models.BooleanField(_('subscriber'), default=False, help_text=_('Designates whether this user is a newsletter subscriber.'))
    picture = thumbnail.ImageField(_('picture'), upload_to=generate_filename, blank=True)  # , storage=MediaStorage())
    notes = models.TextField(_("Notes"), blank=True, max_length=1024)
    gender = models.CharField(_('gender'), max_length=255, choices=GENDER_CHOICES, blank=True)
    dob = models.DateField(_("date of birth"), blank=True, null=True)
    homepage = models.URLField(_("homepage"), max_length=512, blank=True)
    language = models.CharField(_('language'), max_length=254, choices=settings.LANGUAGES, blank=True)
    timezone = models.CharField(_('timezone'), blank=True, max_length=254)
    valid_until = models.DateTimeField(_('valid until'), blank=True, null=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    class Meta(AbstractBaseUser.Meta):
        verbose_name = _('user')
        verbose_name_plural = _('users')
        permissions = (
            ("read_user", "Can read user data"),
            ("access_all_users", "Can access all users"),
        )

    def get_full_name(self):
        """
        Returns the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        """Returns the short name for the user."""
        return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        """
        Sends an email to this User.
        """
        email = self.primary_email()
        assert(email is not None)

        send_mail(subject, message, from_email, [email.email], **kwargs)

    def primary_email(self):
        # iterate through useremail_set.all because useremail_set is cached
        # if we use prefetch_related('useremail_set')
        for user_mail in self.useremail_set.all():
            if user_mail.primary:
                return user_mail
        return None

    def create_primary_email(self, email, confirmed=None, delete_others=False):
        """
        make email as the primary email and all other emails non primary
        if the user email does not exist, it is created
        the other user emails are marked as not primary or deleted
        """
        email = UserManager.normalize_email(email)
        user_email = None
        for l_user_email in self.useremail_set.all():
            if email.lower() == l_user_email.email.lower():
                l_user_email.primary = True
                l_user_email.email = email
                if confirmed is not None:
                    l_user_email.confirmed = confirmed
                l_user_email.save()

                user_email = l_user_email
            else:
                if delete_others:
                    l_user_email.delete()
                else:
                    if l_user_email.primary:
                        l_user_email.primary = False
                        l_user_email.save(update_fields=['primary'])
        if not user_email:
            kwargs = {'email': email, 'user': self, 'primary': True}
            if confirmed is not None:
                kwargs['confirmed'] = confirmed
            user_email = UserEmail.objects.create(**kwargs)
        return user_email

    def confirm_primary_email_if_no_confirmed(self):
        if not UserEmail.objects.filter(confirmed=True, user=self).exists():
            # no confirmed email addresses for this user, then the password reset
            # must be send to the primary email and we can mark this email as confirmed
            user_email = UserEmail.objects.get(primary=True, user=self)
            assert(not user_email.confirmed)
            user_email.confirmed = True
            user_email.save(update_fields=['confirmed'])

    def ensure_single_primary_email(self):
        ensure_single_primary(self.useremail_set.all())

    @memoize
    def get_last_modified_deep(self):
        """
        get the max date of last_modified from user and corresponding address and phones
        and use _prefetched_objects_cache if available for performance in api lists
        """
        last_modified_list = [self.last_modified]
        if hasattr(self, '_prefetched_objects_cache') and ('useraddress' in self._prefetched_objects_cache):
            last_modified_list += [obj.last_modified for obj in self.useraddress_set.all()]
        else:
            last_modified_list += self.useraddress_set.values_list("last_modified", flat=True)
            
        if hasattr(self, '_prefetched_objects_cache') and ('userphonenumber' in self._prefetched_objects_cache):
            last_modified_list += [obj.last_modified for obj in self.userphonenumber_set.all()]
        else:
            last_modified_list += self.userphonenumber_set.values_list("last_modified", flat=True)
        
        last_modified = max(last_modified_list)
        return last_modified

    @classmethod
    def get_primary_or_none(cls, queryset):
        # iterate through all uses the prefetch_related cache
        for item in queryset:
            if item.primary:
                return item
        return None

    @classmethod
    def get_default_role_profile(cls):
        if settings.SSO_DEFAULT_ROLE_PROFILE_UUID:
            role_profile = RoleProfile.objects.none()
            try:
                role_profile = RoleProfile.objects.get(uuid=settings.SSO_DEFAULT_ROLE_PROFILE_UUID)
            except ObjectDoesNotExist:
                pass
            return role_profile                

    @classmethod
    def get_default_admin_profile(cls):
        if settings.SSO_DEFAULT_ADMIN_PROFILE_UUID:
            role_profile = RoleProfile.objects.none()
            try:
                role_profile = RoleProfile.objects.get(uuid=settings.SSO_DEFAULT_ADMIN_PROFILE_UUID)
            except ObjectDoesNotExist:
                pass
            return role_profile                

    @property
    def primary_address(self):
        return self.get_primary_or_none(self.useraddress_set.all())
        
    @property
    def primary_phone(self):
        return self.get_primary_or_none(self.userphonenumber_set.all())

    @memoize
    def get_apps(self):
        applicationrole_ids = self.get_applicationrole_ids()
        return Application.objects.distinct().filter(applicationrole__in=applicationrole_ids, is_active=True).\
            order_by('order').prefetch_related('applicationrole_set', 'applicationrole_set__role')

    def get_global_navigation_urls(self):
        applicationrole_ids = self.get_applicationrole_ids()
        return Application.objects.distinct().filter(applicationrole__in=applicationrole_ids,
                                                     is_active=True, 
                                                     global_navigation=True).order_by('order')
    
    def get_roles_by_app(self, app_uuid):
        applicationrole_ids = self.get_applicationrole_ids()
        return Role.objects.distinct().filter(applicationrole__in=applicationrole_ids, applicationrole__application__uuid=app_uuid)
    
    def get_group_and_role_permissions(self):
        """
        get all permissions the user has through his groups and roles
        """
        applicationrole_ids = self.get_applicationrole_ids()
        q = Q(group__role__applicationrole__in=applicationrole_ids,
              group__role__applicationrole__application__uuid=settings.SSO_APP_UUID) | Q(group__user=self)
        return Permission.objects.distinct().filter(q)

    @memoize
    def get_applicationrole_ids(self):
        approles1 = ApplicationRole.objects.filter(user=self).only("id").values_list('id', flat=True)
        approles2 = ApplicationRole.objects.filter(roleprofile__user=self).only("id").values_list('id', flat=True)
        # to get a list of distinct values, we create first a set and then a list
        return list(set(chain(approles1, approles2)))

    @memoize
    def get_applicationroles(self):
        applicationrole_ids = self.get_applicationrole_ids()
        return ApplicationRole.objects.filter(id__in=applicationrole_ids).select_related()

    @memoize
    def get_administrable_application_roles(self):
        """
        get a queryset for the admin
        """
        if self.is_superuser:
            return ApplicationRole.objects.all().select_related()
        else:
            applicationrole_ids = self.get_applicationrole_ids()
            # all roles the user has, with adequate inheritable flag
            if self.is_global_user_admin:
                application_roles = ApplicationRole.objects.filter(id__in=applicationrole_ids, 
                                                                   is_inheritable_by_global_admin=True).select_related()
            elif self.is_user_admin:
                application_roles = ApplicationRole.objects.filter(id__in=applicationrole_ids, 
                                                                   is_inheritable_by_org_admin=True).select_related()
            else:
                application_roles = ApplicationRole.objects.none()

            if self.is_app_admin:
                application_roles |= ApplicationRole.objects.filter(application__applicationadmin__admin=self)

            return application_roles
    
    @memoize
    def get_administrable_role_profiles(self):
        if self.is_superuser:
            return RoleProfile.objects.all().prefetch_related('application_roles', 'application_roles__role', 'application_roles__application')
        else:
            # all role profiles the user has, with adequate inheritable flag
            if self.is_global_user_admin:
                role_profiles = self.role_profiles.filter(is_inheritable_by_global_admin=True)
            elif self.is_user_admin:
                role_profiles = self.role_profiles.filter(is_inheritable_by_org_admin=True)
            else:
                role_profiles = self.role_profiles.none()

            if self.is_app_admin:
                role_profiles |= RoleProfile.objects.filter(roleprofileadmin__admin=self)

            return role_profiles.prefetch_related('application_roles', 'application_roles__role', 'application_roles__application').distinct()
    
    @memoize
    def get_administrable_user_organisations(self):
        """
        return a list of organisations from all the users we have admin rights on
        """
        if self.is_global_admin:
            return Organisation.objects.all().select_related('country', 'email')
        elif self.is_admin:
            return Organisation.objects.filter(
                Q(pk__in=self.organisations.all()) | Q(admin_region__in=self.admin_regions.all()) | Q(country__in=self.admin_countries.all())).select_related('country', 'email').distinct()
        else:
            return Organisation.objects.none()
    
    @memoize
    def get_administrable_user_regions(self):
        """
        return a list of regions from all the users we have admin rights on
        """
        if self.is_global_admin:
            return AdminRegion.objects.all()
        elif self.is_admin:
            return AdminRegion.objects.filter(Q(organisation__in=self.organisations.all()) | Q(pk__in=self.admin_regions.all()) | Q(country__in=self.admin_countries.all())).distinct()
        else:
            return AdminRegion.objects.none()

    @memoize
    def get_administrable_user_countries(self):
        """
        return a list of countries from all the users we have admin rights on
        """        
        if self.is_global_admin:
            return Country.objects.filter(organisation__isnull=False).distinct()
        elif self.is_admin:
            return Country.objects.filter(
                Q(organisation__admin_region__in=self.admin_regions.all()) |  # for adminregions without a associated country 
                Q(organisation__in=self.organisations.all()) | Q(adminregion__in=self.admin_regions.all()) | Q(pk__in=self.admin_countries.all())).distinct()
        else:
            return Country.objects.none()

    @memoize
    def get_administrable_organisations(self):
        """
        return a list of all organisations the user has admin rights on
        """
        if self.has_perms(["organisations.change_organisation", "organisations.access_all_organisations"]):
            return Organisation.objects.all().select_related('country', 'email')
        elif self.has_perm("organisations.change_organisation"):
            return Organisation.objects.filter(
                Q(user=self) | Q(admin_region__user=self) | Q(country__user=self)).select_related('country', 'email').distinct()
        else:
            return Organisation.objects.none()
    
    @memoize
    def get_assignable_organisation_countries(self):
        """
        return a list of countries the user can assign to organisations
        """        
        if self.has_perms(["organisations.change_organisation", "organisations.access_all_organisations"]):
            return Country.objects.filter(organisationcountry__isnull=False, organisationcountry__is_active=True).distinct()
        elif self.has_perm("organisations.change_organisation"):
            return Country.objects.filter(user=self, organisationcountry__is_active=True)
        else:
            return Country.objects.none()

    @memoize
    def get_assignable_organisation_regions(self):
        """
        return a list of regions the user can assign to organisations
        """        
        if self.has_perms(["organisations.change_organisation", "organisations.access_all_organisations"]):
            return AdminRegion.active_objects.all()
        elif self.has_perm("organisations.change_organisation"):
            return AdminRegion.active_objects.filter(Q(user=self) | Q(country__user=self)).distinct()
        else:
            return AdminRegion.objects.none()

    @memoize
    def get_administrable_regions(self):
        """
        return a list of all admin_regions the user has admin rights on
        """
        if self.has_perms(["organisations.change_adminregion", "organisations.access_all_organisations"]):
            return AdminRegion.objects.all()
        elif self.has_perm("organisations.change_adminregion"):
            return AdminRegion.objects.filter(Q(user=self) | Q(country__user=self)).distinct()
        else:
            return AdminRegion.objects.none()

    @memoize
    def get_administrable_region_countries(self):
        """
        return a list of countries from the administrable regions the user has 
        """        
        if self.has_perms(["organisations.change_adminregion", "organisations.access_all_organisations"]):
            return Country.objects.filter(organisationcountry__isnull=False).distinct()
        elif self.has_perm("organisations.change_adminregion"):
            return Country.objects.filter(Q(adminregion__user=self) | Q(user=self)).distinct()
        else:
            return Country.objects.none()

    @memoize
    def get_administrable_countries(self):
        """
        return a list of countries the user has admin rights on 
        """        
        if self.has_perms(["organisations.change_organisationcountry", "organisations.access_all_organisations"]):
            return Country.objects.filter(organisation__isnull=False).distinct()
        elif self.has_perm("organisations.change_organisationcountry"):
            return Country.objects.filter(user=self)
        else:
            return Country.objects.none()

    @memoize
    def get_count_of_registrationprofiles(self):
        qs = RegistrationProfile.objects.filter(is_access_denied=False, user__is_active=False, is_validated=True)
        return RegistrationProfile.objects.filter_administrable_registrationprofiles(self, qs).count()

    @memoize
    def get_count_of_centerchanges(self):
        organisationchanges = OrganisationChange.objects.all()
        return self.filter_administrable_organisationchanges(organisationchanges).count()

    def filter_administrable_organisationchanges(self, qs):
        #  filter the organisationchanges for who the authenticated user has access to
        if self.is_superuser:
            pass
        elif self.is_global_admin:
            qs = qs.filter(user__is_superuser=False)
        elif self.is_admin:
            organisations = self.get_administrable_user_organisations()
            q = Q(user__is_superuser=False) & Q(organisation__in=organisations)
            qs = qs.filter(q).distinct()
        else:
            qs = OrganisationChange.objects.none()
        return qs

    def filter_administrable_users(self, qs):
        # filter the users for who the authenticated user has admin rights
        if self.is_superuser:
            pass
        elif self.is_global_admin:
            qs = qs.filter(is_superuser=False)
        elif self.is_admin:
            organisations = self.get_administrable_user_organisations()
            q = Q(is_superuser=False) & Q(organisations__in=organisations)
            qs = qs.filter(q).distinct()
        else:
            qs = User.objects.none()
        return qs

    @property
    def is_global_admin(self):
        return self.has_perm("accounts.access_all_users")

    @property
    def is_admin(self):
        return self.is_user_admin or self.is_app_admin

    @property
    def is_global_user_admin(self):
        # can access user data: name, email, center and roles for all users
        return self.has_perms(["accounts.read_user", "accounts.access_all_users"])
    
    @property
    def is_user_admin(self):
        # can access user data: name, email, center and roles
        return self.has_perm("accounts.read_user")

    @property
    def is_app_admin(self):
        return self.applicationadmin_set.exists() or self.roleprofileadmin_set.exists()

    @property
    def is_global_organisation_admin(self):
        return self.has_perms(["organisations.change_organisation", "organisations.access_all_organisations"])
    
    @property
    def is_organisation_admin(self):
        return self.has_perm("organisations.change_organisation")

    @memoize
    def has_organisation(self, uuid):
        return Organisation.objects.filter(Q(uuid=uuid) & (Q(user=self) | Q(admin_region__user=self) | Q(country__user=self))).exists()
    
    @memoize
    def has_region(self, uuid):
        return AdminRegion.objects.filter(Q(uuid=uuid) & (Q(user=self) | Q(country__user=self))).exists()

    @memoize
    def has_country(self, uuid):
        return self.admin_countries.filter(organisationcountry__uuid=uuid).exists()
    
    def has_user_access_and_perm(self, uuid, perm):
        """
        Check if the user is an admin of the user with uuid and has the permission
        """
        return self.has_perm(perm) and self.has_user_access(uuid)

    def has_user_access(self, uuid):
        """
        Check if the user is an admin of the user with uuid
        """
        if self.is_superuser:
            return True
        elif self.has_perm("accounts.access_all_users"): 
            return not User.objects.get(uuid=uuid).is_superuser
        else:
            return User.objects.filter(Q(uuid=uuid) & (Q(organisations__user=self) | Q(organisations__admin_region__user=self) | Q(organisations__country__user=self))).exists()

    def has_organisation_user_access(self, uuid):
        if self.has_perm("accounts.access_all_users"):
            return True
        else:
            return self.has_organisation(uuid)
    
    def has_organisation_access_and_perm(self, uuid, perm):
        return self.has_perm(perm) and self.has_organisation_access(uuid)

    def has_organisation_access(self, uuid):
        if self.has_perm("organisations.access_all_organisations"):
            return True
        else:
            return self.has_organisation(uuid)

    def has_region_access(self, uuid):
        if self.has_perm("organisations.access_all_organisations"):
            return True
        else:
            return self.has_region(uuid)

    def has_country_access(self, uuid):
        if self.has_perm("organisations.access_all_organisations"):
            return True
        else:
            return self.has_country(uuid)

    @property
    def is_groupemail_admin(self):
        if self.has_perm('emails.change_groupemail') or GroupEmailManager.objects.filter(manager=self).exists():
            return True
        else:
            return False 

    def has_groupemail_access(self, uuid):
        if self.has_perm('emails.change_groupemail') or GroupEmailManager.objects.filter(group_email__uuid=uuid, manager=self).exists():
            return True
        else:
            return False 

    @property
    def is_complete(self):
        if self.first_name and self.last_name:
            return True
        else:
            return False

    @property
    def is_verified(self):
        if hasattr(self, 'otp_device'):
            return self.otp_device is not None
        return False
    
    @property
    def default_dharmashop_roles(self):
        ds_roles = []  # [{'uuid': 'e4a281ef13e1484b93fe4b7cc66374c8', 'roles': ['User']}]  # Dharma Shop 108 Home]
        roles = ['Guest', 'User'] if self.is_center else ['Guest']
        organisation = self.organisations.first()
        if organisation:                
            if organisation.country.iso2_code in ['CZ', 'SK', 'PL', 'RU', 'UA', 'RO', 'RS', 'HR', 'GR', 'BG', 'EE', 'LV']:
                # Dharma Shop 108 - Central and East Europe
                ds_roles += [{'uuid': DS108_CEE, 'roles': roles}]
            else:
                # Dharma Shop 108 - West Europe
                ds_roles += [{'uuid': DS108_EU, 'roles': roles}]
        return ds_roles

    def add_default_roles(self):
        app_roles_dict_array = self.default_dharmashop_roles
        self.add_roles(app_roles_dict_array)
        
        default_role_profile = self.get_default_role_profile()
        if default_role_profile:
            self.role_profiles.add(default_role_profile) 

        if self.is_center:  # for center accounts from streaming database
            default_admin_profile = self.get_default_admin_profile()
            if default_admin_profile:
                self.role_profiles.add(default_admin_profile)
        
    def add_roles(self, app_roles_dict_array):
        # get or create Roles
        for app_roles_dict_item in app_roles_dict_array:
            roles = []
            for roles_name in app_roles_dict_item['roles']:
                roles += [Role.objects.get_or_create(name=roles_name)[0]]
            app_roles_dict_item['roles'] = roles
        
        for app_roles_dict_item in app_roles_dict_array:
            try:
                application = Application.objects.get(uuid=app_roles_dict_item['uuid'])
                app_roles = []
                for role in app_roles_dict_item['roles']:
                    app_roles += [ApplicationRole.objects.get_or_create(application=application, role=role)[0]]
                self.application_roles.add(*app_roles)
            except ObjectDoesNotExist:
                logger.warning("Application %s does not exist" % app_roles_dict_item['uuid'])


class OrganisationChange(AbstractBaseModel):
    """
    a request from an user to change the organisation
    """
    user = models.OneToOneField(User)
    organisation = models.ForeignKey(Organisation)
    reason = models.TextField(_("reason"), max_length=2048)

    class Meta(AbstractBaseModel.Meta):
        verbose_name = _('organisation change')
        verbose_name_plural = _('organisation change')

    def get_absolute_url(self):
        return reverse('accounts:organisationchange_update', kwargs={'pk': self.pk})


class OneTimeMessage(AbstractBaseModel):
    user = models.ForeignKey(User)
    title = models.CharField(_("title"), max_length=255, default='')
    message = models.TextField(_("message"), blank=True, max_length=2048, default='')

    class Meta(AbstractBaseModel.Meta):
        verbose_name = _('one time message')
        verbose_name_plural = _('one time messages')


class UserAddress(AbstractBaseModel, AddressMixin):
    ADDRESSTYPE_CHOICES = (
        ('home', pgettext_lazy('address', 'Home')),
        ('work', _('Business')),
        ('other', _('Other')),            
    )
        
    address_type = models.CharField(_("address type"), choices=ADDRESSTYPE_CHOICES, max_length=20)
    user = models.ForeignKey(User)

    class Meta(AbstractBaseModel.Meta, AddressMixin.Meta):
        unique_together = (("user", "address_type"),)
    
    @classmethod
    def ensure_single_primary(cls, user):
        ensure_single_primary(user.useraddress_set.all())


class UserPhoneNumber(AbstractBaseModel, PhoneNumberMixin):
    PHONE_CHOICES = [
        ('home', pgettext_lazy('phone number', 'Home')),  # with translation context 
        ('mobile', _('Mobile')),
        ('work', _('Business')),
        ('fax', _('Fax')),
        ('pager', _('Pager')),
        ('other', _('Other')),
    ]
    phone_type = models.CharField(_("phone type"), help_text=_('Mobile, home, office, etc.'), choices=PHONE_CHOICES, max_length=20)
    user = models.ForeignKey(User)

    class Meta(AbstractBaseModel.Meta, PhoneNumberMixin.Meta):
        # unique_together = (("user", "phone_type"),)
        pass
    
    @classmethod
    def ensure_single_primary(cls, user):
        ensure_single_primary(user.userphonenumber_set.all())


class UserAssociatedSystem(models.Model):
    """
    Holds mappings to user IDs on other systems
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    application = models.ForeignKey(Application)
    userid = models.CharField(max_length=255)

    class Meta:
        verbose_name = _('associated system')
        verbose_name_plural = _('associated systems')
        unique_together = (("application", "userid"),)

    def __unicode__(self):
        return u"%s - %s" % (self.application, self.userid)    


class RoleProfileAdmin(AbstractBaseModel):
    role_profile = models.ForeignKey(RoleProfile, verbose_name=_("role profile"))
    admin = models.ForeignKey(User)

    class Meta(AbstractBaseModel.Meta):
        unique_together = (("role_profile", "admin"),)
        verbose_name = _('role profile admin')
        verbose_name_plural = _('role profile admins')


class ApplicationAdmin(AbstractBaseModel):
    application = models.ForeignKey(Application, verbose_name=_("application"))
    admin = models.ForeignKey(User)

    class Meta(AbstractBaseModel.Meta):
        unique_together = (("application", "admin"),)
        verbose_name = _('application admin')
        verbose_name_plural = _('application admins')


def update_or_create_organisation_account(organisation, old_email_value, new_email_value):
    """
    If a organisation was created or updated, we create or update a user account (the 'organisation' user)
    with the same email address.
    old_email_value can be None if there was no email for the organisation before or the organisation was just created
    """
    first_name = 'BuddhistCenter'
    last_name = capfirst(organisation.name)

    is_active = organisation.is_active
    organisation_account = None

    try:
        if old_email_value:
            organisation_account = User.objects.get_by_email(old_email_value)
        else:
            organisation_account = User.objects.get_by_email(new_email_value)
    except ObjectDoesNotExist:
        if is_active:
            organisation_account = User()
            organisation_account.set_password(get_random_string(40))
        else:
            # organisation is not activ and no user account exists, so don't create one
            pass

    if organisation_account:
        username = default_username_generator(first_name, last_name, user=organisation_account)
        organisation_account.first_name = first_name
        organisation_account.last_name = last_name
        organisation_account.username = username
        organisation_account.is_center = True
        organisation_account.is_active = organisation.is_active
        organisation_account.save()

        organisation_account.create_primary_email(new_email_value, confirmed=True, delete_others=True)

        organisation_account.organisations = [organisation]
        organisation_account.add_default_roles()


@receiver(signals.m2m_changed, sender=User.organisations.through)
@disable_for_loaddata
def user_organisation_changed(sender, instance, action, **kwargs):
    """
    Add regional dharmashop role if the user has no dharmashop role
    """
    if action == 'post_add' and settings.SSO_ADD_DHARMASHOP_ROLE:
        app_roles_dict_array = instance.default_dharmashop_roles
        if not instance.application_roles.filter(application__uuid__in=[DS108_CEE, DS108_EU]).exists():
            instance.add_roles(app_roles_dict_array)


@receiver(signals.post_save, sender=User)
@disable_for_loaddata
def update_user(sender, instance, created, **kwargs):
    if created and instance.last_modified_by_user:
        instance.created_by_user = instance.last_modified_by_user
        instance.save()


"""
@receiver(user_logged_in)
def add_cache_key(request, user, **kwargs):
    cache_key = ",".join([org.uuid.hex for org in user.get_profile().organisations.all().only('uuid')[:10]])
    request.session['_auth_cache_key'] = cache_key
"""
