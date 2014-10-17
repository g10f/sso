from django.db import models
from django.contrib.gis.db import models as gis_models
from django.contrib.gis import measure
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist
from django.utils.crypto import get_random_string
from django.utils.text import capfirst
from django.utils.translation import pgettext_lazy, ugettext_lazy as _
from django.contrib.auth import get_user_model
from l10n.models import Country
from smart_selects.db_fields import ChainedForeignKey
from utils.loaddata import disable_for_loaddata
from sso.models import AbstractBaseModel, AddressMixin, PhoneNumberMixin, ensure_single_primary
from sso.emails.models import Email, CENTER_EMAIL_TYPE, COUNTRY_EMAIL_TYPE, REGION_EMAIL_TYPE, COUNTRY_GROUP_EMAIL_TYPE
from sso.registration import default_username_generator

import logging

logger = logging.getLogger(__name__)


class CountryGroup(AbstractBaseModel):
    name = models.CharField(_("name"), max_length=255)
    email = models.ForeignKey(Email, verbose_name=_("email address"), blank=True, null=True, unique=True, limit_choices_to={'email_type': COUNTRY_GROUP_EMAIL_TYPE})
    homepage = models.URLField(_("homepage"), blank=True,)
    
    class Meta(AbstractBaseModel.Meta):
        verbose_name = _('Country group')
        verbose_name_plural = _('Country groups')
        ordering = ['name']

    def __unicode__(self):
        return u"%s" % self.name


class OrganisationCountry(AbstractBaseModel):
    country = models.OneToOneField(Country, verbose_name=_("country"), null=True, limit_choices_to={'active': True})
    country_groups = models.ManyToManyField(CountryGroup, blank=True, null=True)
    homepage = models.URLField(_("homepage"), blank=True,)
    email = models.ForeignKey(Email, verbose_name=_("email address"), blank=True, null=True, limit_choices_to={'email_type': COUNTRY_EMAIL_TYPE},
                              on_delete=models.SET_NULL)
    is_active = models.BooleanField(_('active'), default=True, help_text=_('Designates whether this country should be treated as '
                                                                           'active. Unselect this instead of deleting the country.'))

    class Meta(AbstractBaseModel.Meta):
        verbose_name = _('Country')
        verbose_name_plural = _('Countries')
        ordering = ['country']

    def __unicode__(self):
        return u"%s" % self.country

    @models.permalink
    def get_absolute_url(self):
        return 'organisations:organisationcountry_detail', (), {'uuid': self.uuid, }


class ActiveAdminRegionManager(models.Manager):
    """
    custom manager for using in chained field
    """
    def get_queryset(self):
        return super(ActiveAdminRegionManager, self).get_queryset().filter(is_active=True)


class ExtraManager(models.Model):
    active_objects = ActiveAdminRegionManager()

    class Meta:
        abstract = True


class AdminRegion(AbstractBaseModel, ExtraManager):
    name = models.CharField(_("name"), max_length=255)
    homepage = models.URLField(_("homepage"), blank=True)
    country = models.ForeignKey(Country, verbose_name=_("country"), limit_choices_to={'active': True})
    email = models.ForeignKey(Email, verbose_name=_("email address"), blank=True, null=True, unique=True, limit_choices_to={'email_type': REGION_EMAIL_TYPE},
                              on_delete=models.SET_NULL)
    is_active = models.BooleanField(_('active'), default=True, help_text=_('Designates whether this region should be treated as '
                                                                           'active. Unselect this instead of deleting the region.'))
    
    class Meta(AbstractBaseModel.Meta):
        verbose_name = _('Region')
        verbose_name_plural = _('Regions')
        ordering = ['name']

    def __unicode__(self):
        return u"%s" % self.name

    @models.permalink
    def get_absolute_url(self):
        return 'organisations:adminregion_detail', (), {'uuid': self.uuid, }


def get_near_organisations(current_point, distance_from_point=None, qs=None, order=True):
    """
    get all centers with the distance from current_point 
    where the distance is less than distance_from_point
    """
    if current_point is None:
        return Organisation.objects.none()
    if qs is not None:
        organisations = qs
    else:
        organisations = Organisation.objects.all()
    if distance_from_point:
        organisations = organisations.filter(location__distance_lt=(current_point, measure.D(**distance_from_point)))
    organisations = organisations.distance(current_point)
    if order:
        return organisations.distance(current_point).order_by('distance')
    else:
        return organisations.distance(current_point)


class GeoManager(gis_models.GeoManager):
    def get_by_natural_key(self, uuid):
        return self.get(uuid=uuid)

    
class Organisation(AbstractBaseModel):
    CENTER_TYPE_CHOICES = (
        ('1', _('Buddhist Center')),
        ('2', _('Buddhist Group')),
        ('3', _('Buddhist Retreat')),            
        ('7', _('Buddhist Center & Retreat')),            
        ('16', _('Buddhist Group & Retreat')),            
    )
    COORDINATES_TYPE_CHOICES = (
        ('1', _('Unknown')),
        ('2', _('City/Village')),
        ('3', _('Exact')),
        ('4', _('Nearby')),
        # ('5', _('Others')) is not included in legacy data and seems to be redundent 
    )
    _center_type_choices = {}
    for choice in CENTER_TYPE_CHOICES:
        _center_type_choices[choice[0]] = choice[1]

    def center_type_desc(self):
        return self._center_type_choices.get(self.center_type, '')

    name = models.CharField(_("name"), max_length=255)
    country = models.ForeignKey(Country, verbose_name=_("country"), null=True, limit_choices_to={'active': True})
    admin_region = ChainedForeignKey(AdminRegion, chained_field='country', chained_model_field="country", verbose_name=_("admin region"), blank=True, null=True,
                                     limit_choices_to={'is_active': True}) 
    email = models.ForeignKey(Email, verbose_name=_("email address"), blank=True, null=True, limit_choices_to={'email_type': CENTER_EMAIL_TYPE},
                              on_delete=models.SET_NULL)
    homepage = models.URLField(_("homepage"), blank=True,)
    notes = models.TextField(_('notes'), blank=True, max_length=255)
    center_type = models.CharField(_('center type'), max_length=2, choices=CENTER_TYPE_CHOICES, db_index=True)    
    centerid = models.IntegerField(blank=True, null=True)
    founded = models.DateField(_("founded"), blank=True, null=True)
    coordinates_type = models.CharField(_('coordinates type'), max_length=1, choices=COORDINATES_TYPE_CHOICES, default='3', db_index=True)    
    latitude = models.DecimalField(_("latitude"), max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(_("longitude"), max_digits=9, decimal_places=6, blank=True, null=True)
    location = gis_models.PointField(_("longitude/latitude"), geography=True, blank=True, null=True)
    is_active = models.BooleanField(_('active'), 
                                    default=True,
                                    help_text=_('Designates whether this buddhist center should be treated as '
                                                'active. Unselect this instead of deleting buddhist center.'))
    is_private = models.BooleanField(_("private"), 
                                     help_text=_('Designates whether this buddhist center data should be treated as private and '
                                                 'only a telephone number should be displayed on public sites.'), 
                                     default=False)
    can_publish = models.BooleanField(_("publish"), 
                                      help_text=_('Designates whether this buddhist center data can be published.'), 
                                      default=True)
    # history = HistoricalRecords()
    
    objects = GeoManager()

    class Meta(AbstractBaseModel.Meta):
        permissions = (
            ("access_all_organisations", "Can access all organisations"),
            # ("read_organisation", "Can read organisation data"),
        )
        ordering = ['name']
        verbose_name = _('Buddhist Center')
        verbose_name_plural = _('Buddhist Centers')

    def __unicode__(self):
        if self.country:
            return u'%s (%s)' % (self.name, self.country.iso2_code)
        else:
            return u'%s' % self.name

    def get_near_organisations(self):
        return get_near_organisations(self.location).exclude(pk=self.pk)[:10]

    @models.permalink
    def get_absolute_url(self):
        return 'organisations:organisation_detail', (), {'uuid': self.uuid, }
    
    @property
    def google_maps_url(self):
        if self.location:
            return "http://maps.google.de/maps?q=%f,+%f&iwloc=A" % (self.location.y, self.location.x)
        else:
            ""
        
    def google_maps_link(self):
        return u'<a href="%s">%s</a>' % (self.google_maps_url, 'google maps')
    google_maps_link.allow_tags = True
    google_maps_link.short_description = _('Maps')

    def homepage_link(self):
        if self.homepage:
            return u'<a href="%s">%s</a>' % (self.homepage, self.homepage)
        else:
            return ''
    homepage_link.allow_tags = True
    homepage_link.short_description = _('homepage')
        
    def phone_number(self, phone_type=None):
        """Return the default phone number or None."""
        try:
            if phone_type is None:
                return self.phonenumber_set.get(primary=True)
            else:
                return self.phonenumber_set.filter(phone_type=phone_type)[0]
        except ObjectDoesNotExist:
            pass
        except IndexError:
            pass            
        return None
    primary_phone = property(phone_number)       


class OrganisationAddress(AbstractBaseModel, AddressMixin):
    ADDRESSTYPE_CHOICES = (
        ('meditation', _('Meditation')),
        ('post', _('Post Only')),
    )        
    address_type = models.CharField(_("address type"), choices=ADDRESSTYPE_CHOICES, max_length=20)
    organisation = models.ForeignKey(Organisation)
    careof = models.CharField(_('care of (c/o)'), default='', blank=True, max_length=80)

    class Meta(AbstractBaseModel.Meta, AddressMixin.Meta):
        unique_together = (("organisation", "address_type"),)
    
    @classmethod
    def ensure_single_primary(cls, organisation):
        ensure_single_primary(organisation.organisationaddress_set.all())
                

class OrganisationPhoneNumber(AbstractBaseModel, PhoneNumberMixin):
    PHONE_CHOICES = [
        ('home', pgettext_lazy('phone number', 'Home')),  # with translation context 
        ('mobile', _('Mobile')),
        ('mobile2', _('Mobile#2')),
        ('fax', _('Fax')),
        ('other', _('Other')),
        ('other2', _('Other#2')),
    ]   
    phone_type = models.CharField(_("phone type"), help_text=_('Mobile, home, office, etc.'), choices=PHONE_CHOICES, max_length=20)
    organisation = models.ForeignKey(Organisation)

    class Meta(AbstractBaseModel.Meta, PhoneNumberMixin.Meta):
        # unique_together = (("organisation", "phone_type"),)
        pass

    @classmethod
    def ensure_single_primary(cls, organisation):
        ensure_single_primary(organisation.organisationphonenumber_set.all())
        

@receiver(post_delete, sender=Organisation)
@disable_for_loaddata
def post_delete_center_account(sender, instance, **kwargs):
    deactivate_center_account(instance)


@receiver(post_save, sender=Organisation)
@disable_for_loaddata
def post_save_center_account(sender, instance, **kwargs):
    update_center_account(instance)


def deactivate_center_account(organisation):
    """
    deactivate the center user account if the center was deleted
    """
    try:
        if organisation.email:
            for user in get_user_model().objects.filter(email__iexact=organisation.email.email):
                user.is_active = False
                user.save()
    except ObjectDoesNotExist:
        pass


def create_center_account(center):
    first_name = 'BuddhistCenter'
    last_name = capfirst(center.name)
    username = default_username_generator(first_name, last_name)
    user = get_user_model()(first_name='BuddhistCenter', last_name=last_name, username=username, email=center.email.email, is_center=True)
    user.set_password(get_random_string(40))
    user.save()
    user.organisations = [center]
    user.add_default_roles()


def update_center_account(organisation):
    """
    deactivate or activate the center user account if the center account is activated or deactivated
    """
    try:
        if organisation.email:
            qs = get_user_model().objects.filter(email__iexact=organisation.email.email)
            if not qs.exists():
                if organisation.is_active:
                    create_center_account(organisation)
            else:
                for user in get_user_model().objects.filter(email__iexact=organisation.email.email):
                    if organisation.is_active != user.is_active:
                        user.is_active = organisation.is_active
                        user.save()
    except ObjectDoesNotExist:
        pass
