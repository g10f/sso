import datetime 
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.contrib.sites.models import get_current_site
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.core.mail import send_mail
from django.template import loader
from django.core import urlresolvers
from django.contrib.auth.tokens import default_token_generator as default_pwd_reset_token_generator
from l10n.models import Country
from tokens import default_token_generator
from current_user.models import CurrentUserField


def send_user_validated_email(registration_profile, request):
    email_recipient_list = settings.REGISTRATION.get('EMAIL_RECIPIENT_LIST', None)
    if email_recipient_list:
        protocol = 'https' if request.is_secure() else 'http'
        current_site = get_current_site(request)
        domain = current_site.domain
        
        subject = u"Validation for %s completed" % registration_profile.user
        admin_url = urlresolvers.reverse("registration:update_user_registration", args=(registration_profile.pk,))
        email = subject + u"\n %s://%s%s" % (protocol, domain, admin_url)
        send_mail(subject, email, None, email_recipient_list)
        
        
def send_set_password_email(user, request, token_generator=default_pwd_reset_token_generator,
                              from_email=None,
                              email_template_name='registration/set_password_email.txt',
                              subject_template_name='registration/set_password_subject.txt'
                              ):
    use_https = request.is_secure()
    current_site = get_current_site(request)
    site_name = current_site.name
    domain = current_site.domain
    c = {
        'email': user.email,
        'username': user.username,
        'domain': domain,
        'site_name': site_name,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': token_generator.make_token(user),
        'protocol': use_https and 'https' or 'http',
    }
    subject = loader.render_to_string(subject_template_name, c)
    # Email subject *must not* contain newlines
    subject = ''.join(subject.splitlines())
    email = loader.render_to_string(email_template_name, c)
    send_mail(subject, email, from_email, [user.email])


def send_validation_email(registration_profile, request, token_generator=default_token_generator):
    use_https = request.is_secure()
    current_site = get_current_site(request)
    site_name = current_site.name
    domain = current_site.domain
    c = {
        'domain': domain,
        'site_name': site_name,
        'protocol': use_https and 'https' or 'http',
        'token': token_generator.make_token(registration_profile),
        'uid': urlsafe_base64_encode(force_bytes(registration_profile.pk)),
        'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS
    }
    subject = render_to_string('registration/validation_email_subject.txt', c)
    # Email subject *must not* contain newlines
    subject = ''.join(subject.splitlines())
    message = render_to_string('registration/validation_email.txt', c)
    send_mail(subject, message, None, [registration_profile.user.email])


class RegistrationManager(models.Manager):
   
    @classmethod
    def expiration_date(cls):
        return timezone.now() - datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS)
    
    @classmethod
    def get_expired_users(cls):
        expiration_date = cls.expiration_date()
        return get_user_model().objects.filter(is_active=False,
                                   registrationprofile__is_validated=False, 
                                   registrationprofile__date_registered__lte=expiration_date)
    
    @classmethod
    def delete_expired_users(cls):
        expired_users = cls.get_expired_users()
        return expired_users.delete()


class RegistrationProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, unique=True, verbose_name=_('user'))
    last_modified = models.DateTimeField(_('last modified'), auto_now=True)
    last_modified_by_user = CurrentUserField(verbose_name=_('last modified by'), related_name='registrationprofile_last_modified_by')
    verified_by_user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, verbose_name=_('verified by'), related_name='registrationprofile_verified_by')
    date_registered = models.DateTimeField(_('date registered'), default=timezone.now)
    is_validated = models.BooleanField(_('validated'), default=False, help_text=_('Designates whether this profile was already validated by the user.'))
    purpose = models.TextField(_('purpose'), max_length=255)
    street = models.CharField(_('street'), blank=True, max_length=255)
    notes = models.TextField(_("Notes"), blank=True, max_length=255)
    city = models.CharField(_("city"), max_length=100, blank=True)
    postal_code = models.CharField(_("zip code"), max_length=30, blank=True)
    country = models.ForeignKey(Country, verbose_name=_("country"), default=81, blank=True, null=True)
    phone = models.CharField(_("phone Number"), max_length=30)
    known_person1 = models.CharField(_("person who can recommend you"), max_length=100, blank=True)
    known_person2 = models.CharField(_("another person who can recommend you"), max_length=100, blank=True)
    
    objects = RegistrationManager()
    
    class Meta:
        permissions = (
            ("verify_users", "Can verify users"),
        )
        verbose_name = _('registration profile')
        verbose_name_plural = _('registration profiles')
    
    def __unicode__(self):
        return u"%s" % (self.user)
    
    def expired(self):
        expiration_date = RegistrationManager.expiration_date()
        return bool(self.date_registered < expiration_date)
    expired.boolean = True
