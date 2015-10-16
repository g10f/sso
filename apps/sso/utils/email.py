from __future__ import absolute_import

from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from django.core.mail.message import EmailMessage
from django.conf import settings


def send_html_mail(subject, message, html_message, to, fail_silently=False):
    msg_alternative = MIMEMultipart('alternative')
    msg_html = MIMEText(html_message, _subtype='html', _charset='utf-8')
    msg_text = MIMEText(message, _charset='utf-8')
    msg_alternative.attach(msg_text)
    msg_alternative.attach(msg_html)

    msg = EmailMessage(subject, None, None, to)
    msg.mixed_subtype = 'related'
    msg.attach(msg_alternative)

    if settings.SSO_EMAIL_LOGO:
        with open(settings.SSO_EMAIL_LOGO, 'rb') as f:
            email_image = MIMEImage(f.read())
            email_image.add_header('Content-ID', '<{}>'.format("logo"))
            email_image.add_header("Content-Disposition", "inline", filename="logo")
            msg.attach(email_image)

    return msg.send(fail_silently=fail_silently)
