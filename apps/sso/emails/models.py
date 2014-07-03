# -*- coding: utf-8 -*-
from django.db import models
from django.utils.translation import ugettext_lazy as _

from sso.models import AbstractBaseModel

import logging
logger = logging.getLogger(__name__)


class Email(AbstractBaseModel):
    EMAIL_TYPE_CHOICES = (
        ('1', _('Type 1')),
        ('2', _('Type 2')),
        ('3', _('Type 3')),
        ('4', _('Type 4')),
    )
    name = models.CharField(_("name"), max_length=255)    
    email_type = models.CharField(_('email type'), max_length=2, choices=EMAIL_TYPE_CHOICES, db_index=True)
    email = models.EmailField(_('email address'), unique=True)
    
    class Meta(AbstractBaseModel.Meta):
        ordering = ['email']
        verbose_name = _('e-mail')
        verbose_name_plural = _('e-mails')

    def __unicode__(self):
        return u"%s" % self.email

class EmailForward(AbstractBaseModel):
    email_list = models.ForeignKey(Email, verbose_name=_('e-mail list'))
    email = models.EmailField(_('email address'))
    
    class Meta(AbstractBaseModel.Meta):
        unique_together = (("email", "email_list"),)
        ordering = ['email', 'email_list']
        verbose_name = _('e-mail forward')
        verbose_name_plural = _('e-mail forwards')


class EmailAlias(AbstractBaseModel):
    email_list = models.ForeignKey(Email, verbose_name=_('e-mail list'))
    email = models.EmailField(_('email address'), unique=True)
    
    class Meta(AbstractBaseModel.Meta):
        unique_together = (("email", "email_list"),)
        ordering = ['email', 'email_list']
        verbose_name = _('e-mail alias')
        verbose_name_plural = _('e-mail aliases')
