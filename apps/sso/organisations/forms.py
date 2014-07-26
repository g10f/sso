# -*- coding: utf-8 -*-
import datetime
from django.utils.translation import ugettext_lazy as _
from django.forms import ModelChoiceField, ModelMultipleChoiceField
from sso.forms import bootstrap, BaseForm, BaseTabularInlineForm
from .models import OrganisationPhoneNumber, OrganisationAddress, Organisation, AdminRegion, OrganisationCountry, CountryGroup
from l10n.models import Country 

class OrganisationAddressForm(BaseForm):
    country = ModelChoiceField(queryset=Country.objects.filter(organisationcountry__isnull=False), cache_choices=True, required=True, label=_("Country"), widget=bootstrap.Select())
    
    class Meta:
        model = OrganisationAddress
        fields = ('primary', 'address_type', 'addressee', 'street_address', 'city', 'postal_code', 'country', 'region') 
        widgets = {
            'primary': bootstrap.CheckboxInput(),
            'address_type': bootstrap.Select(),
            'addressee': bootstrap.TextInput(attrs={'size': 50}),
            'street_address': bootstrap.Textarea(attrs={'cols': 50, 'rows': 2}),
            'city': bootstrap.TextInput(attrs={'size': 50}),
            'postal_code': bootstrap.TextInput(attrs={'size': 50}),
            'country': bootstrap.Select(),
            'region': bootstrap.TextInput(attrs={'size': 50}),            
        }
    
    def template(self):
        return 'edit_inline/stacked.html'


class OrganisationPhoneNumberForm(BaseTabularInlineForm):
    class Meta:
        model = OrganisationPhoneNumber
        fields = ('phone_type', 'phone', 'primary') 
        widgets = {
            'phone_type': bootstrap.Select(),
            'phone': bootstrap.TextInput(attrs={'size': 50}),
            'primary': bootstrap.CheckboxInput()
        }


class OrganisationBaseForm(BaseForm):
    google_maps_url = bootstrap.ReadOnlyField(label=_("Google Maps"))
    country = ModelChoiceField(queryset=Country.objects.filter(organisationcountry__isnull=False), cache_choices=True, required=True, label=_("Country"), widget=bootstrap.Select())
    
    class Meta:
        model = Organisation
        
        fields = ('name', 'homepage', 'founded', 'latitude', 'longitude', 'is_active', 'is_private', 'can_publish', 'center_type', 'country')
        years_to_display = range(datetime.datetime.now().year - 100, datetime.datetime.now().year + 1)
        widgets = {
            'homepage': bootstrap.TextInput(attrs={'size': 50}),
            'country': bootstrap.Select(),
            'name': bootstrap.TextInput(attrs={'size': 50}), 
            'founded': bootstrap.SelectDateWidget(years=years_to_display, required=False),
            'latitude': bootstrap.TextInput(attrs={'size': 50}),
            'longitude': bootstrap.TextInput(attrs={'size': 50}),
            'center_type': bootstrap.Select(),
            'is_active': bootstrap.CheckboxInput(),
            'is_private': bootstrap.CheckboxInput(),
            'can_publish': bootstrap.CheckboxInput()
        }


class OrganisationCenterForm(OrganisationBaseForm):
    email = bootstrap.ReadOnlyField(label=_("Email address"))

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')  # remove custom user keyword      
        super(OrganisationCenterForm, self).__init__(*args, **kwargs)
        self.fields['email'].initial = str(self.instance.email)
        self.fields['country'].queryset = self.user.get_administrable_organisation_countries()
        

class OrganisationAdminForm(OrganisationBaseForm):
    """
    A form for a user who can add new organisations and edit the fields
    - email
    - admin_region
    """
    class Meta(OrganisationBaseForm.Meta):
        fields = OrganisationBaseForm.Meta.fields + ('admin_region', 'email')
        widgets = OrganisationBaseForm.Meta.widgets
        widgets['admin_region'] = bootstrap.Select()
        widgets['email'] = bootstrap.Select()

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')  # remove custom user keyword      
        super(OrganisationAdminForm, self).__init__(*args, **kwargs)
        self.fields['admin_region'].queryset = self.user.get_administrable_regions()
        self.fields['country'].queryset = self.user.get_administrable_organisation_countries()


class AdminRegionForm(BaseForm):
    # cache_choices performance optimisation and filter for organisation countries
    country = ModelChoiceField(queryset=Country.objects.filter(organisationcountry__isnull=False), cache_choices=True, required=True, label=_("Country"), widget=bootstrap.Select())
    
    class Meta:
        model = AdminRegion
        
        fields = ('name', 'email', 'homepage', 'country')
        widgets = {
            'homepage': bootstrap.TextInput(attrs={'size': 50}),
            'country': bootstrap.Select(),
            'email': bootstrap.Select(),
            'name': bootstrap.TextInput(attrs={'size': 50}), 
        }
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')  # remove custom user keyword      
        super(AdminRegionForm, self).__init__(*args, **kwargs)
        self.fields['country'].queryset = self.user.get_administrable_region_countries()


class OrganisationCountryForm(BaseForm):
    # cache_choices performance optimisation 
    country_groups = ModelMultipleChoiceField(queryset=CountryGroup.objects.all(), cache_choices=True, required=False, widget=bootstrap.CheckboxSelectMultiple(), label=_("Country Groups"))
    
    class Meta:
        model = OrganisationCountry
        
        fields = ('email', 'homepage', 'country_groups')
        widgets = {
            'homepage': bootstrap.TextInput(attrs={'size': 50}),
            'email': bootstrap.Select(),
        }
