# -*- coding: utf-8 -*-
import datetime
from django.utils.translation import ugettext_lazy as _
from django.forms import ModelChoiceField, ModelMultipleChoiceField, ValidationError
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
    # country = ModelChoiceField(queryset=Country.objects.filter(organisationcountry__isnull=False), cache_choices=True, required=True, label=_("Country"), widget=bootstrap.Select())
    
    class Meta:
        model = Organisation
        
        fields = ('name', 'homepage', 'founded', 'latitude', 'longitude', 'is_active', 'is_private', 'can_publish', 'center_type')
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
            'can_publish': bootstrap.CheckboxInput(),
            'email': bootstrap.Select()
        }


class OrganisationCenterAdminForm(OrganisationBaseForm):
    email = bootstrap.ReadOnlyField(label=_("Email address"))
    country = bootstrap.ReadOnlyField(label=_("Country"))

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')  # remove custom user keyword      
        super(OrganisationCenterAdminForm, self).__init__(*args, **kwargs)
        self.fields['email'].initial = self.instance.email
        if self.instance.admin_region:
            self.fields['admin_region'] = bootstrap.ReadOnlyField(initial=self.instance.admin_region, label=_("Admin region"))
        self.fields['country'].initial = self.instance.country
        

class OrganisationCountryAdminForm(OrganisationBaseForm):
    """
    A form for a country admin
    - email
    - admin_region
    - country
    """
    class Meta(OrganisationBaseForm.Meta):
        fields = OrganisationBaseForm.Meta.fields + ('email', 'country', 'admin_region')

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')  # remove custom user keyword      
        super(OrganisationCountryAdminForm, self).__init__(*args, **kwargs)
        self.fields['country'].queryset = self.user.get_assignable_organisation_countries()


class OrganisationRegionAdminForm(OrganisationBaseForm):
    """
    A form for a regional admin
    - email
    - admin_region
    """
    # don't use the default ChainedModelChoiceField, because the regions are restricted to the administrable_organisation_regions
    # of the region admin
    admin_region = ModelChoiceField(queryset=AdminRegion.objects.none(), cache_choices=True, required=True, label=_("Admin Region"), widget=bootstrap.Select())

    class Meta(OrganisationBaseForm.Meta):
        fields = OrganisationBaseForm.Meta.fields + ('email', 'admin_region')

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')  # remove custom user keyword      
        super(OrganisationRegionAdminForm, self).__init__(*args, **kwargs)
        self.fields['admin_region'].queryset = self.user.get_assignable_organisation_regions()
        self.fields['country'] = bootstrap.ReadOnlyField(initial=self.instance.country, label=_("Country"))

    def clean_admin_region(self):
        """
        check if the admin_region and country fits together
        """
        data = self.cleaned_data['admin_region']

        if data.country != self.instance.country:
            msg = _("The admin region is not valid for the selected country.")
            raise ValidationError(msg)
        return data


class OrganisationRegionAdminCreateForm(OrganisationBaseForm):
    """
    A form for a regional admin to create new centers
    the selectable  countries are limited to the countries from the regions
    - email
    - admin_region
    """
    # don't use the default ChainedModelChoiceField, because the regions are restricted to the administrable_organisation_regions
    # of the region admin
    admin_region = ModelChoiceField(queryset=AdminRegion.objects.none(), cache_choices=True, required=True, label=_("Admin Region"), widget=bootstrap.Select())
    
    class Meta(OrganisationBaseForm.Meta):
        fields = OrganisationBaseForm.Meta.fields + ('email', 'country', 'admin_region')

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')  # remove custom user keyword      
        super(OrganisationRegionAdminCreateForm, self).__init__(*args, **kwargs)
        regions = self.user.get_assignable_organisation_regions()
        self.fields['admin_region'].queryset = regions
        self.fields['country'].queryset = Country.objects.filter(adminregion__in=regions).distinct()

    def clean(self):
        """
        check if the admin_region and country fits together
        """
        cleaned_data = super(OrganisationBaseForm, self).clean()
        admin_region = cleaned_data.get("admin_region")
        country = cleaned_data.get("country")

        if admin_region and country:
            if admin_region.country != country:
                msg = _("The admin region is not valid for the selected country.")
                # self.add_error('admin_region', msg)  #  django 1.7
                self._errors["admin_region"] = self.error_class([msg])
                del cleaned_data["admin_region"]
        return cleaned_data


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
