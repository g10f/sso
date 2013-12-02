# -*- coding: utf-8 -*-

from django.shortcuts import render
from django.core.urlresolvers import reverse
from django.contrib.sites.models import get_current_site
from django.utils.translation import ugettext as _


def home(request, template="home.html"):
    current_site = get_current_site(request)
    site_name = current_site.name
    
    apps = None
    if request.user.is_authenticated():
        apps = request.user.get_apps()
        
    data = {'title': _('Home'),
            'login_url': reverse('accounts:login'),
            'site_name': site_name,
            'apps': apps
            }
    return render(request, template, data)
