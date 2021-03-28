import datetime
import logging
import uuid

from sorl import thumbnail

from current_user.models import CurrentUserField
from django.conf import settings
from django.contrib.auth.models import Permission, \
    PermissionsMixin, AbstractBaseUser, BaseUserManager
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Q
from django.db.utils import IntegrityError
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from sso.access_requests.models import AccessRequest
from sso.accounts.models import OrganisationChange
from sso.accounts.models.application import ApplicationRole, RoleProfile, Application, Role, get_applicationrole_ids
from sso.accounts.models.user_data import UserEmail, Membership
from sso.decorators import memoize
from sso.emails.models import GroupEmailManager
from sso.models import ensure_single_primary, get_filename
from sso.organisations.models import AdminRegion, Organisation, OrganisationCountry, Association
from sso.registration.models import RegistrationProfile
from sso.signals import default_roles
from sso.utils.email import send_mail

logger = logging.getLogger(__name__)


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

    @classmethod
    def recovery_expiration_date(cls):
        # The date after deactivated users should be deleted
        return timezone.now() - datetime.timedelta(minutes=settings.SSO_USER_RECOVERY_PERIOD_MINUTES)

    def create_user(self, username, password=None, **extra_fields):
        return self._create_user(username, password, False, False,
                                 **extra_fields)

    def create_superuser(self, username, password, **extra_fields):
        return self._create_user(username, password, True, True,
                                 **extra_fields)

    def get_by_confirmed_or_primary_email(self, email):
        q = Q(useremail__email=email) & (Q(useremail__confirmed=True) | Q(useremail__primary=True))
        return self.filter(q).prefetch_related('useremail_set').get()

    def get_by_email(self, email):
        return self.filter(useremail__email=email).prefetch_related('useremail_set').get()


def generate_filename(instance, filename):
    return 'image/%s/%s' % (instance.uuid.hex, get_filename(filename.encode('ascii', 'replace')))


class User(AbstractBaseUser, PermissionsMixin):
    MAX_PICTURE_SIZE = 5242880  # 5 MB
    GENDER_CHOICES = [
        ('m', _('male')),
        ('f', _('female'))
    ]
    username_validator = UnicodeUsernameValidator()

    username = models.CharField(_('username'), max_length=70, unique=True,
                                help_text=_('Required. 70 characters or fewer. Letters, digits and @/./+/-/_ only.'),
                                validators=[username_validator], error_messages={
            'unique': _("A user with that username already exists."), }, )
    first_name = models.CharField(_('first name'), max_length=30, blank=True)
    last_name = models.CharField(_('last name'), max_length=40, blank=True)
    is_staff = models.BooleanField(_('staff status'), default=False, help_text=_('Designates whether the user can log into this admin site.'))
    is_active = models.BooleanField(_('active'), default=True, db_index=True, help_text=_(
        'Designates whether this user should be treated as active. Unselect this instead of deleting accounts.'))
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=True)
    organisations = models.ManyToManyField(Organisation, verbose_name=_('organisations'), through=Membership, blank=(not settings.SSO_ORGANISATION_REQUIRED))
    admin_regions = models.ManyToManyField(AdminRegion, verbose_name=_('admin regions'), blank=True)
    admin_organisation_countries = models.ManyToManyField(OrganisationCountry, verbose_name=_('admin countries'), blank=True)
    admin_associations = models.ManyToManyField(Association, verbose_name=_('admin associations'), blank=True)
    app_admin_regions = models.ManyToManyField(AdminRegion, related_name='app_admin_user', verbose_name=_('app admin regions'), blank=True)
    app_admin_organisation_countries = models.ManyToManyField(OrganisationCountry, related_name='app_admin_user',
                                                              verbose_name=_('app admin countries'), blank=True)
    app_admin_associations = models.ManyToManyField(Association, related_name='app_admin_user', verbose_name=_('app admin associations'), blank=True)
    application_roles = models.ManyToManyField(ApplicationRole, verbose_name=_('application roles'), blank=True)
    role_profiles = models.ManyToManyField(RoleProfile, verbose_name=_('role profiles'), blank=True,
                                           help_text=_('Organises a group of application roles that are usually '
                                                       'assigned together.'))
    last_modified_by_user = CurrentUserField(verbose_name=_('last modified by'), related_name='+', on_delete=models.SET_NULL)
    last_modified = models.DateTimeField(_('last modified'), auto_now=True)
    created_by_user = models.ForeignKey('self', verbose_name=_('created by'), related_name='+', null=True, on_delete=models.SET_NULL)
    is_center = models.BooleanField(_('organisation'), default=False,
                                    help_text=_('Designates that this user is representing a organisation and not a '
                                                'private person.'))
    is_service = models.BooleanField(_('service'), default=False,
                                     help_text=_('Designates that this user is representing a service account and '
                                                 'not a person.'))
    is_subscriber = models.BooleanField(_('subscriber'), default=False, help_text=_('Designates whether this user is a newsletter subscriber.'))
    picture = thumbnail.ImageField(_('picture'), upload_to=generate_filename, blank=True)  # , storage=MediaStorage())
    gender = models.CharField(_('gender'), max_length=255, choices=GENDER_CHOICES, blank=True)
    dob = models.DateField(_("date of birth"), blank=True, null=True)
    homepage = models.URLField(_("homepage"), max_length=512, blank=True)
    language = models.CharField(_('language'), max_length=254, choices=settings.LANGUAGES, blank=True)
    timezone = models.CharField(_('timezone'), blank=True, max_length=254)
    valid_until = models.DateTimeField(_('valid until'), blank=True, null=True)
    last_ip = models.GenericIPAddressField(_('last ip address'), blank=True, null=True)
    is_stored_permanently = models.BooleanField(_('store permanently'), help_text=_('Do not delete, even if inactive'), default=False)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    class Meta(AbstractBaseUser.Meta):
        verbose_name = _('user')
        verbose_name_plural = _('users')
        permissions = (
            ("read_user", "Can read user data"),
            ("access_all_users", "Can access all users"),
            ("app_admin_access_all_users", "Can access all users as App admin"),
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
        if self.primary_email() is not None:
            recipient_list = [self.primary_email().email]
            if from_email is not None:
                from_email = force_str(from_email)
            return send_mail(subject, message, recipient_list, from_email=from_email, **kwargs)
        else:
            logger.error('User %s has no primary_email', self.username)
        return 0

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
            assert (not user_email.confirmed)
            user_email.confirmed = True
            user_email.save(update_fields=['confirmed'])

    def ensure_single_primary_email(self):
        ensure_single_primary(self.useremail_set.all())

    def update_last_modified(self):
        self.save(update_fields=['last_modified'])

    @memoize
    def get_last_modified_deep(self):
        """
        get the max date of last_modified from user and corresponding address and phones
        and use _prefetched_objects_cache if available for performance in api lists
        """
        last_modified_list = [self.last_modified]
        if hasattr(self, '_prefetched_objects_cache') and ('useraddress_set' in self._prefetched_objects_cache):
            last_modified_list += [obj.last_modified for obj in self.useraddress_set.all()]
        else:
            last_modified_list += self.useraddress_set.values_list("last_modified", flat=True)

        if hasattr(self, '_prefetched_objects_cache') and ('userphonenumber_set' in self._prefetched_objects_cache):
            last_modified_list += [obj.last_modified for obj in self.userphonenumber_set.all()]
        else:
            last_modified_list += self.userphonenumber_set.values_list("last_modified", flat=True)

        if hasattr(self, '_prefetched_objects_cache') and ('useremail_set' in self._prefetched_objects_cache):
            last_modified_list += [obj.last_modified for obj in self.useremail_set.all()]
        else:
            last_modified_list += self.useremail_set.values_list("last_modified", flat=True)

        if hasattr(self, '_prefetched_objects_cache') and ('userattribute_set' in self._prefetched_objects_cache):
            last_modified_list += [obj.last_modified for obj in self.userattribute_set.all()]
        else:
            last_modified_list += self.userattribute_set.values_list("last_modified", flat=True)

        last_modified = max(last_modified_list)
        return last_modified

    @classmethod
    def get_primary_or_none(cls, queryset):
        # iterate through all items, uses the prefetch_related cache
        for item in queryset:
            if item.primary:
                return item
        return None

    @classmethod
    def get_default_role_profile(cls, role_uuid=None):
        role_profile = RoleProfile.objects.none()
        if role_uuid is None:
            role_uuid = settings.SSO_DEFAULT_MEMBER_PROFILE_UUID
        if role_uuid:
            try:
                role_profile = RoleProfile.objects.get(uuid=role_uuid)
            except ObjectDoesNotExist:
                pass
        return role_profile

    @classmethod
    def get_default_guest_profile(cls, role_uuid=None):
        role_profile = None
        if role_uuid is None:
            role_uuid = settings.SSO_DEFAULT_GUEST_PROFILE_UUID
        if role_uuid:
            try:
                role_profile = RoleProfile.objects.get(uuid=role_uuid)
            except ObjectDoesNotExist:
                pass
        return role_profile

    @classmethod
    def get_default_admin_profile(cls):
        role_profile = RoleProfile.objects.none()
        if settings.SSO_DEFAULT_ADMIN_PROFILE_UUID:
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
        return Application.objects.distinct().filter(applicationrole__in=applicationrole_ids, is_active=True). \
            order_by('order').prefetch_related('applicationrole_set', 'applicationrole_set__role')

    def get_global_navigation_urls(self):
        applicationrole_ids = self.get_applicationrole_ids()
        return Application.objects.distinct().filter(applicationrole__in=applicationrole_ids,
                                                     is_active=True,
                                                     global_navigation=True).order_by('order')

    def get_roles_by_app(self, app_uuid):
        applicationrole_ids = self.get_applicationrole_ids()
        return Role.objects.distinct().filter(applicationrole__in=applicationrole_ids,
                                              applicationrole__application__uuid=app_uuid)

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
        return get_applicationrole_ids(self.id)

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
            return application_roles

    @memoize
    def get_administrable_role_profiles(self):
        if self.is_superuser:
            return RoleProfile.objects.all().prefetch_related('application_roles', 'application_roles__role',
                                                              'application_roles__application')
        else:
            # all role profiles the user has, with adequate inheritable flag
            if self.is_global_user_admin:
                role_profiles = self.role_profiles.filter(is_inheritable_by_global_admin=True)
            elif self.is_user_admin:
                role_profiles = self.role_profiles.filter(is_inheritable_by_org_admin=True)
            else:
                role_profiles = self.role_profiles.none()
            return role_profiles.prefetch_related('application_roles', 'application_roles__role',
                                                  'application_roles__application').distinct()

    @memoize
    def get_administrable_app_admin_application_roles(self):
        """
        get a queryset for the admin
        """
        if self.is_app_admin():
            return ApplicationRole.objects.filter(application__applicationadmin__admin=self)
        else:
            return ApplicationRole.objects.none()

    @memoize
    def get_administrable_app_admin_role_profiles(self):
        # all role profiles the user has, with adequate inheritable flag
        role_profiles = self.role_profiles.none()
        if self.is_app_admin():
            role_profiles = RoleProfile.objects.filter(roleprofileadmin__admin=self)

        return role_profiles.prefetch_related('application_roles', 'application_roles__role',
                                              'application_roles__application').distinct()

    @memoize
    def get_administrable_user_organisations(self):
        """
        return a list of organisations from all the users we have admin rights on
        """
        if self.is_global_user_admin:
            return Organisation.objects.all().select_related('organisation_country__country', 'email', 'association')
        elif self.is_user_admin:
            return Organisation.objects.filter(
                Q(pk__in=self.organisations.all()) |
                Q(admin_region__in=self.admin_regions.all()) |
                Q(organisation_country__in=self.admin_organisation_countries.all()) |
                Q(association__in=self.admin_associations.all())) \
                .select_related('organisation_country__country', 'email', 'association').distinct()
        else:
            return Organisation.objects.none()

    @memoize
    def get_administrable_user_regions(self):
        """
        return a list of regions from all the users we have admin rights on
        """
        if self.is_global_user_admin:
            return AdminRegion.objects.all()
        elif self.is_user_admin:
            return AdminRegion.objects.filter(
                Q(organisation__in=self.organisations.all()) |
                Q(pk__in=self.admin_regions.all()) |
                Q(organisation_country__in=self.admin_organisation_countries.all()) |
                Q(organisation_country__association__in=self.admin_associations.all())) \
                .distinct()
        else:
            return AdminRegion.objects.none()

    @memoize
    def get_administrable_user_countries(self):
        """
        return a list of countries from all the users we have admin rights on
        """
        if self.is_global_user_admin:
            return OrganisationCountry.objects.filter(is_active=True).distinct().select_related('country',
                                                                                                'association')
        elif self.is_user_admin:
            return OrganisationCountry.objects.filter(
                # for adminregions without a associated country
                Q(organisation__admin_region__in=self.admin_regions.all()) |
                Q(organisation__in=self.organisations.all()) |
                Q(adminregion__in=self.admin_regions.all()) |
                Q(pk__in=self.admin_organisation_countries.all()) |
                Q(association__in=self.admin_associations.all())) \
                .select_related('country', 'association').distinct()
        else:
            return OrganisationCountry.objects.none()

    @memoize
    def get_administrable_user_associations(self):
        """
        return a list of associations from all the users we have admin rights on
        """
        if self.is_global_user_admin:
            return Association.objects.all()
        else:
            return self.admin_associations.all()

    @memoize
    def get_administrable_app_admin_user_countries(self):
        """
        return a list of countries from all the users we have app admin rights on
        """
        if self.is_global_app_admin or self.is_superuser:
            return OrganisationCountry.objects.all().select_related('country', 'association')
        elif self.is_app_admin():
            return OrganisationCountry.objects.filter(
                # for admin regions without a associated country
                Q(organisation__admin_region__in=self.app_admin_regions.all()) |
                Q(organisation__in=self.organisations.all()) |
                Q(adminregion__in=self.app_admin_regions.all()) |
                Q(pk__in=self.app_admin_organisation_countries.all()) |
                Q(association__in=self.app_admin_associations.all())). \
                select_related('country', 'association').distinct()
        else:
            return OrganisationCountry.objects.none()

    @memoize
    def get_administrable_app_admin_user_organisations(self):
        """
        return a list of organisations from all the users we have rights to manage app_roles
        """
        if self.is_global_app_admin or self.is_superuser:
            return Organisation.objects.all().select_related('organisation_country__country', 'email')
        elif self.is_app_admin():
            return Organisation.objects.filter(
                Q(pk__in=self.organisations.all()) |
                Q(admin_region__in=self.app_admin_regions.all()) |
                Q(organisation_country__in=self.app_admin_organisation_countries.all()) |
                Q(association__in=self.app_admin_associations.all())) \
                .select_related('organisation_country__country', 'email').distinct()
        else:
            return Organisation.objects.none()

    @memoize
    def get_administrable_app_admin_user_regions(self):
        """
        return a list of regions from all the users we have admin rights on
        """
        if self.is_global_app_admin or self.is_superuser:
            return AdminRegion.objects.all()
        elif self.is_app_admin():
            return AdminRegion.objects.filter(
                Q(organisation__in=self.organisations.all()) |
                Q(pk__in=self.app_admin_regions.all()) |
                Q(organisation_country__in=self.app_admin_organisation_countries.all()) |
                Q(organisation_country__association__in=self.app_admin_associations.all())) \
                .distinct()
        else:
            return AdminRegion.objects.none()

    @memoize
    def get_administrable_organisations(self):
        """
        return a list of all organisations the user has admin rights on
        """
        if self.has_perms(["organisations.change_organisation", "organisations.access_all_organisations"]):
            return Organisation.objects.filter(association__is_external=False).prefetch_related(
                'organisation_country__country', 'email', 'organisationpicture_set')
        elif self.has_perm("organisations.change_organisation"):
            orgs = Organisation.objects.filter(
                Q(association__is_external=False)
                & (Q(user=self) |
                   Q(admin_region__user=self) |
                   Q(organisation_country__user=self) |
                   Q(association__user=self))).distinct()
            return Organisation.objects.filter(id__in=orgs).prefetch_related('organisation_country__country', 'email', 'organisationpicture_set')
        else:
            return Organisation.objects.none()

    @memoize
    def administrable_organisations_exists(self):
        """
        return if the user has admin rights on organisations
        """
        if self.has_perms(["organisations.change_organisation", "organisations.access_all_organisations"]):
            return Organisation.objects.all().exists()
        elif self.has_perm("organisations.change_organisation"):
            return Organisation.objects.filter(
                Q(association__is_external=False)
                & (Q(user=self) |
                   Q(admin_region__user=self) |
                   Q(organisation_country__user=self) |
                   Q(association__user=self))).exists()
        else:
            return False

    @memoize
    def get_assignable_associations(self):
        """
        return a list of Associations the user can assign to organisations
        """
        if self.has_perms(["organisations.change_organisation", "organisations.access_all_organisations"]):
            return Association.objects.filter(is_active=True, is_external=False).distinct()
        elif self.has_perm("organisations.change_organisation"):
            return Association.objects.filter(user=self, is_active=True, is_external=False)
        else:
            return Association.objects.none()

    @memoize
    def get_assignable_organisation_countries(self):
        """
        return a list of OrganisationCountry the user can assign to organisations
        """
        if self.has_perms(["organisations.change_organisation", "organisations.access_all_organisations"]):
            return OrganisationCountry.objects.filter(
                is_active=True, association__is_active=True, association__is_external=False) \
                .distinct().prefetch_related('country', 'association')
        elif self.has_perm("organisations.change_organisation"):
            return OrganisationCountry.objects.filter(
                Q(is_active=True, association__is_active=True, association__is_external=False)
                & (Q(user=self) |
                   Q(association__user=self))).prefetch_related('country', 'association')
        else:
            return OrganisationCountry.objects.none()

    @memoize
    def get_assignable_organisation_regions(self):
        """
        return a list of regions the user can assign to organisations
        """
        if self.has_perms(["organisations.change_organisation", "organisations.access_all_organisations"]):
            return AdminRegion.active_objects.filter(
                is_active=True,
                organisation_country__is_active=True,
                organisation_country__association__is_active=True,
                organisation_country__association__is_external=False,
            )
        elif self.has_perm("organisations.change_organisation"):
            return AdminRegion.active_objects.filter(
                Q(is_active=True,
                  organisation_country__is_active=True,
                  organisation_country__association__is_active=True,
                  organisation_country__association__is_external=False)
                & (Q(user=self) |
                   Q(organisation_country__user=self) |
                   Q(organisation_country__association__user=self))).distinct()
        else:
            return AdminRegion.objects.none()

    @memoize
    def get_administrable_regions(self):
        """
        return a list of all admin_regions the user has admin rights on
        """
        if self.has_perms(["organisations.change_adminregion", "organisations.access_all_organisations"]):
            return AdminRegion.objects.filter(organisation_country__association__is_external=False)
        elif self.has_perm("organisations.change_adminregion"):
            return AdminRegion.objects.filter(
                Q(organisation_country__association__is_external=False)
                & (
                        Q(user=self) |
                        Q(organisation_country__user=self) |
                        Q(organisation_country__association__user=self))).distinct()
        else:
            return AdminRegion.objects.none()

    @memoize
    def get_administrable_region_countries(self):
        """
        return a list of countries from the administrable regions the user has
        """
        if self.has_perms(["organisations.change_adminregion", "organisations.access_all_organisations"]):
            return OrganisationCountry.objects.filter(association__is_external=False) \
                .distinct().prefetch_related('country', 'association')
        elif self.has_perm("organisations.change_adminregion"):
            return OrganisationCountry.objects.filter(
                Q(association__is_external=False)
                & (
                        Q(adminregion__user=self) |
                        Q(user=self) |
                        Q(association__user=self))).distinct().prefetch_related('country', 'association')
        else:
            return OrganisationCountry.objects.none()

    @memoize
    def get_administrable_countries(self):
        """
        return a list of countries the user has admin rights on
        """
        if self.has_perms(["organisations.change_organisationcountry", "organisations.access_all_organisations"]):
            return OrganisationCountry.objects.filter(association__is_external=False) \
                .distinct().prefetch_related('country', 'association')
        elif self.has_perm("organisations.change_organisationcountry"):
            return OrganisationCountry.objects.filter(
                Q(association__is_external=False)
                & (Q(user=self) |
                   Q(association__user=self))).prefetch_related('country', 'association')
        else:
            return OrganisationCountry.objects.none()

    @memoize
    def get_administrable_associations(self):
        """
        return a list of associations the user has admin rights on
        """
        if self.is_superuser:
            return Association.objects.all()
        elif self.has_perm("organisations.change_association"):
            return Association.objects.filter(user=self)
        else:
            return Association.objects.none()

    @memoize
    def get_count_of_registrationprofiles(self):
        qs = RegistrationProfile.objects.filter(is_access_denied=False, user__is_active=False, is_validated=True,
                                                check_back=False, user__last_login__isnull=True)
        return RegistrationProfile.objects.filter_administrable_registrationprofiles(self, qs).count()

    @memoize
    def get_count_of_organisationchanges(self):
        organisationchanges = OrganisationChange.open.all()
        return self.filter_administrable_organisationchanges(organisationchanges).count()

    @memoize
    def get_count_of_extend_access(self):
        access_requests = AccessRequest.open.all()
        return self.filter_administrable_access_requests(access_requests).count()

    def filter_administrable_access_requests(self, qs):
        #  filter the access_request for who the authenticated user has access to
        if self.is_superuser:
            pass
        elif self.is_global_user_admin:
            qs = qs.filter(user__is_superuser=False)
        elif self.is_user_admin:
            organisations = self.get_administrable_user_organisations()
            q = Q(user__is_superuser=False) & Q(user__is_service=False)
            q &= (Q(user__organisations__in=organisations) | Q(organisation__in=organisations))
            qs = qs.filter(q).distinct()
        else:
            qs = AccessRequest.objects.none()
        return qs

    def filter_administrable_organisationchanges(self, qs):
        #  filter the organisationchanges for who the authenticated user has access to
        if self.is_superuser:
            pass
        elif self.is_global_user_admin:
            qs = qs.filter(user__is_superuser=False)
        elif self.is_user_admin:
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
        elif self.is_global_user_admin:
            qs = qs.filter(is_superuser=False, is_service=False)
        elif self.is_user_admin:
            organisations = self.get_administrable_user_organisations()
            q = Q(is_superuser=False) & Q(is_service=False) & Q(organisations__in=organisations)
            qs = qs.filter(q).distinct()
        else:
            qs = User.objects.none()
        return qs

    def filter_administrable_user_emails(self, qs):
        # filter the users for who the authenticated user has admin rights
        if self.is_superuser:
            pass
        elif self.is_global_user_admin:
            qs = qs.filter(user__is_superuser=False, user__is_service=False)
        elif self.is_user_admin:
            organisations = self.get_administrable_user_organisations()
            q = Q(user__is_superuser=False) & Q(user__is_service=False) & Q(user__organisations__in=organisations)
            qs = qs.filter(q).distinct()
        else:
            qs = qs.none()
        return qs

    def filter_administrable_app_admin_users(self, qs):
        # filter the users for who the authenticated user can manage app_roles
        if self.is_global_app_admin:
            qs = qs.filter(is_superuser=False, is_service=False)
        elif self.is_app_admin():
            organisations = self.get_administrable_app_admin_user_organisations()
            q = Q(is_superuser=False) & Q(is_service=False) & Q(organisations__in=organisations)
            qs = qs.filter(q).distinct()
        else:
            qs = User.objects.none()
        return qs

    @property
    def is_guest(self):
        # iterate over all profiles does not makes a new DB query
        # when prefetch_related('role_profiles') is used
        # otherwise self.role_profiles.filter(uuid=settings.SSO_DEFAULT_MEMBER_PROFILE_UUID).exists()
        # would be better
        for profile in self.role_profiles.all():
            if profile.uuid != settings.SSO_DEFAULT_GUEST_PROFILE_UUID:
                return False
        for _ in self.application_roles.all():
            return False
        return True

    @property
    def is_global_user_admin(self):
        # can access user data: name, email, center and roles for all users
        return self.is_user_admin and self.has_perm("accounts.access_all_users")

    @property
    def is_user_admin(self):
        # can access user data: name, email, center and roles
        return self.has_perms(["accounts.read_user"])  # is used also by the api for read_only access

    @property
    def is_global_app_admin(self):
        return self.is_app_admin() and self.has_perm("accounts.app_admin_access_all_users")

    @memoize
    def is_app_admin(self):
        return self.applicationadmin_set.exists() or self.roleprofileadmin_set.exists()

    @property
    def is_global_organisation_admin(self):
        return self.is_organisation_admin and self.has_perms(["organisations.access_all_organisations"])

    @property
    def is_organisation_admin(self):
        return self.has_perm("organisations.change_organisation")

    @memoize
    def has_organisation(self, uuid):
        return Organisation.objects.filter(
            Q(uuid=uuid, association__is_external=False) &
            (Q(user=self) |
             Q(admin_region__user=self) |
             Q(organisation_country__user=self) |
             Q(association__user=self))).exists()

    @memoize
    def has_region(self, uuid):
        return AdminRegion.objects.filter(
            Q(uuid=uuid, organisation_country__association__is_external=False)
            & (Q(user=self) |
               Q(organisation_country__user=self) |
               Q(organisation_country__association__user=self))).exists()

    @memoize
    def has_country(self, uuid):
        return OrganisationCountry.objects.filter(
            Q(uuid=uuid, association__is_external=False)
            & (Q(user=self) |
               Q(association__user=self))).exists()

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
            user = User.objects.get(uuid=uuid)
            return not user.is_superuser and not user.is_service
        else:
            return User.objects.filter(
                Q(uuid=uuid, is_superuser=False, is_service=False)
                & (Q(organisations__user=self) |
                   Q(organisations__admin_region__user=self) |
                   Q(organisations__organisation_country__user=self) |
                   Q(organisations__association__user=self))).exists()

    def has_access_request_access(self, access_request):
        """
        Check if the user is an admin of organisation the user with uuid
        or if the user is an admin of the organisation in the AccessRequest
        """
        if access_request.organisation:
            return self.has_organisation_user_access(access_request.organisation.uuid)
        else:
            return self.has_user_access(access_request.user.uuid)

    def has_app_admin_user_access(self, uuid):
        """
        Check if the user is an admin of the user with uuid
        """
        if self.is_superuser:
            return True
        if self.is_global_app_admin:
            user = User.objects.get(uuid=uuid)
            return not user.is_superuser and not user.is_service
        else:
            return User.objects.filter(
                Q(uuid=uuid, is_superuser=False, is_service=False)
                & (Q(organisations__user=self) |
                   Q(organisations__admin_region__app_admin_user=self) |
                   Q(organisations__organisation_country__app_admin_user=self) |
                   Q(organisations__association__app_admin_user=self))).exists()

    def has_organisation_user_access(self, uuid):
        # used in sso_xxx_theme
        if self.has_perm("accounts.access_all_users"):
            return True
        else:
            return self.has_organisation(uuid)

    def has_organisation_access_and_perm(self, uuid, perm):
        return self.has_perm(perm) and self.has_organisation_access(uuid)

    def has_organisation_access(self, uuid):
        if self.has_perm("organisations.access_all_organisations"):
            return Organisation.objects.filter(uuid=uuid, association__is_external=False).exists()
        else:
            return self.has_organisation(uuid)

    def has_region_access(self, uuid):
        if self.has_perm("organisations.access_all_organisations"):
            return AdminRegion.objects.filter(uuid=uuid, organisation_country__association__is_external=False).exists()
        else:
            return self.has_region(uuid)

    def has_country_access(self, uuid):
        if self.has_perm("organisations.access_all_organisations"):
            return OrganisationCountry.objects.filter(uuid=uuid, association__is_external=False).exists()
        else:
            return self.has_country(uuid)

    @property
    def is_groupemail_admin(self):
        if self.has_perm('emails.change_groupemail') or GroupEmailManager.objects.filter(manager=self).exists():
            return True
        else:
            return False

    def has_groupemail_access(self, uuid):
        if self.has_perm('emails.change_groupemail') or GroupEmailManager.objects.filter(group_email__uuid=uuid,
                                                                                         manager=self).exists():
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

    def add_default_roles(self):
        app_roles = []
        role_profiles = [self.get_default_role_profile()]

        # enable brand specific modification
        default_roles.send_robust(sender=self.__class__, user=self, app_roles=app_roles, role_profiles=role_profiles)

        self.add_roles(app_roles)

        for role_profile in role_profiles:
            self.role_profiles.add(role_profile)
        self.update_last_modified()

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
            except IntegrityError as e:
                # programming error?
                logger.exception(e)

    def set_organisations(self, organisations):
        # Ensure last_modified will be updated in all cases the user changes the organisation
        # Force evaluation of `organisations` in case it's a queryset whose value
        # could be affected by `manager.clear()`. Refs #19816.
        organisations = tuple(organisations)
        self.organisations.clear()
        self.organisations.through.objects.bulk_create([
            self.organisations.through(**{
                'user_id': self.id,
                'organisation_id': organisation.id,
            })
            for organisation in organisations
        ])
        ensure_single_primary(self.organisations.through.objects.filter(user_id=self.id))

    def add_organisation(self, organisation, primary=False):
        # Ensure last_modified will be updated in all cases the user changes the organisation
        self.organisations.through.objects.create(**{
            'user_id': self.id,
            'organisation_id': organisation.id,
            'primary': primary
        })
        ensure_single_primary(self.organisations.through.objects.filter(user_id=self.id))

    def remove_organisation_related_permissions(self,
                                                organisation_related_application_roles=None,
                                                organisation_related_role_profiles=None):
        if organisation_related_application_roles is None:
            organisation_related_application_roles = ApplicationRole.objects.filter(is_organisation_related=True)
        if organisation_related_role_profiles is None:
            organisation_related_role_profiles = RoleProfile.objects.filter(is_organisation_related=True)
        self.application_roles.remove(*list(organisation_related_application_roles))
        self.role_profiles.remove(*list(organisation_related_role_profiles))
