# -*- coding: utf-8 -*-
import datetime
from django.utils.translation import ugettext as _

from sso.forms import bootstrap, BaseForm
from .models import OrganisationPhoneNumber, OrganisationAddress, Organisation 

class OrganisationAddressForm(BaseForm):
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


class OrganisationPhoneNumberForm(BaseForm):
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
    google_maps_url = bootstrap.ReadOnlyField(label=_("Google Maps"))

    class Meta:
        model = Organisation
        
        fields = ('name', 'email', 'homepage', 'founded', 'latitude', 'longitude', 'is_active', 'center_type', 'country', 'admin_region')
        years_to_display = range(datetime.datetime.now().year - 100, datetime.datetime.now().year + 1)
        widgets = {
                   'email': bootstrap.TextInput(attrs={'size': 50}),
                   'homepage': bootstrap.TextInput(attrs={'size': 50}),
                   'country': bootstrap.Select(),
                   'admin_region': bootstrap.Select(),
                   'name': bootstrap.TextInput(attrs={'size': 50}), 
                   'founded': bootstrap.SelectDateWidget(years=years_to_display, required=False),
                   'latitude': bootstrap.TextInput(attrs={'size': 50}),
                   'longitude': bootstrap.TextInput(attrs={'size': 50}),
                   'center_type': bootstrap.Select(),
                   'is_active': bootstrap.CheckboxInput()
                   
                   }
        
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')  # remove custom user keyword      
        # initialise the form
        super(OrganisationForm, self).__init__(*args, **kwargs)
        
        instance = kwargs.get('instance')
        # regional admins can create only centers for the there region
        if not user.has_perm("accounts.change_all_users"):
            if instance:  # update view 
                del self.fields['admin_region']
            else:  # create view. The user must be a regional admin
                assert(user.has_perm("accounts.change_reg_users"))                
                admin_regions = user.get_administrable_regions()
                assert(len(admin_regions) > 0)  # TODO: handle this case more elegant
                self.fields['admin_region'].queryset = admin_regions
                self.fields['admin_region'].required = True
        
    def opts(self):
        # i need the model verbose_name in the html form, is there a better way?
        return self._meta.model._meta
