import datetime

from django import forms
from django.conf import settings
from django.forms import ModelChoiceField, ModelMultipleChoiceField, ValidationError
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from l10n.models import Country
from sso.emails.models import Email, EmailForward, CENTER_EMAIL_TYPE, REGION_EMAIL_TYPE, COUNTRY_EMAIL_TYPE, \
    PERM_EVERYBODY, PERM_DWB
from sso.forms import bootstrap, BaseForm, BaseTabularInlineForm, BLANK_CHOICE_DASH, BaseStackedInlineForm
from sso.forms.fields import EmailFieldLower
from sso.models import clean_picture
from sso.signals import update_or_create_organisation_account
from .models import OrganisationPhoneNumber, OrganisationAddress, Organisation, AdminRegion, OrganisationCountry, \
    CountryGroup, OrganisationPicture

SSO_ORGANISATION_EMAIL_DOMAIN = getattr(settings, 'SSO_ORGANISATION_EMAIL_DOMAIN', '@g10f.de')


class OrganisationPictureForm(BaseStackedInlineForm):
    order = forms.IntegerField(label=_("Order"), required=False,
                               widget=bootstrap.Select(choices=BLANK_CHOICE_DASH + list(zip(range(3), range(3)))))

    class Meta:
        model = OrganisationPicture
        fields = ('picture', 'title', 'description', 'order')
        widgets = {
            'title': bootstrap.TextInput(attrs={'size': 50}),
            'description': bootstrap.Textarea(),
            'picture': bootstrap.ImageWidget(),
        }

    def clean_order(self):
        order = self.cleaned_data["order"]
        if order is None:
            order = 0
        return order

    def clean_picture(self):
        picture = self.cleaned_data["picture"]
        return clean_picture(picture, OrganisationPicture.MAX_PICTURE_SIZE)


class OrganisationAddressForm(BaseForm):
    country = ModelChoiceField(queryset=Country.objects.filter(active=True), required=True,
                               label=_("Country"), widget=bootstrap.Select2(), to_field_name="iso2_code")

    class Meta:
        model = OrganisationAddress
        fields = (
            'address_type', 'addressee', 'careof', 'street_address', 'city', 'city_native', 'postal_code', 'country',
            'region')
        widgets = {
            'address_type': bootstrap.Select(attrs={'class': 'address_type'}),
            'addressee': bootstrap.TextInput(attrs={'size': 50}),
            'careof': bootstrap.TextInput(attrs={'size': 50}),
            'street_address': bootstrap.Textarea(attrs={'cols': 50, 'rows': 2}),
            'city': bootstrap.TextInput(attrs={'size': 50}),
            'city_native': bootstrap.TextInput(attrs={'size': 50}),
            'postal_code': bootstrap.TextInput(attrs={'size': 50}),
            'country': bootstrap.Select2(),
            'region': bootstrap.TextInput(attrs={'size': 50}),
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        if instance and instance.country:
            # update initial field because of to_field_name in ModelChoiceField
            kwargs['initial'] = {'country': instance.country.iso2_code}

        super().__init__(*args, **kwargs)

    def template(self):
        return 'organisations/addresses.html'


class OrganisationPhoneNumberForm(BaseTabularInlineForm):
    class Meta:
        model = OrganisationPhoneNumber
        fields = (
            'phone_type',
            'phone')
        widgets = {
            'phone_type': bootstrap.Select(),
            'phone': bootstrap.TextInput(attrs={'size': 50}),
        }


class OrganisationBaseForm(BaseForm):
    google_maps_url = bootstrap.ReadOnlyField(label=_("Google Maps"))

    class Meta:
        model = Organisation

        fields = (
            'name_native', 'homepage', 'source_urls', 'google_plus_page', 'facebook_page', 'twitter_page', 'founded',
            'coordinates_type',
            'is_private', 'is_live', 'location', 'neighbour_distance', 'transregional_distance', 'timezone')
        years_to_display = range(datetime.datetime.now().year - 100, datetime.datetime.now().year + 1)
        widgets = {
            'homepage': bootstrap.URLInput(attrs={'size': 50}),
            'source_urls': bootstrap.Textarea(attrs={'rows': '3'}),
            'google_plus_page': bootstrap.URLInput(attrs={'size': 50}),
            'facebook_page': bootstrap.URLInput(attrs={'size': 50}),
            'twitter_page': bootstrap.URLInput(attrs={'size': 50}),
            'association': bootstrap.Select(),
            'name': bootstrap.TextInput(attrs={'size': 50}),
            'name_native': bootstrap.TextInput(attrs={'size': 50}),
            'founded': bootstrap.SelectDateWidget(years=years_to_display),
            'coordinates_type': bootstrap.Select(),
            'center_type': bootstrap.Select(),
            'is_private': bootstrap.CheckboxInput(),
            'is_active': bootstrap.CheckboxInput(),
            'is_live': bootstrap.CheckboxInput(),
            'timezone': bootstrap.Select2(),
            'location': bootstrap.OSMWidget(),
            'neighbour_distance': bootstrap.TextInput(attrs={'type': 'number', 'step': '0.001'}),
            'transregional_distance': bootstrap.TextInput(attrs={'type': 'number', 'step': '0.001'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')  # remove custom user keyword
        super().__init__(*args, **kwargs)
        if self.instance.location:
            self.fields['google_maps_url'].initial = self.instance.google_maps_url

    def clean(self):
        cleaned_data = super().clean()

        # check combination of coordinates_type location
        coordinates_type = cleaned_data['coordinates_type']
        location = cleaned_data['location']
        if location and coordinates_type == '':
            msg = _("Please select a coordinates type.")
            self.add_error('coordinates_type', ValidationError(msg, params={'active': 'organisationaddress_set'}))
        if not location and coordinates_type:
            cleaned_data['coordinates_type'] = ''

        return cleaned_data


class OrganisationCenterAdminForm(OrganisationBaseForm):
    email_value = bootstrap.ReadOnlyField(label=_("Email address"))
    center_type = bootstrap.ReadOnlyField(label=_("Organisation type"))
    name = bootstrap.ReadOnlyField(label=_("Name"))
    is_active = bootstrap.ReadOnlyYesNoField(label=_("Active"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.organisation_country:
            self.fields['organisation_country'] = bootstrap.ReadOnlyField(initial=self.instance.organisation_country,
                                                                          label=_("Country"))
        if self.instance.admin_region:
            self.fields['admin_region'] = bootstrap.ReadOnlyField(initial=self.instance.admin_region,
                                                                  label=_("Admin region"))

        self.fields['email_value'].initial = force_str(self.instance.email)
        self.fields['center_type'].initial = self.instance.get_center_type_display()
        self.fields['name'].initial = self.instance.name
        self.fields['is_active'].initial = self.instance.is_active


class OrganisationEmailAdminForm(OrganisationBaseForm):
    """
    A Form for Admins of Organisations. The Form includes an additional Email Field for creating an Email objects
    """
    email_type = CENTER_EMAIL_TYPE
    permission = PERM_EVERYBODY
    email_value = EmailFieldLower(required=True, label=_("Email address"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.email:
            self.fields['email_value'].initial = force_str(self.instance.email)
        else:
            self.fields['email_value'].initial = SSO_ORGANISATION_EMAIL_DOMAIN

    def clean_email_value(self):
        """
        the new email address must be ending with SSO_ORGANISATION_EMAIL_DOMAIN
        """
        email_value = self.cleaned_data['email_value']
        if SSO_ORGANISATION_EMAIL_DOMAIN and (
                email_value[-len(SSO_ORGANISATION_EMAIL_DOMAIN):] != SSO_ORGANISATION_EMAIL_DOMAIN):
            msg = _('The email address of the center must be ending with %(domain)s') % {
                'domain': SSO_ORGANISATION_EMAIL_DOMAIN}
            raise ValidationError(msg)

        if Email.objects.filter(email=email_value).exclude(organisation=self.instance).exists():
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

        instance = super().save(commit)

        # enable brand specific modification
        update_or_create_organisation_account.send_robust(sender=self.__class__, organisation=self.instance,
                                                          old_email_value=old_email_value,
                                                          new_email_value=new_email_value, user=self.user)
        return instance


class OrganisationAssociationAdminForm(OrganisationEmailAdminForm):
    class Meta(OrganisationBaseForm.Meta):
        fields = OrganisationBaseForm.Meta.fields + (
            'association', 'admin_region', 'organisation_country', 'name', 'center_type',
            'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assignable_associations = self.user.get_assignable_associations()
        if not OrganisationCountry.objects.filter(association__in=assignable_associations).exists():
            del self.fields['organisation_country']
            del self.fields['admin_region']

        self.fields['association'].queryset = assignable_associations


class OrganisationCountryAdminForm(OrganisationEmailAdminForm):
    """
    A form for a country admin for update organisations
    """
    # use the ModelChoiceField, because organisation_country is a ChainedForeignKey and we don't display the
    # association
    organisation_country = ModelChoiceField(queryset=OrganisationCountry.objects.none(), required=True,
                                            label=_("Country"), widget=bootstrap.Select2())

    class Meta(OrganisationBaseForm.Meta):
        fields = OrganisationBaseForm.Meta.fields + (
            'organisation_country', 'admin_region', 'name', 'center_type', 'is_active')  # , 'can_publish')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assignable_countries = self.user.get_assignable_organisation_countries()
        self.fields['organisation_country'].queryset = assignable_countries
        if not AdminRegion.objects.filter(organisation_country__in=assignable_countries).exists():
            del self.fields['admin_region']

    def clean(self):
        cleaned_data = super().clean()
        self.instance.association = cleaned_data['organisation_country'].association
        return cleaned_data


class OrganisationRegionAdminForm(OrganisationEmailAdminForm):
    """
    A form for a regional admin
    """
    # don't use the default ModelChoiceField, because the regions are restricted to the
    # administrable_organisation_regions of the region admin
    organisation_country = ModelChoiceField(queryset=OrganisationCountry.objects.none(), required=True,
                                            label=_("Country"), widget=bootstrap.Select2())
    admin_region = ModelChoiceField(queryset=AdminRegion.objects.none(), required=True, label=_("Admin Region"),
                                    widget=bootstrap.Select2())

    class Meta(OrganisationBaseForm.Meta):
        fields = OrganisationBaseForm.Meta.fields + (
            'organisation_country', 'admin_region', 'name', 'center_type', 'is_active')  # , 'can_publish')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        regions = self.user.get_assignable_organisation_regions()
        self.fields['admin_region'].queryset = regions
        self.fields['organisation_country'].queryset = OrganisationCountry.objects.filter(adminregion__in=regions,
                                                                                          association__is_external=False).distinct()

    def clean(self):
        """
        check if the admin_region and country fits together
        """
        cleaned_data = super().clean()
        admin_region = cleaned_data['admin_region']
        organisation_country = cleaned_data['organisation_country']
        if admin_region.organisation_country != organisation_country:
            msg = _("The admin region is not valid for the selected country.")
            raise ValidationError(msg)

        self.instance.association = cleaned_data['organisation_country'].association
        return cleaned_data


class EmailForwardMixin(object):
    def check_email_forward(self):
        """
        make sure, that email and forward email are different
        """
        cleaned_data = self.cleaned_data
        email_forward = cleaned_data.get("email_forward")
        email_value = cleaned_data.get("email_value")

        if email_value and (email_forward == email_value):
            msg = _('The email forward address and email address must be different')
            # self.add_error('admin_region', msg)  #  django 1.7
            self._errors["email_forward"] = self.error_class([msg])
            del cleaned_data["email_forward"]
            raise ValidationError(msg)

        return cleaned_data

    def save_email_forward(self, instance):
        forward = EmailForward(email=instance.email, forward=self.cleaned_data['email_forward'], primary=True)
        forward.save()
        return instance


class OrganisationAssociationAdminCreateForm(EmailForwardMixin, OrganisationAssociationAdminForm):
    """
    A form for a association admins for create organisations with
    additionally email_forward field
    """
    email_forward = EmailFieldLower(required=True, label=_("Email forwarding address"),
                                    help_text=_('The primary email forwarding address for the organisation'),
                                    widget=bootstrap.EmailInput())

    def clean(self):
        super().clean()
        # check email forward
        return self.check_email_forward()

    def save(self, commit=True):
        """
        creating a new center with a forward address
        """
        instance = super().save(commit)
        return self.save_email_forward(instance)


class OrganisationCountryAdminCreateForm(EmailForwardMixin, OrganisationCountryAdminForm):
    """
    A form for a country admin for create organisations with
    additionally email_forward field
    """
    email_forward = EmailFieldLower(required=True, label=_("Email forwarding address"),
                                    help_text=_('The primary email forwarding address for the organisation'),
                                    widget=bootstrap.EmailInput())

    def clean(self):
        super().clean()
        # check email forward
        return self.check_email_forward()

    def save(self, commit=True):
        """
        creating a new center with a forward address
        """
        instance = super().save(commit)
        return self.save_email_forward(instance)


class OrganisationRegionAdminCreateForm(EmailForwardMixin, OrganisationRegionAdminForm):
    """
    A form for a regional admin to create new centers
    the selectable  countries are limited to the countries from the regions
    with additionally email_forward field
    """
    email_forward = EmailFieldLower(required=True, label=_("Email forwarding address"),
                                    help_text=_('The primary email forwarding address for the organisation'),
                                    widget=bootstrap.EmailInput())

    def clean(self):
        super().clean()
        # check email forward
        return self.check_email_forward()

    def save(self, commit=True):
        """
        creating a new center with a forward address
        """
        instance = super().save(commit)
        return self.save_email_forward(instance)


class AdminRegionForm(BaseForm):
    email_value = EmailFieldLower(required=True, label=_("Email address"))
    organisation_country = ModelChoiceField(queryset=None, required=True, label=_("Country"),
                                            widget=bootstrap.Select2())

    class Meta:
        model = AdminRegion
        fields = ('name', 'homepage', 'organisation_country', 'is_active')
        widgets = {
            'homepage': bootstrap.TextInput(attrs={'size': 50}),
            'organisation_country': bootstrap.Select2(),
            'name': bootstrap.TextInput(attrs={'size': 50}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')  # remove custom user keyword
        super().__init__(*args, **kwargs)
        self.fields['organisation_country'].queryset = self.user.get_administrable_region_countries()
        if self.instance.email:
            self.fields['email_value'].initial = force_str(self.instance.email)
        else:
            self.fields['email_value'].initial = SSO_ORGANISATION_EMAIL_DOMAIN

    def clean_email_value(self):
        """
        the new email address must be ending with SSO_ORGANISATION_EMAIL_DOMAIN
        """
        email_value = self.cleaned_data['email_value']
        if SSO_ORGANISATION_EMAIL_DOMAIN and email_value[
                                             -len(SSO_ORGANISATION_EMAIL_DOMAIN):] != SSO_ORGANISATION_EMAIL_DOMAIN:
            msg = _('The email address of the center must be ending with %(domain)s') % {
                'domain': SSO_ORGANISATION_EMAIL_DOMAIN}
            raise ValidationError(msg)

        if Email.objects.filter(email=email_value).exclude(adminregion=self.instance).exists():
            msg = _('The email address already exists')
            raise ValidationError(msg)

        return email_value

    def save(self, commit=True):
        instance = super().save(commit)
        if 'email_value' in self.changed_data:
            if self.instance.email:
                self.instance.email.email = self.cleaned_data['email_value']
                self.instance.email.save()
            else:
                # create email object
                email = Email(email_type=REGION_EMAIL_TYPE, permission=PERM_DWB,
                              email=self.cleaned_data['email_value'])
                email.save()
                instance.email = email
                instance.save()

        return instance


class OrganisationCountryForm(BaseForm):
    email_value = EmailFieldLower(required=True, label=_("Email address"))
    country_groups = ModelMultipleChoiceField(queryset=CountryGroup.objects.all(), required=False,
                                              widget=bootstrap.CheckboxSelectMultiple(), label=_("Country Groups"))

    class Meta:
        model = OrganisationCountry

        fields = ('association', 'homepage', 'country_groups', 'country', 'is_active')
        widgets = {
            'homepage': bootstrap.TextInput(attrs={'size': 50}),
            'association': bootstrap.Select(),
            'country': bootstrap.Select2(),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')  # remove custom user keyword
        super().__init__(*args, **kwargs)
        if self.instance.email:
            self.fields['email_value'].initial = force_str(self.instance.email)
        else:
            self.fields['email_value'].initial = SSO_ORGANISATION_EMAIL_DOMAIN
        if self.instance.pk is not None and self.instance.country:
            # readonly field for the update form
            self.fields['country_text'] = bootstrap.ReadOnlyField(initial=force_str(self.instance.country),
                                                                  label=_("Country"))
            self.fields['association_text'] = bootstrap.ReadOnlyField(initial=force_str(self.instance.association),
                                                                      label=_("Association"))
            del self.fields['association']
            del self.fields['country']
        else:
            self.fields['association'].queryset = self.user.get_administrable_associations()

    def clean_email_value(self):
        """
        the new email address must be ending with SSO_ORGANISATION_EMAIL_DOMAIN
        """
        email_value = self.cleaned_data['email_value']
        if SSO_ORGANISATION_EMAIL_DOMAIN and email_value[
                                             -len(SSO_ORGANISATION_EMAIL_DOMAIN):] != SSO_ORGANISATION_EMAIL_DOMAIN:
            msg = _('The email address of the center must be ending with %(domain)s') % {
                'domain': SSO_ORGANISATION_EMAIL_DOMAIN}
            raise ValidationError(msg)

        if Email.objects.filter(email=email_value).exclude(organisationcountry=self.instance).exists():
            msg = _('The email address already exists')
            raise ValidationError(msg)

        return email_value

    def save(self, commit=True):
        instance = super().save(commit)
        if 'email_value' in self.changed_data:
            if self.instance.email:
                self.instance.email.email = self.cleaned_data['email_value']
                self.instance.email.save()
            else:
                # create email object
                email = Email(email_type=COUNTRY_EMAIL_TYPE, permission=PERM_DWB,
                              email=self.cleaned_data['email_value'])
                email.save()
                instance.email = email
                instance.save()

        return instance
