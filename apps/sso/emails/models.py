# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from sso.models import AbstractBaseModel

import logging
logger = logging.getLogger(__name__)

PERSON_EMAIL_TYPE = 'person'
GROUP_EMAIL_TYPE = 'group'
CENTER_EMAIL_TYPE = 'center'
REGION_EMAIL_TYPE = 'region'
COUNTRY_EMAIL_TYPE = 'country'
COUNTRY_GROUP_EMAIL_TYPE = 'global_region'
CLOSED_GROUP_EMAIL_TYPE = 'closed_group'

PERM_EVERYBODY = '1'
PERM_DWB = '2'
PERM_VIP = '3'
PERM_VIP_DWB = '4'

class Email(AbstractBaseModel):
    EMAIL_TYPE_CHOICES = (
        (CENTER_EMAIL_TYPE, _('Center')),
        (REGION_EMAIL_TYPE, _('Region')),
        (COUNTRY_EMAIL_TYPE, _('Country')),
        (COUNTRY_GROUP_EMAIL_TYPE, _('Country group')),
        (PERSON_EMAIL_TYPE, _('Person')),
        (GROUP_EMAIL_TYPE, _('Group')),
        # (CLOSED_GROUP_EMAIL_TYPE, _('Closed Group')),
    )
    PERMISSION_CHOICES = (
        (PERM_EVERYBODY, _('Everybody')),
        (PERM_DWB, _('Diamondway Buddhism')),
        (PERM_VIP, _('VIP')),
        (PERM_VIP_DWB, _('VIP + Diamondway Buddhism')),
    )
    # name = models.CharField(_("name"), max_length=255, blank=True)    
    email_type = models.CharField(_('email type'), max_length=20, choices=EMAIL_TYPE_CHOICES, db_index=True)
    permission = models.CharField(_('access control'), max_length=20, choices=PERMISSION_CHOICES, db_index=True, default=PERM_EVERYBODY)
    email = models.EmailField(_('email address'), unique=True, max_length=254)
    is_active = models.BooleanField(_('active'), default=True, help_text=_('Designates whether this email should be treated as '
                                                                           'active. Unselect this instead of deleting the email.'))
    
    def primary_forward(self):
        return self.emailforward_set.filter(primary=True).first()
    
    @models.permalink
    def get_absolute_url(self):
        # return  ('emails:email_update', (), {'uuid': self.uuid, })
        return 'emails:email_list', (), {}

    class Meta(AbstractBaseModel.Meta):
        permissions = (
            ("read_email", "Can read mail data"),
        )
        ordering = ['email']
        verbose_name = _('Email')
        verbose_name_plural = _('Emails')

    def __unicode__(self):
        return u"%s" % self.email


class EmailForward(AbstractBaseModel):
    email = models.ForeignKey(Email, verbose_name=_('email address'))
    forward = models.EmailField(_('email forwarding address'), max_length=254)
    primary = models.BooleanField(_("primary"), help_text=_('Designates the email address, which can only changed by users with special administration rights.'), default=False)
    
    class Meta(AbstractBaseModel.Meta):
        unique_together = (("email", "forward"),)
        ordering = ['forward', 'email']
        verbose_name = _('email forwarding')
        verbose_name_plural = _('email forwardings')

    def __unicode__(self):
        return u"%s" % self.forward


class EmailAlias(AbstractBaseModel):
    email = models.ForeignKey(Email, verbose_name=_('email address'))
    alias = models.EmailField(_('email alias address'), unique=True, max_length=254)
    
    class Meta(AbstractBaseModel.Meta):
        unique_together = (("email", "alias"),)
        ordering = ['alias', 'email']
        verbose_name = _('email alias')
        verbose_name_plural = _('email aliases')

    def __unicode__(self):
        return u"%s" % self.alias


class GroupEmail(AbstractBaseModel):
    name = models.CharField(_("name"), blank=True, default='', max_length=255)
    email = models.ForeignKey(Email, verbose_name=_("email address"), unique=True, limit_choices_to={'email_type': GROUP_EMAIL_TYPE})
    homepage = models.URLField(_("homepage"), blank=True, default='')
    is_guide_email = models.BooleanField(_('guide email'), default=False)
    is_active = models.BooleanField(_('active'), default=True, help_text=_('Designates whether this email should be treated as '
                                                                           'active. Unselect this instead of deleting the email.'))
    
    class Meta(AbstractBaseModel.Meta):
        verbose_name = _('group email')
        verbose_name_plural = _('group emails')

    @models.permalink
    def get_absolute_url(self):
        return 'emails:groupemail_detail', (), {'uuid': self.uuid, }

    def __unicode__(self):
        return u"%s" % self.email


class GroupEmailManager(models.Model):
    group_email = models.ForeignKey(GroupEmail, verbose_name=_("group email"))
    manager = models.ForeignKey(settings.AUTH_USER_MODEL)

    class Meta:
        unique_together = (("group_email", "manager"),)
        verbose_name = _('group email manager')
        verbose_name_plural = _('group email managers')
