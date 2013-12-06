# -*- coding: utf-8 -*-
import os
from django.db import models
from django.db.models import Q
from django.conf import settings
from django.dispatch import receiver
from django.db.models import signals
from django.utils.timezone import now
from django.template import loader
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.tokens import default_token_generator as default_pwd_reset_token_generator
from django.contrib.sites.models import get_current_site
from django.core.mail import send_mail
from django.core.mail.message import EmailMessage
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import get_language, activate, ugettext_lazy as _
from django.utils.text import get_valid_filename

from south.modelsinspector import add_introspection_rules
from sorl.thumbnail import ImageField
from l10n.models import Country

from sso.fields import UUIDField
from sso.utils import disable_for_loaddata
from current_user.models import CurrentUserField
import logging

logger = logging.getLogger(__name__)


SUPERUSER_ROLE = 'Superuser'
#STAFF_ROLE = 'Staff'
#USER_ROLE = 'User'

class AbstractBaseModel(models.Model):
    uuid = UUIDField(version=4, unique=True, editable=True)
    last_modified = models.DateTimeField(_('last modified'), auto_now=True, default=now)
    name = models.CharField(_("name"), max_length=255)
    
    def __unicode__(self):
        return u"%s" % (self.name)
    
    class Meta:
        abstract = True
        ordering = ['name']
        get_latest_by = 'last_modified'
        

class Application(models.Model):
    order = models.IntegerField(default=0, help_text=_('Overwrites the alphabetic order.'))
    title = models.CharField(max_length=255)
    url = models.URLField(max_length=2047, blank=True)
    uuid = UUIDField(version=4, unique=True, editable=True)
    enable_url = models.BooleanField(_('enable url'), help_text=_('Designates whether this application should be shown in '
                    'the global navigation bar.'), default=True)

    def link(self):
        if self.url:
            return u'<a href="%s">%s</a>' % (self.url, self.title)
        else:
            return ''
    link.allow_tags = True

    def __unicode__(self):
        return u"%s" % (self.title)

    class Meta:
        ordering = ['order', 'title']
        verbose_name = _("application")
        verbose_name_plural = _("applications")
        

class Role(models.Model):
    name = models.CharField(_("name"), max_length=255)
    order = models.IntegerField(default=0, help_text=_('Overwrites the alphabetic order.'))
    
    def __unicode__(self):
        return u"%s" % (self.name)
    
    class Meta:
        ordering = ['order', 'name']


class ApplicationRole(models.Model):
    application = models.ForeignKey(Application)
    role = models.ForeignKey(Role)
    is_inheritable_by_org_admin = models.BooleanField(_('inheritable by organisation admin'), default=True,
        help_text=_('Designates that role can inherited by a organisation admin.'))
    is_inheritable_by_global_admin = models.BooleanField(_('inheritable by global admin'), default=True,
        help_text=_('Designates that role can inherited by a global admin.'))
    
    class Meta:
        ordering = ['application', 'role']
        unique_together = (("application", "role"),)
    
    def __unicode__(self):
        return u"%s - %s" % (self.application, self.role)


class Region(AbstractBaseModel):
    pass

 
class Organisation(AbstractBaseModel):
    iso2_code = models.CharField(_('ISO alpha-2'), max_length=2)
    last_update = models.DateTimeField(auto_now=True, default=now)
    email = models.EmailField(_('e-mail address'), blank=True)
    region = models.ForeignKey(Region, blank=True, null=True)

    def __unicode__(self):
        return u"%s (%s)" % (self.name, self.iso2_code)
    
    class Meta(AbstractBaseModel.Meta):
        verbose_name = _('center')
        verbose_name_plural = _('centers')


def get_filename(filename):
    return os.path.normpath(get_valid_filename(os.path.basename(filename)))

class User(AbstractUser):
    def generate_filename(self, filename):
        return u'image/%s/%s' % (self.uuid, get_filename(filename.encode('ascii', 'replace'))) 

    uuid = UUIDField(version=4, editable=True, unique=True)
    organisations = models.ManyToManyField(Organisation, blank=True, null=True)
    application_roles = models.ManyToManyField(ApplicationRole, blank=True, null=True)
    last_modified_by_user = CurrentUserField(verbose_name=_('last modified by'), related_name='+')
    last_modified = models.DateTimeField(_('last modified'), auto_now=True)
    created_by_user = models.ForeignKey('self', verbose_name=_('created by'), related_name='+', null=True)
    is_center = models.BooleanField(_('center'), default=False, help_text=_('Designates that this user is representing a center and not a private person.'))
    is_subscriber = models.BooleanField(_('subscriber'), default=False, help_text=_('Designates whether this user is a DWBN News subscriber.'))
    picture = ImageField(_('picture'), upload_to=generate_filename, blank=True)

    def get_apps(self):
        return Application.objects.distinct().filter(applicationrole__user__uuid=self.uuid).order_by('order').prefetch_related('applicationrole_set', 'applicationrole_set__role')

    def get_app_urls(self):
        return Application.objects.distinct().filter(applicationrole__user__uuid=self.uuid, enable_url=True).order_by('order')
    
    def get_roles_by_app(self, app_uuid):
        return Role.objects.filter(applicationrole__user__uuid=self.uuid, applicationrole__application__uuid=app_uuid)
    
    def get_applicationroles(self):
        return ApplicationRole.objects.filter(user__uuid=self.uuid).select_related()

    def get_inheritable_application_roles(self):
        if self.is_superuser:
            return ApplicationRole.objects.all().select_related()
        
        # all roles the user has with flag adequate inheritable flag
        if self.has_perm("accounts.change_all_users"):
            application_roles = self.application_roles.filter(is_inheritable_by_global_admin=True)
        elif self.has_perm("accounts.change_org_users") or self.has_perm("accounts.change_reg_users"):
            application_roles = self.application_roles.filter(is_inheritable_by_org_admin=True)
        else:
            application_roles = self.application_roles.none()
                    
        application_roles.select_related()
        q = Q(id__in=application_roles.values_list('id', flat=True))
        
        # additionaly all roles of application where the user is a superuser
        for application_role in application_roles:
            if application_role.role.name == SUPERUSER_ROLE:
                q |= Q(application__id=application_role.application.id)
         
        app_roles = ApplicationRole.objects.filter(q).select_related()
        return app_roles
    
    def get_administrable_organisations(self):
        """
        return a list of all organisations the user has admin rights on
        """
        if self.has_perm("accounts.change_all_users"):
            return Organisation.objects.all()
        if self.has_perm("accounts.change_reg_users"):
            # Regional Admin
            return Organisation.objects.filter(Q(user=self) | Q(region__organisation__user=self)).distinct()
        elif self.has_perm("accounts.change_org_users"):
            return self.organisations.all()
        else:
            return Organisation.objects.none()
    
    def get_countries_of_administrable_organisations(self):
        """
        return a list of countries from the administrable organisations the user has 
        """
        return Country.objects.filter(iso2_code__in=self.get_administrable_organisations().values_list('iso2_code', flat=True))

    @property
    def can_add_users(self):
        return self.is_staff and self.is_active and self.get_administrable_organisations().exists()
    
    @property
    def is_complete(self):
        if self.organisations.all().exists() and self.first_name and self.last_name:  # or self.has_perm("accounts.change_org_users")) \
            return True
        else:
            return False
        
    def add_standard_roles(self):
        roles = []
        # Dharma Shop 108 - Home
        application = Application.objects.get_or_create(uuid='e4a281ef13e1484b93fe4b7cc66374c8', defaults={'title': 'Dharma Shop 108 - Home'})[0]
        user_role = Role.objects.get_or_create(name='User')[0]
        roles += [ApplicationRole.objects.get_or_create(application=application, role=user_role)[0]]
        
        if self.is_center:
            wiki = Application.objects.get_or_create(uuid='b8c38af479e54f4c94faf9d8184528fe', defaults={'title': 'Wiki'})[0]
            roles += [ApplicationRole.objects.get_or_create(application=wiki, role=user_role)[0]]
        
        if self.organisations.filter(iso2_code__in=['CZ', 'SK', 'PL', 'RU', 'UA', 'RO', 'RS', 'HR', 'GR', 'BG', 'EE', 'LV']).exists():
            # Dharma Shop 108 - Central and East Europe
            application = Application.objects.get_or_create(uuid='2139dc55af8b42ec84a1ce9fd25fdf18', defaults={'title': 'Dharma Shop 108 - Central and East Europe'})[0]    
            guest_role = Role.objects.get_or_create(name='Guest')[0]
            roles += [ApplicationRole.objects.get_or_create(application=application, role=guest_role)[0]]
            if self.is_center:
                roles += [ApplicationRole.objects.get_or_create(application=application, role=user_role)[0]]
        else:
            # Dharma Shop 108 - West Europe
            application = Application.objects.get_or_create(uuid='35efc492b8f54f1f86df9918e8cc2b3d', defaults={'title': 'Dharma Shop 108 - West Europe'})[0]    
            guest_role = Role.objects.get_or_create(name='Guest')[0]
            roles += [ApplicationRole.objects.get_or_create(application=application, role=guest_role)[0]]
            if self.is_center:
                roles += [ApplicationRole.objects.get_or_create(application=application, role=user_role)[0]]
       
        self.application_roles.add(*roles)

    class Meta:
        permissions = (
            ("change_reg_users", "Can manage region users"),
            ("change_org_users", "Can manage organisation users"),
            ("change_all_users", "Can manage all users"),
        )


class UserAssociatedSystem(models.Model):
    """
    Holds mappings to user IDs on other systems
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    application = models.ForeignKey(Application)
    userid = models.CharField(max_length=255)

    class Meta:
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
    organisation = user.organisations.all()[:1]
    if organisation and organisation[0].iso2_code in ['DE', 'CH', 'AT', 'LI']:
        language = 'de'
    else:
        language = 'en'
    use_https = request.is_secure()
    current_site = get_current_site(request)
    site_name = settings.SITE_NAME
    domain = current_site.domain
    c = {
        'email': user.email,
        'username': user.username,
        'domain': domain,
        'site_name': site_name,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': token_generator.make_token(user),
        'protocol': use_https and 'https' or 'http',
    }

    cur_language = get_language()
        
    try:
        activate(language)
        subject = loader.render_to_string(subject_template_name, c)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        email = loader.render_to_string(email_template_name, c)
    finally:
        activate(cur_language)

    send_mail(subject, email, from_email, [user.email], fail_silently=settings.DEBUG)


@receiver(signals.post_save, sender=User)
@disable_for_loaddata
def update_user(sender, instance, created, **kwargs):
    if created and instance.last_modified_by_user:
        instance.created_by_user = instance.last_modified_by_user
        instance.save()

"""
@receiver(signals.pre_save, sender=User)
@disable_for_loaddata
def update_user2(sender, instance, **kwargs):
    # TODO: update the last_modified_by_user of the UserProfile if the
    # User was changed 
    if instance.pk is not None:
        orig = get_user_model().objects.get(pk=instance.pk)
        
        for field in instance._meta.fields:
            if getattr(orig, field.attname) != getattr(instance, field.attname):
                logger.debug('%s changed' % field.attname)
"""                

@receiver(signals.post_save, sender=LogEntry)
def send_notification_email(sender, instance, **kwargs):
    if settings.LOCAL_DEV:
        return
    change = instance
    subject = u"model %(model)s has been changed by %(user)s" % {'model': change.content_type, 'user': change.user}
    subject = ''.join(subject.splitlines())
    body = loader.render_to_string('accounts/email/change_email.html', {'change': change})
    msg = EmailMessage(subject, body, to=settings.USER_CHANGE_EMAIL_RECIPIENT_LIST)
    msg.content_subtype = "html"  # Main content is now text/html
    msg.send(fail_silently=settings.DEBUG)


#@receiver(user_logged_in)
#def add_cache_key(request, user, **kwargs):
#    cache_key = ",".join([org.uuid for org in user.get_profile().organisations.all().only('uuid')[:10]])    
#    request.session['_auth_cache_key'] = cache_key
