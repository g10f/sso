import datetime
import logging

from current_user.models import CurrentUserField
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
from sso.accounts.models.application import ApplicationRole, RoleProfile
from sso.models import AbstractBaseModel, AddressMixin, PhoneNumberMixin, ensure_single_primary, \
    CaseInsensitiveEmailField, AbstractBaseModelManager
from sso.organisations.models import Organisation

logger = logging.getLogger(__name__)


class UserEmail(AbstractBaseModel):
    MAX_EMAIL_ADRESSES = 2
    email = CaseInsensitiveEmailField(_('email address'), max_length=254, unique=True)
    confirmed = models.BooleanField(_('confirmed'), default=False)
    primary = models.BooleanField(_('primary'), default=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta(AbstractBaseModel.Meta):
        verbose_name = _('email address')
        verbose_name_plural = _('email addresses')
        ordering = ['email']

    def __str__(self):
        return self.email


class UserAddress(AbstractBaseModel, AddressMixin):
    ADDRESSTYPE_CHOICES = (
        ('home', pgettext_lazy('address', 'Home')),
        ('work', _('Business')),
        ('other', _('Other')),
    )

    address_type = models.CharField(_("address type"), choices=ADDRESSTYPE_CHOICES, max_length=20)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

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
    phone_type = models.CharField(_("phone type"), help_text=_('Mobile, home, office, etc.'), choices=PHONE_CHOICES,
                                  max_length=20)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta(AbstractBaseModel.Meta, PhoneNumberMixin.Meta):
        # unique_together = (("user", "phone_type"),)
        pass

    @classmethod
    def ensure_single_primary(cls, user):
        ensure_single_primary(user.userphonenumber_set.all())


class OneTimeMessage(AbstractBaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(_("title"), max_length=255, default='')
    message = models.TextField(_("message"), blank=True, max_length=2048, default='')

    class Meta(AbstractBaseModel.Meta):
        verbose_name = _('one time message')
        verbose_name_plural = _('one time messages')


class OrganisationChangeManager(AbstractBaseModelManager):
    def open(self):
        return self.get(status='o')


class OpenOrganisationChangeManager(AbstractBaseModelManager):
    def get_queryset(self):
        return super().get_queryset().filter(status='o').prefetch_related(
            'user__useremail_set', 'organisation__organisation_country__country')


class OrganisationChange(AbstractBaseModel):
    """
    a request from an user to change the organisation
    """
    STATUS_CHOICES = [
        ('o', _('open')),  # opened by user
        ('c', _('canceled')),  # by user
        ('v', _('approved')),
        ('d', _('denied'))
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    original_organisation = models.ForeignKey(Organisation, related_name='original_organisation', null=True,
                                              blank=True, on_delete=models.CASCADE)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    message = models.TextField(_("message"), max_length=2048,
                               help_text=_('Message for the organisation administrator.'),
                               blank=True)
    comment = models.TextField(_("Comment"), max_length=2048, blank=True)
    status = models.CharField(_('status'), max_length=255, choices=STATUS_CHOICES, default='o')
    last_modified_by_user = CurrentUserField(verbose_name=_('last modified by'),
                                             related_name='organisationchange_last_modified_by',
                                             on_delete=models.SET_NULL)
    completed_by_user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True,
                                          verbose_name=_('completed by'),
                                          related_name='organisationchange_completed_by', on_delete=models.SET_NULL)

    objects = OrganisationChangeManager()
    open = OpenOrganisationChangeManager()

    def cancel(self, user):
        self.status = 'c'
        self.completed_by_user = user
        self.save()

    def verify(self, user):
        self.user.organisations.set([self.organisation])
        self.status = 'v'
        self.completed_by_user = user

        # check if organisation uses user activation
        if self.organisation.uses_user_activation:
            if self.user.valid_until is None:
                self.user.valid_until = now() + datetime.timedelta(days=settings.SSO_VALIDATION_PERIOD_DAYS)
                self.user.save()
        else:
            self.user.valid_until = None
            self.user.save()

        # remove organisation related permissions
        organisation_related_application_roles = ApplicationRole.objects.filter(is_organisation_related=True)
        organisation_related_role_profiles = RoleProfile.objects.filter(is_organisation_related=True)
        self.user.application_roles.remove(*list(organisation_related_application_roles))
        self.user.role_profiles.remove(*list(organisation_related_role_profiles))
        self.save()

    def deny(self, user):
        self.status = 'd'
        self.completed_by_user = user
        self.save()

    @property
    def is_open(self):
        return self.status == 'o'

    class Meta(AbstractBaseModel.Meta):
        verbose_name = _('organisation change')
        verbose_name_plural = _('organisation change')

    def get_absolute_url(self):
        return reverse('accounts:organisationchange_detail', kwargs={'pk': self.pk})
