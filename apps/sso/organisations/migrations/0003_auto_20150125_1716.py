# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import sso.fields


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0002_auto_20141115_2029'),
    ]

    operations = [
        migrations.AddField(
            model_name='organisation',
            name='facebook_page',
            field=sso.fields.URLFieldEx(domain=b'www.facebook.com', verbose_name='Facebook page', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='organisation',
            name='google_plus_page',
            field=sso.fields.URLFieldEx(domain=b'plus.google.com', verbose_name='Google+ page', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='organisation',
            name='twitter_page',
            field=sso.fields.URLFieldEx(domain=b'twitter.com', verbose_name='Twitter page', blank=True),
            preserve_default=True,
        ),
    ]
