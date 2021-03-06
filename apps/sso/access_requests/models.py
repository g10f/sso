from datetime import timedelta

from current_user.models import CurrentUserField
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from sso.accounts.models import Application
from sso.models import AbstractBaseModel, AbstractBaseModelManager
from sso.organisations.models import is_validation_period_active, Organisation


class AccessRequestManager(AbstractBaseModelManager):
    def open(self):
        return self.get(status='o')


class OpenAccessRequestManager(AbstractBaseModelManager):
    def get_queryset(self):
        return super().get_queryset().filter(status='o').prefetch_related('user__useremail_set')

    @classmethod
    def expiration_date(cls):
        return timezone.now() - timedelta(days=getattr(settings, 'ACCESS_REQUEST_EXPIRATION_DAYS', 180))

    def expired_q(self):
        q = Q(last_modified__lte=self.expiration_date())
        return q

    def get_expired(self):
        return super().filter(self.expired_q()).order_by('last_modified')

    def get_not_expired(self):
        return super().exclude(self.expired_q())


class AccessRequest(AbstractBaseModel):
    STATUS_CHOICES = [
        ('o', _('open')),  # opened by user
        ('c', _('canceled')),  # by user
        ('v', _('approved')),
        ('d', _('denied'))
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField(_("message"), max_length=2048,
                               help_text=_('Message for the administrators.'),
                               blank=True)
    comment = models.TextField(_("Comment"), max_length=2048, blank=True)
    status = models.CharField(_('status'), max_length=255, choices=STATUS_CHOICES, default='o')
    last_modified_by_user = CurrentUserField(verbose_name=_('last modified by'),
                                             related_name='accessrequest_last_modified_by',
                                             on_delete=models.SET_NULL)
    completed_by_user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True,
                                          verbose_name=_('completed by'),
                                          related_name='accessrequest_completed_by', on_delete=models.SET_NULL)
    application = models.ForeignKey(Application, blank=True, null=True, on_delete=models.SET_NULL,
                                    verbose_name=_('application'))
    # required field if the user has no organisation
    organisation = models.ForeignKey(Organisation, blank=True, null=True, on_delete=models.CASCADE)

    objects = AccessRequestManager()
    open = OpenAccessRequestManager()

    def process(self, action=None, user=None):
        if action in ['cancel', 'verify', 'deny']:
            getattr(self, action)(user)
        else:
            raise ValueError

    def cancel(self, user):
        self.status = 'c'
        self.completed_by_user = user
        self.save()

    def verify(self, user):
        self.status = 'v'
        self.completed_by_user = user
        if self.organisation:
            self.user.set_organisations([self.organisation])

        # check if organisation uses user activation
        validation_period_active = False
        for organisation in self.user.organisations.all():
            if is_validation_period_active(organisation):
                self.user.valid_until = now() + timedelta(days=settings.SSO_VALIDATION_PERIOD_DAYS)
                self.user.save()
                validation_period_active = True
        if not validation_period_active:
            self.user.valid_until = None
            self.user.save()

        # add default member profile
        self.user.role_profiles.add(user.get_default_role_profile())
        self.user.role_profiles.remove(user.get_default_guest_profile())
        self.save()

    def deny(self, user):
        self.status = 'd'
        self.completed_by_user = user
        self.save()

    @property
    def is_open(self):
        return self.status == 'o'

    class Meta(AbstractBaseModel.Meta):
        verbose_name = _('access request')
        verbose_name_plural = _('access request')

    def get_absolute_url(self):
        return reverse('accounts:accessrequest_detail', kwargs={'pk': self.pk})
