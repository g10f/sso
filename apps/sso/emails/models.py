# -*- coding: utf-8 -*-
from django.db import models
from django.utils.translation import ugettext_lazy as _

from sso.models import AbstractBaseModel

import logging
logger = logging.getLogger(__name__)

CENTER_EMAIL_TYPE = '1'

class Email(AbstractBaseModel):
    EMAIL_TYPE_CHOICES = (
        ('1', _('Center')),
        ('2', _('Type 2')),
        ('3', _('Type 3')),
        ('4', _('Type 4')),
    )
    name = models.CharField(_("name"), max_length=255, blank=True)    
    email_type = models.CharField(_('email type'), max_length=2, choices=EMAIL_TYPE_CHOICES, db_index=True)
    email = models.EmailField(_('email address'), unique=True)
    
    class Meta(AbstractBaseModel.Meta):
        ordering = ['email']
        verbose_name = _('email')
        verbose_name_plural = _('emails')

    def __unicode__(self):
        return u"%s" % self.email

class EmailForward(AbstractBaseModel):
    email = models.ForeignKey(Email, verbose_name=_('email address'))
    forward = models.EmailField(_('email forward address'))
    
    class Meta(AbstractBaseModel.Meta):
        unique_together = (("email", "forward"),)
        ordering = ['forward', 'email']
        verbose_name = _('e-mail forward')
        verbose_name_plural = _('e-mail forwards')


class EmailAlias(AbstractBaseModel):
    email = models.ForeignKey(Email, verbose_name=_('email address'))
    alias = models.EmailField(_('email alias address'), unique=True)
    
    class Meta(AbstractBaseModel.Meta):
        unique_together = (("email", "alias"),)
        ordering = ['alias', 'email']
        verbose_name = _('e-mail alias')
        verbose_name_plural = _('e-mail aliases')
