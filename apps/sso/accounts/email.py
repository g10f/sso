import datetime
import logging

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator as default_pwd_reset_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.timezone import now
from sso.accounts.tokens import email_confirm_token_generator
from sso.utils.email import send_mail
from sso.utils.translation import i18n_email_msg_and_subj

logger = logging.getLogger(__name__)


def send_account_created_email(user, request, token_generator=default_pwd_reset_token_generator,
                               email_template_name='accounts/email/account_created_email.txt',
                               subject_template_name='accounts/email/account_created_email_subject.txt',
                               apply_async=None,
                               countdown=0
                               ):
    use_https = request.is_secure()
    current_site = get_current_site(request)
    site_name = settings.SSO_SITE_NAME
    domain = current_site.domain
    user_primary_email = request.user.primary_email()
    reply_to = [user_primary_email.email] if user_primary_email else None
    expiration_date = now() + datetime.timedelta(settings.PASSWORD_RESET_TIMEOUT_DAYS)
    email = user.primary_email()
    c = {
        'email': email,
        'first_name': user.first_name,
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

    user.email_user(subject, message, reply_to=reply_to, fail_silently=settings.DEBUG, apply_async=apply_async,
                    countdown=countdown)


def send_useremail_confirmation(user_email, request, token_generator=email_confirm_token_generator,
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
        'first_name': user.first_name,
        'username': user.username,
        'domain': domain,
        'site_name': site_name,
        'uid': urlsafe_base64_encode(force_bytes(user_email.pk)),
        'token': token_generator.make_token(user_email),
        'protocol': use_https and 'https' or 'http',
        'expiration_date': expiration_date
    }
    # use the user language or the current language from the browser
    message, subject = i18n_email_msg_and_subj(c, email_template_name, subject_template_name, user.language)
    send_mail(subject, message, recipient_list=[user_email.email], fail_silently=settings.DEBUG)


def send_mail_managers(subject, message, fail_silently=False, html_message=None, reply_to=None):
    """Sends a message to the managers, as defined by the MANAGERS setting."""
    if not settings.MANAGERS:
        return
    recipient_list = [a[1] for a in settings.MANAGERS]
    subject = '%s%s' % (settings.EMAIL_SUBJECT_PREFIX, subject)

    send_mail(subject, message, recipient_list=recipient_list, fail_silently=fail_silently, html_message=html_message,
              reply_to=reply_to)
