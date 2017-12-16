# -*- coding: utf-8 -*-
import logging

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
from sso.models import AbstractBaseModel, AddressMixin, PhoneNumberMixin, ensure_single_primary, \
    CaseInsensitiveEmailField
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


class OrganisationChange(AbstractBaseModel):
    """
    a request from an user to change the organisation
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    reason = models.TextField(_("reason"), max_length=2048)
    comment = models.TextField(_("Comment"), max_length=2048, blank=True)

    class Meta(AbstractBaseModel.Meta):
        verbose_name = _('organisation change')
        verbose_name_plural = _('organisation change')

    def get_absolute_url(self):
        return reverse('accounts:organisationchange_detail', kwargs={'pk': self.pk})
