
import os
import re

from celery import Celery

from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sso.settings')

app = Celery('sso')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

SSO_SEND_FROM_VERIFIED_EMAIL_ADDRESSES_RE = re.compile(settings.SSO_SEND_FROM_VERIFIED_EMAIL_ADDRESSES, re.I)


@app.task(ignore_result=True)
def send_mail_task(subject, message, recipient_list, from_email=None, html_message=None, fail_silently=False, **kwargs):
    if from_email and not SSO_SEND_FROM_VERIFIED_EMAIL_ADDRESSES_RE.match(from_email):
        from_email = None

    if html_message is not None:
        from sso.utils.email import send_html_mail
        send_html_mail(subject, message, recipient_list, from_email, html_message, fail_silently)
    else:
        from django.core.mail import send_mail
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)
