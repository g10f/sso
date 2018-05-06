"""
from current_user.models import CurrentUserField
from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from sso.models import AbstractBaseModel


class OrganisationChange(AbstractBaseModel):
    STATUS_CHOICES = [
        ('o', _('open')),  # opened by user
        ('c', _('canceled')),  # by user
        ('v', _('approved')),
        ('d', _('denied'))
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
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
"""
