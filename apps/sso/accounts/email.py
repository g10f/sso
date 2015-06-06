import datetime
import logging

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator as default_pwd_reset_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.timezone import now
from sso.accounts.tokens import email_confirm_token_generator
from sso.utils.translation import i18n_email_msg_and_subj


logger = logging.getLogger(__name__)


def send_account_created_email(user, request, token_generator=default_pwd_reset_token_generator,
                               from_email=None,
                               email_template_name='accounts/email/account_created_email.txt',
                               subject_template_name='accounts/email/account_created_email_subject.txt'
                               ):

    use_https = request.is_secure()
    current_site = get_current_site(request)
    site_name = settings.SSO_SITE_NAME
    domain = current_site.domain
    expiration_date = now() + datetime.timedelta(settings.PASSWORD_RESET_TIMEOUT_DAYS)
    email = user.primary_email()
    c = {
        'email': email,
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
    message, subject = i18n_email_msg_and_subj(c, email_template_name, subject_template_name, language)

    user.email_user(subject, message, from_email=from_email, fail_silently=settings.DEBUG)


def send_useremail_confirmation(user_email, request, token_generator=email_confirm_token_generator,
                                from_email=None,
                                email_template_name='accounts/email/useremail_confirm_email.txt',
                                subject_template_name='accounts/email/useremail_confirm_email_subject.txt'
                                ):

    use_https = request.is_secure()
    current_site = get_current_site(request)
    site_name = settings.SSO_SITE_NAME
    domain = current_site.domain
    expiration_date = now() + datetime.timedelta(minutes=settings.SSO_EMAIL_CONFIRM_TIMEOUT_MINUTES)
    user = user_email.user
    c = {
        'user_email': user_email.email,
        'username': user.username,
        'domain': domain,
        'site_name': site_name,
        'uid': urlsafe_base64_encode(force_bytes(user_email.pk)),
        'token': email_confirm_token_generator.make_token(user_email),
        'protocol': use_https and 'https' or 'http',
        'expiration_date': expiration_date
    }
    # use the user language or the current language from the browser
    message, subject = i18n_email_msg_and_subj(c, email_template_name, subject_template_name, user.language)
    send_mail(subject, message, from_email, [user_email.email], fail_silently=settings.DEBUG)


def send_account_expires_info(user, base_url, from_email=None,
                              email_template_name='accounts/email/account_expires_info_email.txt',
                              subject_template_name='accounts/email/account_expires_info_email_subject.txt'
                              ):
    """
    send expiration warning from cron job.
    """
    site_name = settings.SSO_SITE_NAME
    expiration_date = user.valid_until
    email = user.primary_email()
    c = {
        'email': email,
        'username': user.username,
        'site_name': site_name,
        'base_url': base_url,
        'expiration_date': expiration_date,
        'has_expired': expiration_date < now()
    }
    # use the user language or the default language (en-us)
    language = user.language if user.language else settings.LANGUAGE_CODE
    message, subject = i18n_email_msg_and_subj(c, email_template_name, subject_template_name, language)

    user.email_user(subject, message, from_email=from_email, fail_silently=settings.DEBUG)
