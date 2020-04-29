import logging
import uuid
from itertools import chain

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.validators import validate_slug
from django.db import models
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from sso.models import AbstractBaseModel, AbstractBaseModelManager

logger = logging.getLogger(__name__)


def get_applicationrole_ids(user_id, filter=None):
    approles1 = ApplicationRole.objects.filter(user__id=user_id).only("id").values_list('id', flat=True)
    approles2 = ApplicationRole.objects.filter(roleprofile__user__id=user_id).only("id").values_list('id', flat=True)
    if filter is not None:
        approles1 = approles1.filter(filter)
        approles2 = approles2.filter(filter)
    # to get a list of distinct values, we create first a set and then a list
    return list(set(chain(approles1, approles2)))


class ApplicationManager(models.Manager):
    def get_by_natural_key(self, uuid):
        return self.get(uuid=uuid)


class Application(models.Model):
    order = models.IntegerField(default=0, help_text=_('Overwrites the alphabetic order.'))
    title = models.CharField(max_length=255)
    url = models.URLField(max_length=2047, blank=True)
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=True)
    global_navigation = models.BooleanField(
        _('global navigation'),
        help_text=_('Designates whether this application should be shown in the global navigation bar.'),
        default=True)
    is_internal = models.BooleanField(_('internal'), default=False)
    is_active = models.BooleanField(_('active'), default=True,
                                    help_text=_('Designates whether this application should be provided.'))
    redirect_to_after_first_login = models.BooleanField(
        _('redirect to after first login'), default=False,
        help_text=_('Designates whether the user should redirected to this app after the first login.'))
    notes = models.TextField(_("Notes"), blank=True, max_length=2048)
    required_scope = models.CharField(_("Required scope"), blank=True, max_length=32,
                                      validators=[validate_slug],
                                      help_text=_('Required OAuth2 scope to get the application roles.'))
    objects = ApplicationManager()

    class Meta:
        ordering = ['order', 'title']
        verbose_name = _("application")
        verbose_name_plural = _("applications")

    @mark_safe
    def link(self):
        if self.url:
            return '<a href="%s">%s</a>' % (self.url, self.url)
        else:
            return ''

    def natural_key(self):
        return self.uuid,

    def __str__(self):
        return self.title


class RoleManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)


class Role(models.Model):
    name = models.CharField(_("name"), unique=True, max_length=255)
    order = models.IntegerField(default=0, help_text=_('Overwrites the alphabetic order.'))
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, blank=True, null=True,
                              help_text=_('Associated group for SSO internal permission management.'))
    objects = RoleManager()

    class Meta:
        ordering = ['order', 'name']
        verbose_name = _('role')
        verbose_name_plural = _('roles')

    def natural_key(self):
        return self.name,

    def __str__(self):
        return self.name


class ApplicationRoleManager(models.Manager):
    def get_by_natural_key(self, uuid, name):
        return self.get(application__uuid=uuid, role__name=name)


class ApplicationRole(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    is_inheritable_by_org_admin = models.BooleanField(
        _('inheritable by organisation admin'), default=True,
        help_text=_('Designates that the role can inherited by a organisation admin.'))
    is_inheritable_by_global_admin = models.BooleanField(
        _('inheritable by global admin'), default=True,
        help_text=_('Designates that the role can inherited by a global admin.'))
    is_organisation_related = models.BooleanField(
        _('organisation related'), default=False,
        help_text=_('Designates that the role will be deleted in case of a change of the organisation.'))

    objects = ApplicationRoleManager()

    class Meta:
        ordering = ['application', 'role']
        unique_together = (("application", "role"),)
        verbose_name = _('application role')
        verbose_name_plural = _('application roles')

    def natural_key(self):
        return self.application.natural_key() + self.role.natural_key()

    def __str__(self):
        return "%s - %s" % (self.application, self.role)


class RoleProfile(AbstractBaseModel):
    name = models.CharField(_("name"), max_length=255)
    application_roles = models.ManyToManyField(ApplicationRole, blank=True, help_text=_(
        'Associates a group of application roles that are usually assigned together.'))
    order = models.IntegerField(default=0, help_text=_('Overwrites the alphabetic order.'))
    is_inheritable_by_org_admin = models.BooleanField(
        _('inheritable by organisation admin'), default=True,
        help_text=_('Designates that the role profile can inherited by a organisation admin.'))
    is_inheritable_by_global_admin = models.BooleanField(
        _('inheritable by global admin'), default=True,
        help_text=_('Designates that the role profile can inherited by a global admin.'))
    is_organisation_related = models.BooleanField(
        _('organisation related'), default=False,
        help_text=_('Designates that the role will be deleted in case of a change of the organisation.'))

    class Meta(AbstractBaseModel.Meta):
        ordering = ['order', 'name']
        verbose_name = _('role profile')
        verbose_name_plural = _('role profiles')

    def __str__(self):
        return self.name


class UserAssociatedSystem(models.Model):
    """
    Holds mappings to user IDs on other systems
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    userid = models.CharField(max_length=255)

    class Meta:
        verbose_name = _('associated system')
        verbose_name_plural = _('associated systems')
        unique_together = (("application", "userid"),)

    def __str__(self):
        return "%s - %s" % (self.application, self.userid)


class RoleProfileAdmin(AbstractBaseModel):
    role_profile = models.ForeignKey(RoleProfile, on_delete=models.CASCADE, verbose_name=_("role profile"))
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta(AbstractBaseModel.Meta):
        unique_together = (("role_profile", "admin"),)
        verbose_name = _('role profile admin')
        verbose_name_plural = _('role profile admins')


class ApplicationAdmin(AbstractBaseModel):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, verbose_name=_("application"))
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta(AbstractBaseModel.Meta):
        unique_together = (("application", "admin"),)
        verbose_name = _('application admin')
        verbose_name_plural = _('application admins')


class UserNoteManager(AbstractBaseModelManager):
    def create_note(self, user, created_by_user, notes, **kwargs):
        if len(notes) > 0:
            return self.create(user=user, note="\n".join(notes), created_by_user=created_by_user, **kwargs)
        else:
            return self.none()


class UserNote(AbstractBaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    note = models.TextField(_("Note"), max_length=1024)
    created_by_user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('created by'), related_name='+',
                                        null=True, on_delete=models.SET_NULL)

    objects = UserNoteManager()

    class Meta(AbstractBaseModel.Meta):
        verbose_name = _('user note')
        verbose_name_plural = _('user notes')
