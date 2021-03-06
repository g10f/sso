import datetime

from current_user.models import CurrentUserField
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator as default_pwd_reset_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from sso.utils.translation import i18n_email_msg_and_subj
from .tokens import default_token_generator
from ..accounts.models import UserNote
from ..utils.email import get_email_message


def send_access_denied_email(user, request, reply_to_email,
                             email_template_name='registration/email/access_denied_email.txt',
                             subject_template_name='registration/email/access_denied_subject.txt'
                             ):
    from_email = settings.REGISTRATION.get('CONTACT_EMAIL', None)
    message, subject = get_access_denied_email_message(user, request, reply_to_email, email_template_name,
                                                       subject_template_name)
    user.email_user(subject, message, from_email)


def get_access_denied_email_message(user, request, reply_to_email,
                                    email_template_name='registration/email/access_denied_email.txt',
                                    subject_template_name='registration/email/access_denied_subject.txt'
                                    ):
    return get_email_message(user, request, reply_to_email, email_template_name, subject_template_name)


def send_check_back_email(user, request, reply_to_email,
                          email_template_name='registration/email/check_back_email.txt',
                          subject_template_name='registration/email/check_back_subject.txt'
                          ):
    from_email = settings.REGISTRATION.get('CONTACT_EMAIL', None)
    message, subject = get_check_back_email_message(user, request, reply_to_email, email_template_name,
                                                    subject_template_name)
    user.email_user(subject, message, from_email)


def get_check_back_email_message(user, request, reply_to_email,
                                 email_template_name='registration/email/check_back_email.txt',
                                 subject_template_name='registration/email/check_back_subject.txt'
                                 ):
    return get_email_message(user, request, reply_to_email, email_template_name, subject_template_name)


def get_set_password_email_message(user, request, token_generator=default_pwd_reset_token_generator,
                                   email_template_name='registration/email/set_password_email.txt',
                                   subject_template_name='registration/email/set_password_subject.txt'
                                   ):
    use_https = request.is_secure()
    current_site = get_current_site(request)
    site_name = settings.SSO_SITE_NAME
    domain = current_site.domain
    expiration_date = now() + datetime.timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT)

    c = {
        'email': user.primary_email(),
        'username': user.username,
        'domain': domain,
        'site_name': site_name,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': token_generator.make_token(user),
        'protocol': use_https and 'https' or 'http',
        'expiration_date': expiration_date
    }
    # use the user language or the default language (en-us)
    language = user.language if user.language else settings.LANGUAGE_CODE
    return i18n_email_msg_and_subj(c, email_template_name, subject_template_name, language)


def send_set_password_email(user, request, token_generator=default_pwd_reset_token_generator,
                            from_email=None,
                            email_template_name='registration/email/set_password_email.txt',
                            subject_template_name='registration/email/set_password_subject.txt',
                            **kwargs):
    message, subject = get_set_password_email_message(user, request, token_generator, email_template_name,
                                                      subject_template_name)
    user.email_user(subject, message, from_email, **kwargs)


def send_validation_email(registration_profile, request, token_generator=default_token_generator,
                          email_template_name='registration/email/validation_email.txt',
                          subject_template_name='registration/email/validation_email_subject.txt'
                          ):
    use_https = request.is_secure()
    current_site = get_current_site(request)
    site_name = settings.SSO_SITE_NAME
    domain = current_site.domain
    expiration_date = now() + datetime.timedelta(settings.REGISTRATION.get('TOKEN_EXPIRATION_DAYS', 7))

    c = {
        'domain': domain,
        'site_name': site_name,
        'protocol': use_https and 'https' or 'http',
        'token': token_generator.make_token(registration_profile),
        'uid': urlsafe_base64_encode(force_bytes(registration_profile.pk)),
        'expiration_date': expiration_date
    }
    # use the user language or the current language from the browser
    language = registration_profile.user.language
    message, subject = i18n_email_msg_and_subj(c, email_template_name, subject_template_name, language)
    registration_profile.user.email_user(subject, message, None)


class RegistrationManager(models.Manager):
    @classmethod
    def token_expiration_date(cls):
        return timezone.now() - datetime.timedelta(days=settings.REGISTRATION.get('TOKEN_EXPIRATION_DAYS', 7))

    @classmethod
    def activation_expiration_date(cls):
        # The activation of a new user should take no longer then 2 month
        return timezone.now() - datetime.timedelta(days=settings.REGISTRATION.get('ACTIVATION_EXPIRATION_DAYS', 60))

    @classmethod
    def expired_q(cls):
        """
        Users who don't complete the email validation in TOKEN_EXPIRATION_DAYS or did not activated by
        an admin in ACTIVATION_EXPIRATION_DAYS will be deleted.
        """
        # Users who didn't validate there email in the token_expiration_date
        q = Q(user__is_active=False) & Q(is_validated=False) & Q(date_registered__lte=cls.token_expiration_date()) & Q(user__last_login__isnull=True)
        # Users who where not activated in activation_expiration_date
        q = q | (Q(user__is_active=False) & Q(date_registered__lte=cls.activation_expiration_date())) & Q(user__last_login__isnull=True)
        return q

    def get_expired(self):
        return super().filter(self.expired_q())

    def get_not_expired(self):
        return super().exclude(self.expired_q())

    @classmethod
    def filter_administrable_registrationprofiles(cls, user, qs):
        if user.is_superuser:
            pass  # return unchanged qs
        elif user.has_perm("accounts.access_all_users"):
            qs = qs.filter(user__is_superuser=False)
        else:
            organisations = user.get_administrable_user_organisations()
            q = Q(user__is_superuser=False) & Q(user__organisations__in=organisations)
            qs = qs.filter(q).distinct()
        return qs

    @classmethod
    def delete_expired_users(cls):
        num_deleted = 0
        for profile in RegistrationProfile.objects.get_expired().filter(user__is_stored_permanently=False):
            profile.user.delete()
            num_deleted += 1
        return num_deleted


class RegistrationProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_('user'))
    last_modified = models.DateTimeField(_('last modified'), auto_now=True)
    last_modified_by_user = CurrentUserField(verbose_name=_('last modified by'),
                                             related_name='registrationprofile_last_modified_by',
                                             on_delete=models.SET_NULL)
    date_registered = models.DateTimeField(_('date registered'), default=timezone.now)
    is_validated = models.BooleanField(_('validated'), default=False, db_index=True, help_text=_(
        'Designates whether this profile was already validated by the user.'))
    about_me = models.TextField(_('about_me'), blank=True, max_length=1024)
    known_person1_first_name = models.CharField(_("first name of a known person"), max_length=100, blank=True)
    known_person1_last_name = models.CharField(_("last name of a known person"), max_length=100, blank=True)
    known_person2_first_name = models.CharField(_("first name of a another known person"), max_length=100, blank=True)
    known_person2_last_name = models.CharField(_("last name of a another known person"), max_length=100, blank=True)
    check_back = models.BooleanField(_('check back'), default=False,
                                     help_text=_('Designates if there are open questions to check.'))
    is_access_denied = models.BooleanField(_('access denied'), default=False, db_index=True,
                                           help_text=_('Designates if access is denied to the user.'))
    comment = models.TextField(_("Comment"), max_length=2048, blank=True)

    objects = RegistrationManager()

    class Meta:
        verbose_name = _('registration profile')
        verbose_name_plural = _('registration profiles')

    def __str__(self):
        return '%s' % self.user

    def token_valid(self):
        token_expiration_date = RegistrationManager.token_expiration_date()
        return bool(self.date_registered > token_expiration_date)

    token_valid.boolean = True

    def activation_valid(self):
        activation_expiration_date = RegistrationManager.activation_expiration_date()
        return self.user.is_active or (self.date_registered > activation_expiration_date)

    activation_valid.boolean = True

    def process(self, action=None, user=None):
        notes = []
        if action == 'activate':
            self.user.is_active = True
            self.is_access_denied = False
            self.check_back = False
            if not self.user.has_usable_password():
                self.user.set_password(get_random_string(40))
            self.save()
            self.user.save()
            notes.append('activated')
        elif action == 'deny':
            self.is_access_denied = True
            self.user.is_active = False
            self.save()
            self.user.save()
            notes.append('denied')
        elif action == 'check_back':
            self.check_back = True
            self.save()
            notes.append('check back required')

        UserNote.objects.create_note(user=self.user, created_by_user=user, notes=notes)
