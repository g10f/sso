from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import get_connection
from django.core.mail.message import EmailMessage, EmailMultiAlternatives
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from sso.celery import send_mail_task
from sso.utils.translation import i18n_email_msg_and_subj


def send_mail(subject, message, recipient_list, from_email=None, html_message=None, fail_silently=False,
              apply_async=None, countdown=0, bcc=None, **kwargs):
    if apply_async is None:
        apply_async = settings.SSO_ASYNC_EMAILS
    kwargs.update({'subject': subject, 'message': message, 'from_email': from_email, 'recipient_list': recipient_list,
                   'html_message': html_message, 'fail_silently': fail_silently, 'bcc': bcc})
    if apply_async:
        return send_mail_task.apply_async(countdown=countdown, kwargs=kwargs)
    else:
        return send_mail_task(**kwargs)


def send_html_mail(subject, message, recipient_list, from_email, html_message, fail_silently=False, reply_to=None,
                   bcc=None):
    msg_alternative = MIMEMultipart('alternative')
    msg_html = MIMEText(html_message, _subtype='html', _charset='utf-8')
    msg_text = MIMEText(message, _charset='utf-8')
    msg_alternative.attach(msg_text)
    msg_alternative.attach(msg_html)

    msg = EmailMessage(subject, '', from_email, recipient_list, reply_to=reply_to, bcc=bcc)
    msg.mixed_subtype = 'related'
    msg.attach(msg_alternative)

    if settings.SSO_EMAIL_LOGO:
        with open(settings.SSO_EMAIL_LOGO, 'rb') as f:
            email_image = MIMEImage(f.read())
            email_image.add_header('Content-ID', '<{}>'.format("logo"))
            email_image.add_header("Content-Disposition", "inline", filename="logo")
            msg.attach(email_image)

    return msg.send(fail_silently=fail_silently)


def send_text_mail(subject, message, from_email, recipient_list,
                   fail_silently=False, auth_user=None, auth_password=None,
                   connection=None, html_message=None, reply_to=None, bcc=None):
    """
    extended version with reply_to
    """
    connection = connection or get_connection(
        username=auth_user,
        password=auth_password,
        fail_silently=fail_silently,
    )
    mail = EmailMultiAlternatives(subject, message, from_email, recipient_list, connection=connection,
                                  reply_to=reply_to, bcc=bcc)
    if html_message:
        mail.attach_alternative(html_message, 'text/html')

    return mail.send()


def get_email_message(user, request, reply_to_email, email_template_name, subject_template_name):
    use_https = request.is_secure()
    current_site = get_current_site(request)
    site_name = settings.SSO_SITE_NAME
    domain = current_site.domain

    c = {
        'user': user,
        'sender': request.user,
        'reply_to_email': reply_to_email,
        'brand': settings.SSO_BRAND,
        'email': user.primary_email(),
        'username': user.username,
        'domain': domain,
        'site_name': site_name,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'protocol': use_https and 'https' or 'http',
    }
    # use the user language or the default language (en-us)
    language = user.language if user.language else settings.LANGUAGE_CODE
    return i18n_email_msg_and_subj(c, email_template_name, subject_template_name, language)
