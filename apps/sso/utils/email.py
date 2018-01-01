from __future__ import absolute_import

from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.conf import settings
from django.core.mail.message import EmailMessage
from sso.celery import send_mail_task


def send_mail(subject, message, recipient_list, from_email=None, html_message=None, fail_silently=False,
              apply_async=None, countdown=0, **kwargs):
    if apply_async is None:
        apply_async = settings.SSO_ASYNC_EMAILS
    kwargs.update({'subject': subject, 'message': message, 'from_email': from_email, 'recipient_list': recipient_list,
                   'html_message': html_message, 'fail_silently': fail_silently})
    if apply_async:
        return send_mail_task.apply_async(countdown=countdown, kwargs=kwargs)
    else:
        return send_mail_task(**kwargs)


def send_html_mail(subject, message, recipient_list, from_email, html_message, fail_silently=False):
    msg_alternative = MIMEMultipart('alternative')
    msg_html = MIMEText(html_message, _subtype='html', _charset='utf-8')
    msg_text = MIMEText(message, _charset='utf-8')
    msg_alternative.attach(msg_text)
    msg_alternative.attach(msg_html)

    msg = EmailMessage(subject, '', from_email, recipient_list)
    msg.mixed_subtype = 'related'
    msg.attach(msg_alternative)

    if settings.SSO_EMAIL_LOGO:
        with open(settings.SSO_EMAIL_LOGO, 'rb') as f:
            email_image = MIMEImage(f.read())
            email_image.add_header('Content-ID', '<{}>'.format("logo"))
            email_image.add_header("Content-Disposition", "inline", filename="logo")
            msg.attach(email_image)

    return msg.send(fail_silently=fail_silently)
