import datetime
import logging

from django.conf import settings
from django.template import loader
from django.contrib.auth.tokens import default_token_generator as default_pwd_reset_token_generator
from django.contrib.sites.models import get_current_site
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.timezone import now
from django.utils.translation import get_language, activate
from sso.accounts.tokens import email_confirm_token_generator


logger = logging.getLogger(__name__)


def i18n_email_msg_and_subj(context, email_template_name, subject_template_name, language=None):
    def msg_and_subject():
        subject = loader.render_to_string(subject_template_name, context)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        msg = loader.render_to_string(email_template_name, context)
        return msg, subject

    if language:
        cur_language = get_language()
        try:
            activate(language)
            return msg_and_subject()
        finally:
            activate(cur_language)
    else:
        return msg_and_subject()


def send_account_created_email(user, request, token_generator=default_pwd_reset_token_generator,
                               from_email=None,
                               email_template_name='accounts/account_created_email.txt',
                               subject_template_name='accounts/account_created_email_subject.txt'
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

    message, subject = i18n_email_msg_and_subj(c, email_template_name, subject_template_name, user.language)
    send_mail(subject, message, from_email, [user_email.email], fail_silently=settings.DEBUG)
