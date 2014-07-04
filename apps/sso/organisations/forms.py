# -*- coding: utf-8 -*-
import datetime
from django.utils.translation import ugettext_lazy as _
from django.forms import ModelChoiceField
from sso.forms import bootstrap, BaseForm
from sso.emails.models import EmailForward, EmailAlias
from .models import OrganisationPhoneNumber, OrganisationAddress, Organisation
from l10n.models import Country 

class OrganisationAddressForm(BaseForm):
    country = ModelChoiceField(queryset=Country.objects.filter(organisationcountry__isnull=False), cache_choices=True, required=True, label=_("Country"), widget=bootstrap.Select())
    
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
    
    def template(self):
        return 'edit_inline/stacked.html'


class OrganisationBaseTabularInlineForm(BaseForm):    
    def template(self):
        return 'edit_inline/tabular.html'


class OrganisationPhoneNumberForm(OrganisationBaseTabularInlineForm):
    class Meta:
        model = OrganisationPhoneNumber
        fields = ('phone_type', 'phone', 'primary') 
        widgets = {
            'phone_type': bootstrap.Select(),
            'phone': bootstrap.TextInput(attrs={'size': 50}),
            'primary': bootstrap.CheckboxInput()
        }


class OrganisationEmailForwardForm(OrganisationBaseTabularInlineForm):
    class Meta:
        model = EmailForward
        fields = ('forward', ) 
        widgets = {
            'forward': bootstrap.TextInput(attrs={'size': 50}),
        }


class OrganisationEmailAliasForm(OrganisationBaseTabularInlineForm):
    class Meta:
        model = EmailAlias
        fields = ('alias', ) 
        widgets = {
            'alias': bootstrap.TextInput(attrs={'size': 50}),
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

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')  # remove custom user keyword      
        super(OrganisationBaseForm, self).__init__(*args, **kwargs)


class OrganisationCenterForm(OrganisationBaseForm):
    email = bootstrap.ReadOnlyField(label=_("Email address"))

    def __init__(self, *args, **kwargs):
        super(OrganisationCenterForm, self).__init__(*args, **kwargs)
        self.fields['email'].initial = str(self.instance.email)
        

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
        super(OrganisationAdminForm, self).__init__(*args, **kwargs)
        self.fields['admin_region'].queryset = self.user.get_administrable_regions()
