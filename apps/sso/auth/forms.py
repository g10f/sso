# -*- coding: utf-8 -*-
from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.utils.text import capfirst
from sso.forms import bootstrap

class EmailAuthenticationForm(AuthenticationForm):
    username = forms.CharField(max_length=75,
        error_messages={'required': 'Please enter your Email address or Username.'}, 
        label=_("Email address or Username"), 
        widget=bootstrap.TextInput(attrs={'placeholder': capfirst(_('Email address or Username')), 'autofocus': ''}))
    password = forms.CharField(
        label=_("Password"), 
        error_messages={'required': 'Please enter your Password.'}, 
        widget=bootstrap.PasswordInput(attrs={'placeholder': capfirst(_('Password'))}))
