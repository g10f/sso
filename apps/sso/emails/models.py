# -*- coding: utf-8 -*-
from django.db import models
from django.utils.translation import ugettext_lazy as _

from sso.models import AbstractBaseModel

import logging
logger = logging.getLogger(__name__)

PERSON_EMAIL_TYPE = 'person'
GROUP_EMAIL_TYPE = 'group'
CENTER_EMAIL_TYPE = 'center'
REGION_EMAIL_TYPE = 'region'
COUNTRY_EMAIL_TYPE = 'country'
GLOBAL_REGION_EMAIL_TYPE = 'global_region'
CLOSED_GROUP_EMAIL_TYPE = 'closed_group'

class Email(AbstractBaseModel):
    EMAIL_TYPE_CHOICES = (
        (PERSON_EMAIL_TYPE, _('Person')),
        (GROUP_EMAIL_TYPE, _('Group')),
        (CENTER_EMAIL_TYPE, _('Center')),
        (REGION_EMAIL_TYPE, _('Region')),
        (COUNTRY_EMAIL_TYPE, _('Country')),
        (GLOBAL_REGION_EMAIL_TYPE, _('Global region')),
        (CLOSED_GROUP_EMAIL_TYPE, _('Closed group')),
    )
    ACCESS_CONTROL_CHOICES = (
        ('1', _('Everybody')),
        ('2', _('Centers')),
        ('3', _('Specials')),
        ('4', _('VIP')),
    )
    name = models.CharField(_("name"), max_length=255, blank=True)    
    email_type = models.CharField(_('email type'), max_length=20, choices=EMAIL_TYPE_CHOICES, db_index=True)
    access_control = models.CharField(_('access control'), max_length=20, choices=ACCESS_CONTROL_CHOICES, db_index=True)
    email = models.EmailField(_('email address'), unique=True, max_length=254)
    
    def primary_forward(self):
        return self.emailforward_set.filter(primary=True).first()
    
    class Meta(AbstractBaseModel.Meta):
        ordering = ['email']
        verbose_name = _('Email')
        verbose_name_plural = _('Emails')

    def __unicode__(self):
        return u"%s" % self.email


class EmailForward(AbstractBaseModel):
    email = models.ForeignKey(Email, verbose_name=_('email address'))
    forward = models.EmailField(_('email forward address'), max_length=254)
    primary = models.BooleanField(_("primary"), default=False)
    
    class Meta(AbstractBaseModel.Meta):
        unique_together = (("email", "forward"),)
        ordering = ['forward', 'email']
        verbose_name = _('e-mail forward')
        verbose_name_plural = _('e-mail forwards')

    def __unicode__(self):
        return u"%s" % self.forward


class EmailAlias(AbstractBaseModel):
    email = models.ForeignKey(Email, verbose_name=_('email address'))
    alias = models.EmailField(_('email alias address'), unique=True, max_length=254)
    
    class Meta(AbstractBaseModel.Meta):
        unique_together = (("email", "alias"),)
        ordering = ['alias', 'email']
        verbose_name = _('e-mail alias')
        verbose_name_plural = _('e-mail aliases')

    def __unicode__(self):
        return u"%s" % self.alias
