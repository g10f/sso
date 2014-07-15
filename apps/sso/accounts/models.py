# -*- coding: utf-8 -*-
import os
import datetime
from itertools import chain
from django.db import models
from django.db.models import Q
from django.conf import settings
from django.dispatch import receiver
from django.db.models import signals
from django.template import loader
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.contrib.auth.tokens import default_token_generator as default_pwd_reset_token_generator
from django.contrib.sites.models import get_current_site
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.timezone import now
from django.utils.translation import get_language, activate, pgettext_lazy, ugettext_lazy as _
from django.utils.text import get_valid_filename
from south.modelsinspector import add_introspection_rules
from sorl import thumbnail
from l10n.models import Country
from sso.fields import UUIDField
from sso.models import AbstractBaseModel, AddressMixin, PhoneNumberMixin, ensure_single_primary
from sso.organisations.models import AdminRegion, Organisation
from sso.decorators import memoize
from utils.loaddata import disable_for_loaddata
from current_user.models import CurrentUserField
import logging

logger = logging.getLogger(__name__)


SUPERUSER_ROLE = 'Superuser'
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
    uuid = UUIDField(version=4, unique=True, editable=True)
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
        return (self.uuid, )

    def __unicode__(self):
        return u"%s" % (self.title)


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

    def natural_key(self):
        return (self.name, )

    def __unicode__(self):
        return u"%s" % (self.name)
    

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
    objects = ApplicationRoleManager()
     
    class Meta:
        ordering = ['application', 'role']
        unique_together = (("application", "role"),)
        verbose_name = _('application role')
        verbose_name_plural = _('application roles')
    
    def natural_key(self):
        return (self.application.natural_key(), self.role.natural_key())

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
        return u"%s" % (self.name)


def get_filename(filename):
    return os.path.normpath(get_valid_filename(os.path.basename(filename)))


class User(AbstractUser):
    GENDER_CHOICES = [
        ('m', _('male')),
        ('f', _('female'))
    ]
    
    def generate_filename(self, filename):
        return u'image/%s/%s' % (self.uuid, get_filename(filename.encode('ascii', 'replace'))) 

    uuid = UUIDField(version=4, editable=True, unique=True)
    organisations = models.ManyToManyField(Organisation, verbose_name=_('organisations'), blank=True, null=True)
    admin_regions = models.ManyToManyField(AdminRegion, verbose_name=_('admin regions'), blank=True, null=True)
    admin_countries = models.ManyToManyField(Country, verbose_name=_('admin countries'), blank=True, null=True)
    application_roles = models.ManyToManyField(ApplicationRole, verbose_name=_('application roles'), blank=True, null=True)
    role_profiles = models.ManyToManyField(RoleProfile, verbose_name=_('role profiles'), blank=True, null=True, help_text=_('Organises a group of application roles that are usually assigned together.'))
    last_modified_by_user = CurrentUserField(verbose_name=_('last modified by'), related_name='+')
    last_modified = models.DateTimeField(_('last modified'), auto_now=True)
    created_by_user = models.ForeignKey('self', verbose_name=_('created by'), related_name='+', null=True)
    is_center = models.BooleanField(_('center'), default=False, help_text=_('Designates that this user is representing a center and not a private person.'))
    is_subscriber = models.BooleanField(_('subscriber'), default=False, help_text=_('Designates whether this user is a DWBN News subscriber.'))
    picture = thumbnail.ImageField(_('picture'), upload_to=generate_filename, blank=True)
    notes = models.TextField(_("Notes"), blank=True, max_length=1024)
    gender = models.CharField(_('gender'), max_length=255, choices=GENDER_CHOICES, blank=True)
    dob = models.DateField(_("date of birth"), blank=True, null=True)
    homepage = models.URLField(_("homepage"), max_length=512, blank=True)
    language = models.CharField(_('language'), max_length=254, choices=settings.LANGUAGES, blank=True)
    
    class Meta(AbstractUser.Meta):
        permissions = (
            ("access_all_users", "Can access all users"),
        )
    
    @classmethod
    def get_primary_or_none(cls, queryset):
        # iterate through all uses the prefetch_related cache
        for item in queryset:
            if item.primary:
                return item
        return None

    @classmethod
    def get_default_role_profile(cls):
        if 'DEFAULT_ROLE_PROFILE_UUID' in settings.SSO_CUSTOM:
            role_profile = RoleProfile.objects.none()
            try:
                role_profile = RoleProfile.objects.get(uuid=settings.SSO_CUSTOM['DEFAULT_ROLE_PROFILE_UUID'])
            except ObjectDoesNotExist:
                pass
            return role_profile                

    @classmethod
    def get_default_admin_profile(cls):
        if 'DEFAULT_ADMIN_PROFILE_UUID' in settings.SSO_CUSTOM:
            role_profile = RoleProfile.objects.none()
            try:
                role_profile = RoleProfile.objects.get(uuid=settings.SSO_CUSTOM['DEFAULT_ADMIN_PROFILE_UUID'])
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
        applicationroles = self.get_applicationroles()
        return Application.objects.distinct().filter(applicationrole__in=applicationroles, is_active=True).\
            order_by('order').prefetch_related('applicationrole_set', 'applicationrole_set__role')

    def get_global_navigation_urls(self):
        applicationroles = self.get_applicationroles()
        return Application.objects.distinct().filter(applicationrole__in=applicationroles, 
                                                     is_active=True, 
                                                     global_navigation=True).order_by('order')
    
    def get_roles_by_app(self, app_uuid):
        applicationroles = self.get_applicationroles()
        return Role.objects.distinct().filter(applicationrole__in=applicationroles, 
                                              applicationrole__application__uuid=app_uuid)
    
    def get_permissions(self):
        applicationroles = self.get_applicationroles()
        q = Q(group__role__applicationrole__in=applicationroles, 
              group__role__applicationrole__application__uuid=settings.SSO_CUSTOM['APP_UUID']) | Q(group__user=self)  
        return Permission.objects.distinct().filter(q)
        
    @memoize
    def get_applicationroles(self):
        approles1 = ApplicationRole.objects.distinct().filter(user__uuid=self.uuid).select_related()
        approles2 = ApplicationRole.objects.distinct().filter(roleprofile__user__uuid=self.uuid).select_related()
        
        # to get a list of distinct values, we create first a set and then a list 
        return list(set(chain(approles1, approles2)))

    @memoize
    def get_administrable_application_roles(self):
        """
        get a queryset for the admin
        """
        if self.is_superuser:
            return ApplicationRole.objects.all().select_related()
        else:
            applicationrole_ids = [x.id for x in self.get_applicationroles()]
            # all roles the user has, with adequate inheritable flag
            if self.is_global_user_admin:
                application_roles = ApplicationRole.objects.filter(id__in=applicationrole_ids, 
                                                                   is_inheritable_by_global_admin=True).select_related()
            elif self.is_user_admin:
                application_roles = ApplicationRole.objects.filter(id__in=applicationrole_ids, 
                                                                   is_inheritable_by_org_admin=True).select_related()
            else:
                application_roles = ApplicationRole.objects.none()
            
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
                        
            return role_profiles.prefetch_related('application_roles', 'application_roles__role', 'application_roles__application')    
    
    @memoize
    def get_administrable_user_organisations(self):
        """
        return a list of organisations from all the users we have admin rights on
        """
        if self.is_global_user_admin:
            return Organisation.objects.all().select_related('country', 'email')
        elif self.is_user_admin:
            return Organisation.objects.filter(
                Q(user=self) | Q(admin_region__user=self) | Q(country__user=self)).select_related('country', 'email').distinct()
        else:
            return Organisation.objects.none()
    
    @memoize
    def get_administrable_user_regions(self):
        """
        return a list of all organisations the user has admin rights on
        """
        if self.is_global_user_admin:
            return AdminRegion.objects.all()
        elif self.is_user_admin:
            return AdminRegion.objects.filter(Q(user=self) | Q(country__user=self)).distinct()
        else:
            return AdminRegion.objects.none()

    @memoize
    def get_administrable_user_countries(self):
        """
        return a list of countries from the administrable organisations the user has 
        """        
        if self.is_global_user_admin:
            return Country.objects.filter(organisation__isnull=False).distinct()
        elif self.is_user_admin:
            return Country.objects.filter(
                Q(organisation__admin_region__user=self) |  # for adminregions without a associated country 
                Q(organisation__user=self) | Q(adminregion__user=self) | Q(user=self)).distinct()
        else:
            return Country.objects.none()

    @memoize
    def get_administrable_organisations(self):
        """
        return a list of all organisations the user has admin rights on
        """
        if self.is_global_organisation_admin:
            return Organisation.objects.all().select_related('country', 'email')
        elif self.is_organisation_admin:
            return Organisation.objects.filter(
                Q(user=self) | Q(admin_region__user=self) | Q(country__user=self)).select_related('country', 'email').distinct()
        else:
            return Organisation.objects.none()
    
    def filter_administrable_users(self, qs):
        # filter the users for who the authenticated user has admin rights
        if self.is_superuser:
            pass
        elif self.is_global_user_admin:
            qs = qs.filter(is_superuser=False)
        elif self.is_user_admin:
            organisations = self.get_administrable_user_organisations()
            q = Q(is_superuser=False) & Q(organisations__in=organisations)
            qs = qs.filter(q).distinct()
        else:
            qs = User.objects.none()
        return qs
        
    @property
    def is_global_user_admin(self):
        return self.has_perms(["accounts.change_user", "accounts.access_all_users"])
    
    @property
    def is_user_admin(self):
        return self.has_perm("accounts.change_user")

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
    def is_complete(self):
        if self.first_name and self.last_name:  # or self.has_perm("accounts.change_org_users")) \
            return True
        else:
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
        
        default_admin_profile = self.get_default_admin_profile()
        if default_admin_profile and self.is_center:  # for center accounts from streaming database
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


add_introspection_rules([
    (
        [UUIDField],  # Class(es) these apply to
        [],         # Positional arguments (not used)
        {           # Keyword argument 
            "verbose_name": ["verbose_name", {"default": None}],
            "name": ["name", {"default": None}],
            "auto": ["auto", {"default": True}],
            "version": ["version", {"default": 1}],
        },
    ),
], ["^sso\.fields\.UUIDField"])  

from current_user import models as current_user
add_introspection_rules([
    (
        [current_user.CurrentUserField],  # Class(es) these apply to
        [],         # Positional arguments (not used)
        {           # Keyword argument 
            "related_name": ["rel.related_name", {"default": None}],
        },
    ),
], ["^current_user\.models\.CurrentUserField"])    


def send_account_created_email(user, request, token_generator=default_pwd_reset_token_generator,
                               from_email=None,
                               email_template_name='accounts/account_created_email.txt',
                               subject_template_name='accounts/account_created_email_subject.txt'
                               ):
    
    use_https = request.is_secure()
    current_site = get_current_site(request)
    site_name = settings.SSO_CUSTOM['SITE_NAME']
    domain = current_site.domain
    expiration_date = now() + datetime.timedelta(settings.PASSWORD_RESET_TIMEOUT_DAYS)
    
    c = {
        'email': user.email,
        'username': user.username,
        'domain': domain,
        'site_name': site_name,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': token_generator.make_token(user),
        'protocol': use_https and 'https' or 'http',
        'expiration_date': expiration_date
    }

    cur_language = get_language()
        
    try:
        language = user.language if user.language else settings.LANGUAGE_CODE
        activate(language)
        subject = loader.render_to_string(subject_template_name, c)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        email = loader.render_to_string(email_template_name, c)
    finally:
        activate(cur_language)

    send_mail(subject, email, from_email, [user.email], fail_silently=settings.DEBUG)


@receiver(signals.m2m_changed, sender=User.organisations.through)
@disable_for_loaddata
def user_organisation_changed(sender, instance, action, **kwargs):
    """
    Add regional dharmashop role if the user has no dharmashop role
    """
    if action == 'post_add' and settings.SSO_CUSTOM.get('ADD_DHARMASHOP_ROLE', False):
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
from django.contrib.admin.models import LogEntry
@receiver(signals.post_save, sender=LogEntry)
def send_notification_email(sender, instance, **kwargs):
    from django.core.mail.message import EmailMessage
    if settings.LOCAL_DEV:
        return
    change = instance
    subject = u"model %(model)s has been changed by %(user)s" % {'model': change.content_type, 'user': change.user}
    subject = ''.join(subject.splitlines())
    body = loader.render_to_string('accounts/email/change_email.html', {'change': change})
    msg = EmailMessage(subject, body, to=settings.USER_CHANGE_EMAIL_RECIPIENT_LIST)
    msg.content_subtype = "html"  # Main content is now text/html
    msg.send(fail_silently=settings.DEBUG)
"""

"""
@receiver(user_logged_in)
def add_cache_key(request, user, **kwargs):
    cache_key = ",".join([org.uuid for org in user.get_profile().organisations.all().only('uuid')[:10]])    
    request.session['_auth_cache_key'] = cache_key
"""
