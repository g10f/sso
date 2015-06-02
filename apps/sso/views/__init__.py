# -*- coding: utf-8 -*-
from django.conf import settings
from django.shortcuts import render
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _


def home(request, template="home.html"):
    site_name = settings.SSO_SITE_NAME
    
    apps = None
    if request.user.is_authenticated():
        apps = request.user.get_apps()
        
    data = {'title': _('Home'),
            'login_url': reverse('auth:login'),
            'site_name': site_name,
            'apps': apps
            }
    return render(request, template, data)
