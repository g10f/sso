import logging
import re

from pytz import timezone
from sorl import thumbnail

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.gis import measure
from django.contrib.gis.db import models as gis_models
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import models
from django.utils.timezone import localtime, now
from django.utils.translation import pgettext_lazy, ugettext_lazy as _
from l10n.models import Country
from smart_selects.db_fields import ChainedForeignKey
from sso.decorators import memoize
from sso.emails.models import Email, CENTER_EMAIL_TYPE, COUNTRY_EMAIL_TYPE, REGION_EMAIL_TYPE, COUNTRY_GROUP_EMAIL_TYPE
from sso.fields import URLFieldEx
from sso.models import AbstractBaseModel, AddressMixin, PhoneNumberMixin, ensure_single_primary, get_filename

logger = logging.getLogger(__name__)


def is_validation_period_active(organisation):
    if settings.SSO_VALIDATION_PERIOD_IS_ACTIVE:
        if settings.SSO_VALIDATION_PERIOD_IS_ACTIVE_FOR_ALL:
            return True
        else:
            return organisation and organisation.uses_user_activation
    else:
        return False


def is_validation_period_active_for_user(user):
    try:
        user_organisation = user.organisations.first()
    except ObjectDoesNotExist:
        user_organisation = None

    return is_validation_period_active(user_organisation)


class TzWorld(models.Model):
    """
    table from http://efele.net/maps/tz/world/ with timezones and areas
    infos; http://shisaa.jp/postset/postgis-and-postgresql-in-action-timezones.html
    """
    gid = models.AutoField(primary_key=True)
    tzid = models.CharField(max_length=30, blank=True)
    geom = gis_models.PolygonField(blank=True, null=True)
    objects = gis_models.GeoManager()

    class Meta:
        # managed = False
        db_table = 'tz_world'


class CountryGroup(AbstractBaseModel):
    name = models.CharField(_("name"), max_length=255)
    email = models.OneToOneField(Email, verbose_name=_("email address"), blank=True, null=True, limit_choices_to={'email_type': COUNTRY_GROUP_EMAIL_TYPE})
    homepage = models.URLField(_("homepage"), blank=True,)
    
    class Meta(AbstractBaseModel.Meta):
        verbose_name = _('Country group')
        verbose_name_plural = _('Country groups')
        ordering = ['name']

    def __unicode__(self):
        return u"%s" % self.name


class OrganisationCountry(AbstractBaseModel):
    country = models.OneToOneField(Country, verbose_name=_("country"), null=True, limit_choices_to={'active': True})
    country_groups = models.ManyToManyField(CountryGroup, blank=True)
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
        return 'organisations:organisationcountry_detail', (), {'uuid': self.uuid.hex, }


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
    email = models.OneToOneField(Email, verbose_name=_("email address"), blank=True, null=True, limit_choices_to={'email_type': REGION_EMAIL_TYPE},
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
        return 'organisations:adminregion_detail', (), {'uuid': self.uuid.hex, }


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
    # TODO: make configurable
    CENTER_TYPE_CHOICES = (
        ('1', pgettext_lazy('Organisation Type', 'Center')),
        ('2', pgettext_lazy('Organisation Type', 'Group')),
        ('3', pgettext_lazy('Organisation Type', 'Retreat')),
        ('4', pgettext_lazy('Organisation Type', 'Contact')),
        ('7', pgettext_lazy('Organisation Type', 'Center & Retreat')),
        ('16', pgettext_lazy('Organisation Type', 'Group & Retreat')),
    )
    COORDINATES_TYPE_CHOICES = (
        ('1', _('Unknown')),
        ('2', _('City/Village')),
        ('3', _('Exact')),
        ('4', _('Nearby')),
    )
    _center_type_choices = {}
    for choice in CENTER_TYPE_CHOICES:
        _center_type_choices[choice[0]] = choice[1]

    def center_type_desc(self):
        return self._center_type_choices.get(self.center_type, '')

    _original_location = None

    name = models.CharField(_("name"), max_length=255)
    name_native = models.CharField(_("name in native language"), max_length=255, blank=True)
    country = models.ForeignKey(Country, verbose_name=_("country"), null=True, limit_choices_to={'active': True})
    admin_region = ChainedForeignKey(AdminRegion, chained_field='country', chained_model_field="country", verbose_name=_("admin region"), blank=True, null=True,
                                     limit_choices_to={'is_active': True}) 
    email = models.ForeignKey(Email, verbose_name=_("email address"), blank=True, null=True, limit_choices_to={'email_type': CENTER_EMAIL_TYPE},
                              on_delete=models.SET_NULL)
    slug = models.SlugField(_("Slug Name"), blank=True, unique=True, help_text=_("Used for URLs, auto-generated from name if blank"), max_length=255)
    homepage = models.URLField(_("homepage"), blank=True,)
    google_plus_page = URLFieldEx(domain='plus.google.com', verbose_name=_("Google+ page"), blank=True)
    facebook_page = URLFieldEx(domain='www.facebook.com', verbose_name=_("Facebook page"), blank=True)
    twitter_page = URLFieldEx(domain='twitter.com', verbose_name=_("Twitter page"), blank=True)
    notes = models.TextField(_('notes'), blank=True, max_length=255)
    center_type = models.CharField(_('organisation type'), max_length=2, choices=CENTER_TYPE_CHOICES, db_index=True)
    centerid = models.IntegerField(blank=True, help_text=_("id from the previous center DB (obsolete)"), null=True)
    founded = models.DateField(_("founded"), blank=True, null=True)
    coordinates_type = models.CharField(_('coordinates type'), max_length=1, choices=COORDINATES_TYPE_CHOICES, default='3', db_index=True, blank=True)
    latitude = models.DecimalField(_("latitude"), max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(_("longitude"), max_digits=9, decimal_places=6, blank=True, null=True)
    location = gis_models.PointField(_("location"), geography=True, blank=True, null=True)
    timezone = models.CharField(_('timezone'), blank=True, max_length=254)
    is_active = models.BooleanField(_('active'),
                                    default=True,
                                    help_text=_('Designates whether this organisation should be treated as '
                                                'active. Unselect this instead of deleting organisation.'))
    is_private = models.BooleanField(_("private"), 
                                     help_text=_('Designates whether this organisation data should be treated as private and '
                                                 'only a telephone number should be displayed on public sites.'), 
                                     default=False)
    can_publish = models.BooleanField(_("publish"), 
                                      help_text=_('Designates whether this organisation data can be published.'),
                                      default=True)
    uses_user_activation = models.BooleanField(_("uses activation"),
                                               help_text=_('Designates whether this organisation uses the new user activation process.'),
                                               default=False)

    objects = GeoManager()

    class Meta(AbstractBaseModel.Meta):
        permissions = (
            ("access_all_organisations", "Can access all organisations"),
            # ("read_organisation", "Can read organisation data"),
        )
        ordering = ['name']
        verbose_name = _('Organisation')
        verbose_name_plural = _('Organisations')

    def __init__(self, *args, **kwargs):
        """
        save original location that we can check if the location changed and update the timezone
        in pre_save if the location changed
        """
        super(Organisation, self).__init__(*args, **kwargs)
        self._original_location = self.location

    def save(self, force_insert=False, force_update=False, *args, **kwargs):
        if self.location != self._original_location:
            self.timezone = self.timezone_from_location

        super(Organisation, self).save(force_insert, force_update, *args, **kwargs)
        self._original_location = self.location

    @property
    def timezone_from_location(self):
        if self.location:
            try:
                return TzWorld.objects.only('tzid').get(geom__contains=self.location).tzid
            except ObjectDoesNotExist as e:
                logger.warning(e)
            except MultipleObjectsReturned as e:
                logger.exception(e)
        return ""

    @property
    def local_datetime(self):
        if self.timezone:
            return localtime(now(), timezone(self.timezone)).strftime('%Y-%m-%d %H:%M:%S %z')
        else:
            return ""

    @memoize
    def get_last_modified_deep(self):
        last_modified_list = [self.last_modified]
        if hasattr(self, '_prefetched_objects_cache') and ('organisationaddress' in self._prefetched_objects_cache):
            last_modified_list += [obj.last_modified for obj in self.organisationaddress_set.all()]
        else:
            last_modified_list += self.organisationaddress_set.values_list("last_modified", flat=True)
            
        if hasattr(self, '_prefetched_objects_cache') and ('organisationphonenumber' in self._prefetched_objects_cache):
            last_modified_list += [obj.last_modified for obj in self.organisationphonenumber_set.all()]
        else:
            last_modified_list += self.organisationphonenumber_set.values_list("last_modified", flat=True)
        
        if hasattr(self, '_prefetched_objects_cache') and ('organisationpicture' in self._prefetched_objects_cache):
            last_modified_list += [obj.last_modified for obj in self.organisationpicture_set.all()]
        else:
            last_modified_list += self.organisationpicture_set.values_list("last_modified", flat=True)

        last_modified = max(last_modified_list)
        return last_modified

    def __unicode__(self):
        if self.country:
                return u'%s (%s)' % (self.name, self.country.iso2_code)
        else:
            return u'%s' % self.name

    def get_near_organisations(self):
        return get_near_organisations(self.location, qs=Organisation.objects.filter(is_active=True).exclude(pk=self.pk))[:10]

    @models.permalink
    def get_absolute_url(self):
        return 'organisations:organisation_detail', (), {'uuid': self.uuid.hex, }
    
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

    @classmethod
    def get_primary_or_none(cls, queryset):
        # iterate through all uses the prefetch_related cache
        for item in queryset:
            if item.primary:
                return item
        return None

    @property
    def primary_address(self):
        return self.get_primary_or_none(self.organisationaddress_set.all())

    @property
    def primary_phone(self):
        return self.get_primary_or_none(self.organisationphonenumber_set.all())


def generate_filename(instance, filename):
    return u'organisation_image/%s/%s' % (instance.organisation.uuid.hex, get_filename(filename.encode('ascii', 'replace')))


class OrganisationPicture(AbstractBaseModel):
    MAX_PICTURE_SIZE = 5242880  # 5 MB
    organisation = models.ForeignKey(Organisation)
    title = models.CharField(_("title"), max_length=255, blank=True)
    description = models.TextField(_("description"), blank=True, max_length=2048)
    picture = thumbnail.ImageField(_('picture'), upload_to=generate_filename)  # , storage=MediaStorage())
    order = models.IntegerField(default=0, help_text=_('Overwrites the alphabetic order.'))

    class Meta(AbstractBaseModel.Meta):
        verbose_name = _('organisation picture')
        verbose_name_plural = _('organisation pictures')
        ordering = ['order']


class OrganisationAddress(AbstractBaseModel, AddressMixin):
    ADDRESSTYPE_CHOICES = [
        ('physical', pgettext_lazy('organisation address', 'Physical Address')),
        ('postal', pgettext_lazy('organisation address', 'Postal Address'))
    ]
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
        

def deactivate_center_account(email):
    """
    deactivate the center user account if the center was deleted
    """
    try:
        user = get_user_model().objects.get_by_email(email.email)
        user.is_active = False
        user.save()
    except ObjectDoesNotExist:
        pass


def default_unique_slug_generator(slug, organisation=None):
    """
    search for existing slugs and create a new one with a not existing number
    after slug if necessary
    """

    if organisation is not None:
        exists = Organisation.objects.filter(slug=slug).exclude(pk=organisation.pk).exists()
    else:
        exists = Organisation.objects.filter(slug=slug).exists()
    if not exists:
        return slug

    slug_pattern = r'^%s-([0-9]+)$' % slug
    organisations = Organisation.objects.filter(slug__regex=slug_pattern)

    existing = set()
    slug_pattern = r'%s-(?P<no>[0-9]+)' % slug
    prog = re.compile(slug_pattern)
    for organisation in organisations:
        m = prog.match(organisation.slug)  # we should always find a match, because of the filter
        result = m.groupdict()
        no = 0 if not result['no'] else result['no']
        existing.add(int(no))

    new_no = 1
    while new_no in existing:
        new_no += 1

    slug = u"%s-%d" % (slug, new_no)
    return slug
