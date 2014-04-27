# -*- coding: utf-8 -*-
import datetime

#from django.contrib.staticfiles.templatetags.staticfiles import static
from .models import OrganisationPhoneNumber, OrganisationAddress, Organisation 

#from django import forms
from sso.forms import bootstrap, BaseForm

class AddressForm(BaseForm):
    class Meta:
        model = OrganisationAddress
        fields = ('primary', 'address_type', 'addressee', 'street_address', 'city', 'postal_code', 'country', 'state') 
        widgets = {
                   'primary': bootstrap.CheckboxInput(),
                   'address_type': bootstrap.Select(),
                   'addressee': bootstrap.TextInput(attrs={'size': 50}),
                   'street_address': bootstrap.Textarea(attrs={'cols': 50, 'rows': 2}),
                   'city': bootstrap.TextInput(attrs={'size': 50}),
                   'postal_code': bootstrap.TextInput(attrs={'size': 50}),
                   'country': bootstrap.Select()
                   }
    
    def opts(self):
        # i need the model verbose_name in the html form, is there a better way?
        return self._meta.model._meta
    
    def template(self):
        return 'edit_inline/stacked.html'


class PhoneNumberForm(BaseForm):
    class Meta:
        model = OrganisationPhoneNumber
        fields = ('phone_type', 'phone', 'primary') 
        widgets = {
                   'phone_type': bootstrap.Select(),
                   'phone': bootstrap.TextInput(attrs={'size': 50}),
                   'primary': bootstrap.CheckboxInput()
                   }
    
    def opts(self):
        # i need the model verbose_name in the html form, is there a better way?
        return self._meta.model._meta
    
    def template(self):
        return 'edit_inline/tabular.html'


class OrganisationForm(BaseForm):
    class Meta:
        model = Organisation
        
        fields = (
                  'email', 'homepage', 'founded', 'latitude', 'longitude',)
        years_to_display = range(datetime.datetime.now().year - 100, datetime.datetime.now().year + 1)
        widgets = {
                   'email': bootstrap.TextInput(attrs={'size': 50}),
                   'homepage': bootstrap.TextInput(attrs={'size': 50}),
                   'name': bootstrap.TextInput(attrs={'size': 50, 'readonly': True}), 
                   'founded': bootstrap.SelectDateWidget(years=years_to_display, required=False),
                   'latitude': bootstrap.TextInput(attrs={'size': 50}),
                   'longitude': bootstrap.TextInput(attrs={'size': 50}),
                   }
    
    def opts(self):
        # i need the model verbose_name in the html form, is there a better way?
        return self._meta.model._meta
    
    def template(self):
        return 'edit_inline/single_stacked.html'
