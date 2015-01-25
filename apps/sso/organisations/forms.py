# -*- coding: utf-8 -*-
import datetime
from urlparse import urlsplit, urlunsplit
from django.utils.translation import ugettext_lazy as _
from django.forms import ModelChoiceField, ModelMultipleChoiceField, ValidationError
from l10n.models import Country
from sso.accounts.models import update_or_create_organisation_account
from sso.forms import bootstrap, BaseForm, BaseTabularInlineForm
from sso.forms.fields import EmailFieldLower
from sso.emails.models import Email, EmailForward, CENTER_EMAIL_TYPE, REGION_EMAIL_TYPE, COUNTRY_EMAIL_TYPE, PERM_EVERYBODY, PERM_DWB
from .models import OrganisationPhoneNumber, OrganisationAddress, Organisation, AdminRegion, OrganisationCountry, CountryGroup


class OrganisationAddressForm(BaseForm):
    country = ModelChoiceField(queryset=Country.objects.filter(organisationcountry__isnull=False, organisationcountry__is_active=True), required=True, 
                               label=_("Country"), widget=bootstrap.Select())
    
    class Meta:
        model = OrganisationAddress
        fields = ('address_type', 'addressee', 'street_address', 'city', 'postal_code', 'country', 'region') 
        widgets = {
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
        fields = ('phone_type', 'phone') 
        widgets = {
            'phone_type': bootstrap.Select(),
            'phone': bootstrap.TextInput(attrs={'size': 50}),
        }


class OrganisationBaseForm(BaseForm):
    google_maps_url = bootstrap.ReadOnlyField(label=_("Google Maps"))
    
    class Meta:
        model = Organisation
        
        fields = ('homepage', 'google_plus_page', 'facebook_page', 'twitter_page', 'founded', 'coordinates_type', 'is_private', 'location')
        years_to_display = range(datetime.datetime.now().year - 100, datetime.datetime.now().year + 1)
        widgets = {
            'homepage': bootstrap.URLInput(attrs={'size': 50}),
            'google_plus_page': bootstrap.URLInput(attrs={'size': 50}),
            'facebook_page': bootstrap.URLInput(attrs={'size': 50}),
            'twitter_page': bootstrap.URLInput(attrs={'size': 50}),
            'country': bootstrap.Select(),
            'name': bootstrap.TextInput(attrs={'size': 50}), 
            'founded': bootstrap.SelectDateWidget(years=years_to_display, required=False),
            'coordinates_type': bootstrap.Select(),
            'center_type': bootstrap.Select(),
            'is_private': bootstrap.CheckboxInput(),
            'is_active': bootstrap.CheckboxInput(),
            'can_publish': bootstrap.CheckboxInput(),
            'location': bootstrap.OSMWidget()
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')  # remove custom user keyword      
        super(OrganisationBaseForm, self).__init__(*args, **kwargs)
        if self.instance.location:
            self.fields['google_maps_url'].initial = self.instance.google_maps_url


class OrganisationCenterAdminForm(OrganisationBaseForm):
    email_value = bootstrap.ReadOnlyField(label=_("Email address"))
    country = bootstrap.ReadOnlyField(label=_("Country"))
    center_type = bootstrap.ReadOnlyField(label=_("Center type"))
    name = bootstrap.ReadOnlyField(label=_("Name"))
    is_active = bootstrap.ReadOnlyYesNoField(label=_("Active"))
    can_publish = bootstrap.ReadOnlyYesNoField(label=_("Publish"))

    def __init__(self, *args, **kwargs):
        super(OrganisationCenterAdminForm, self).__init__(*args, **kwargs)
        
        if self.instance.admin_region:
            self.fields['admin_region'] = bootstrap.ReadOnlyField(initial=self.instance.admin_region, label=_("Admin region"))

        self.fields['email_value'].initial = str(self.instance.email)
        self.fields['country'].initial = self.instance.country
        self.fields['center_type'].initial = self.instance.get_center_type_display()
        self.fields['name'].initial = self.instance.name
        self.fields['is_active'].initial = self.instance.is_active
        self.fields['can_publish'].initial = self.instance.can_publish


class OrganisationEmailAdminForm(OrganisationBaseForm):
    """
    A Form for Admins of Organisations. The Form includes an additional Email Field for creating an Email objects
    """
    email_type = CENTER_EMAIL_TYPE
    permission = PERM_EVERYBODY
    email_value = EmailFieldLower(required=True, label=_("Email address"), widget=bootstrap.EmailInput(attrs={'placeholder': 'name@diamondway-center.org'}))

    def __init__(self, *args, **kwargs):
        super(OrganisationEmailAdminForm, self).__init__(*args, **kwargs)
        if self.instance.email:
            self.fields['email_value'].initial = str(self.instance.email)
        else:
            self.fields['email_value'].initial = "@diamondway-center.org"

    def clean_email_value(self):
        """
        the new email address must be ending with @diamondway-center.org
        """
        email_value = self.cleaned_data['email_value']
        if email_value[-22:] != '@diamondway-center.org':
            msg = _('The email address of the center must be ending with @diamondway-center.org')
            raise ValidationError(msg)
        
        if Email.objects.filter(email__iexact=email_value).exclude(organisation=self.instance).exists():
            msg = _('The email address already exists')
            raise ValidationError(msg)
            
        return email_value

    def save(self, commit=True):
        """
        save the email address or create a new email object if it does not exist 
        """
        if self.instance.email:
            old_email_value = self.instance.email.email
        else:
            old_email_value = None

        new_email_value = self.cleaned_data['email_value']
        
        if 'email_value' in self.changed_data:
            if self.instance.email:
                self.instance.email.email = new_email_value
                self.instance.email.save()
            else:
                # create email object
                email = Email(email_type=self.email_type, permission=self.permission, email=new_email_value)
                email.save()
                self.instance.email = email
                
        instance = super(OrganisationEmailAdminForm, self).save(commit)
        update_or_create_organisation_account(self.instance, old_email_value, new_email_value) 
        return instance


class OrganisationCountryAdminForm(OrganisationEmailAdminForm):
    """
    A form for a country admin for update organisations
    """
    class Meta(OrganisationBaseForm.Meta):
        fields = OrganisationBaseForm.Meta.fields + ('country', 'admin_region', 'name', 'center_type', 'is_active', 'can_publish')

    def __init__(self, *args, **kwargs):
        super(OrganisationCountryAdminForm, self).__init__(*args, **kwargs)
        self.fields['country'].queryset = self.user.get_assignable_organisation_countries()


class OrganisationRegionAdminForm(OrganisationEmailAdminForm):
    """
    A form for a regional admin
    """
    # don't use the default ModelChoiceField, because the regions are restricted to the administrable_organisation_regions
    # of the region admin
    admin_region = ModelChoiceField(queryset=AdminRegion.objects.none(), cache_choices=True, required=True, label=_("Admin Region"), widget=bootstrap.Select())
    country = bootstrap.ReadOnlyField(label=_("Country"))

    class Meta(OrganisationBaseForm.Meta):
        fields = OrganisationBaseForm.Meta.fields + ('admin_region', 'name', 'center_type', 'is_active', 'can_publish')

    def __init__(self, *args, **kwargs):
        super(OrganisationRegionAdminForm, self).__init__(*args, **kwargs)
        self.fields['admin_region'].queryset = self.user.get_assignable_organisation_regions()
        self.fields['country'].initial = str(self.instance.country)

    def clean_admin_region(self):
        """
        check if the admin_region and country fits together
        """
        data = self.cleaned_data['admin_region']

        if data.country != self.instance.country:
            msg = _("The admin region is not valid for the selected country.")
            raise ValidationError(msg)
        return data


class OrganisationCountryAdminCreateForm(OrganisationCountryAdminForm):
    """
    A form for a country admin for create and update organisations with 
    additionally email_forward field  
    """
    email_forward = EmailFieldLower(required=True, label=_("Email forwarding address"), help_text=_('The primary email forwarding address for the center'), 
                                    widget=bootstrap.EmailInput())

    def clean(self):
        """
        make sure, that email and forward email are different
        """
        cleaned_data = super(OrganisationCountryAdminCreateForm, self).clean()
        email_forward = cleaned_data.get("email_forward")
        email_value = cleaned_data.get("email_value")

        if email_value and (email_forward == email_value):
            msg = _('The email forward address and email address must be different')
            # self.add_error('admin_region', msg)  #  django 1.7
            self._errors["email_forward"] = self.error_class([msg])
            del cleaned_data["email_forward"]
            raise ValidationError(msg)
            
        return cleaned_data

    def save(self, commit=True):
        """
        creating a new center with a forward address
        """ 
        instance = super(OrganisationCountryAdminCreateForm, self).save(commit)
        
        forward = EmailForward(email=instance.email, forward=self.cleaned_data['email_forward'], primary=True)
        forward.save()
                
        return instance


class OrganisationRegionAdminCreateForm(OrganisationCountryAdminCreateForm):
    """
    A form for a regional admin to create new centers
    the selectable  countries are limited to the countries from the regions
    """
    # don't use the default ChainedModelChoiceField, because the regions are restricted to the administrable_organisation_regions
    # of the region admin
    admin_region = ModelChoiceField(queryset=AdminRegion.objects.none(), required=True, label=_("Admin Region"), widget=bootstrap.Select())
    
    def __init__(self, *args, **kwargs):
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
    email_value = EmailFieldLower(required=True, label=_("Email address"), widget=bootstrap.EmailInput(attrs={'placeholder': 'name@diamondway-center.org'}))
    # cache_choices performance optimisation and filter for organisation countries
    country = ModelChoiceField(queryset=None, required=True, label=_("Country"), widget=bootstrap.Select())
    
    class Meta:
        model = AdminRegion        
        fields = ('name', 'homepage', 'country', 'is_active')
        widgets = {
            'homepage': bootstrap.TextInput(attrs={'size': 50}),
            'country': bootstrap.Select(),
            'name': bootstrap.TextInput(attrs={'size': 50}), 
        }
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')  # remove custom user keyword      
        super(AdminRegionForm, self).__init__(*args, **kwargs)
        self.fields['country'].queryset = self.user.get_administrable_region_countries()
        if self.instance.email:
            self.fields['email_value'].initial = str(self.instance.email)
        else:
            self.fields['email_value'].initial = "@diamondway-center.org"

    def clean_email_value(self):
        """
        the new email address must be ending with @diamondway-center.org
        """
        email_value = self.cleaned_data['email_value']
        if email_value[-22:] != '@diamondway-center.org':
            msg = _('The email address of the center must be ending with @diamondway-center.org')
            raise ValidationError(msg)
        
        if Email.objects.filter(email__iexact=email_value).exclude(adminregion=self.instance).exists():
            msg = _('The email address already exists')
            raise ValidationError(msg)
            
        return email_value

    def save(self, commit=True):
        instance = super(AdminRegionForm, self).save(commit)
        if 'email_value' in self.changed_data: 
            if self.instance.email:
                self.instance.email.email = self.cleaned_data['email_value']
                self.instance.email.save()
            else:
                # create email object
                email = Email(email_type=REGION_EMAIL_TYPE, permission=PERM_DWB, email=self.cleaned_data['email_value'])
                email.save()
                instance.email = email
                instance.save()      
                
        return instance
    
    
class OrganisationCountryForm(BaseForm):
    email_value = EmailFieldLower(required=True, label=_("Email address"), widget=bootstrap.EmailInput(attrs={'placeholder': 'name@diamondway-center.org'}))
    # cache_choices performance optimisation 
    country_groups = ModelMultipleChoiceField(queryset=CountryGroup.objects.all(), cache_choices=True, required=False, 
                                              widget=bootstrap.CheckboxSelectMultiple(), label=_("Country Groups"))
    country = ModelChoiceField(queryset=Country.objects.filter(organisationcountry__isnull=True), required=True, 
                               label=_("Country"), widget=bootstrap.Select())

    class Meta:
        model = OrganisationCountry
        
        fields = ('homepage', 'country_groups', 'country', 'is_active')
        widgets = {
            'homepage': bootstrap.TextInput(attrs={'size': 50}),
        }

    def __init__(self, *args, **kwargs):
        super(OrganisationCountryForm, self).__init__(*args, **kwargs)
        if self.instance.email:
            self.fields['email_value'].initial = str(self.instance.email)
        else:
            self.fields['email_value'].initial = "@diamondway-center.org"
        if self.instance.country:
            # readonly field for the update form
            self.fields['country_text'] = bootstrap.ReadOnlyField(initial=str(self.instance.country), label=_("Country"))
            del self.fields['country']
            
    def clean_email_value(self):
        """
        the new email address must be ending with @diamondway-center.org
        """
        email_value = self.cleaned_data['email_value']
        if email_value[-22:] != '@diamondway-center.org':
            msg = _('The email address of the center must be ending with @diamondway-center.org')
            raise ValidationError(msg)
        
        if Email.objects.filter(email__iexact=email_value).exclude(organisationcountry=self.instance).exists():
            msg = _('The email address already exists')
            raise ValidationError(msg)
            
        return email_value

    def save(self, commit=True):
        instance = super(OrganisationCountryForm, self).save(commit)
        if 'email_value' in self.changed_data: 
            if self.instance.email:
                self.instance.email.email = self.cleaned_data['email_value']
                self.instance.email.save()
            else:
                # create email object
                email = Email(email_type=COUNTRY_EMAIL_TYPE, permission=PERM_DWB, email=self.cleaned_data['email_value'])
                email.save()
                instance.email = email
                instance.save()      
                
        return instance
