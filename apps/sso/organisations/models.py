import logging
import re

from pytz import timezone, common_timezones, UnknownTimeZoneError
from sorl import thumbnail

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.gis import measure
from django.contrib.gis.db.models import PolygonField, PointField
from django.contrib.gis.db.models.functions import Distance
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import models
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.timezone import localtime, now
from django.utils.translation import pgettext_lazy, ugettext_lazy as _
from l10n.models import Country
from smart_selects.db_fields import ChainedForeignKey
from sso.decorators import memoize
from sso.emails.models import Email, CENTER_EMAIL_TYPE, COUNTRY_EMAIL_TYPE, REGION_EMAIL_TYPE, COUNTRY_GROUP_EMAIL_TYPE
from sso.fields import URLFieldEx, URLArrayField
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
    if user.is_center or user.is_service:
        return False
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
    geom = PolygonField(blank=True, null=True)

    class Meta:
        # managed = False
        db_table = 'tz_world'
        required_db_features = ['gis_enabled']


class CountryGroup(AbstractBaseModel):
    name = models.CharField(_("name"), max_length=255)
    email = models.OneToOneField(Email, on_delete=models.SET_NULL, verbose_name=_("email address"), blank=True,
                                 null=True, limit_choices_to={'email_type': COUNTRY_GROUP_EMAIL_TYPE})
    homepage = models.URLField(_("homepage"), blank=True, )

    class Meta(AbstractBaseModel.Meta):
        verbose_name = _('Country group')
        verbose_name_plural = _('Country groups')
        ordering = ['name']

    def __str__(self):
        return self.name


class Association(AbstractBaseModel):
    name = models.CharField(_("name"), max_length=255)
    homepage = models.URLField(_("homepage"), blank=True)
    email_domain = models.CharField(_("email domain"), blank=True, max_length=254)
    is_active = models.BooleanField(_('active'), default=True,
                                    help_text=_('Designates whether this association should be treated as '
                                                'active. Unselect this instead of deleting the association.'))
    is_external = models.BooleanField(_('external'), default=False,
                                      help_text=_('Designates whether this association is managed externally.'))
    is_selectable = models.BooleanField(_('selectable'), default=True, help_text=_(
        'Designates whether the organisations of this association can be selected by/assigned to users.'))

    class Meta(AbstractBaseModel.Meta):
        verbose_name = _('Association')
        verbose_name_plural = _('Associations')
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('api:v2_association', kwargs={'uuid': self.uuid.hex})


def default_association():
    if multiple_associations():
        return Association.objects.get_by_natural_key(settings.SSO_DEFAULT_ASSOCIATION_UUID).pk
    else:
        return Association.objects.first().pk


def multiple_associations():
    count = cache.get_or_set('association__count', Association.objects.count)
    return count > 1


def region_count():
    return cache.get_or_set('region__count', AdminRegion.objects.count)


class ActiveOrganisationCountryManager(models.Manager):
    """
    custom manager for using in chained field
    """

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class ExtraOrganisationCountryManager(models.Model):
    active_objects = ActiveOrganisationCountryManager()

    class Meta:
        abstract = True


class OrganisationCountry(AbstractBaseModel, ExtraOrganisationCountryManager):
    association = models.ForeignKey(Association, on_delete=models.CASCADE, verbose_name=_("association"),
                                    default=default_association, limit_choices_to={'is_active': True})
    country = models.ForeignKey(Country, on_delete=models.CASCADE, verbose_name=_("country"),
                                limit_choices_to={'active': True})
    country_groups = models.ManyToManyField(CountryGroup, blank=True, related_name='countries')
    homepage = models.URLField(_("homepage"), blank=True, )
    email = models.ForeignKey(Email, verbose_name=_("email address"), blank=True, null=True,
                              limit_choices_to={'email_type': COUNTRY_EMAIL_TYPE},
                              on_delete=models.SET_NULL)
    is_active = models.BooleanField(_('active'), default=True,
                                    help_text=_('Designates whether this country should be treated as '
                                                'active. Unselect this instead of deleting the country.'))

    class Meta(AbstractBaseModel.Meta):
        verbose_name = _('Country')
        verbose_name_plural = _('Countries')
        ordering = ['country']
        unique_together = (("country", "association"),)

    def __str__(self):
        # return u"%s" % self.country
        if multiple_associations():
            return "%s, %s" % (self.country, self.association)
        else:
            return '%s' % self.country

    def get_absolute_url(self):
        return reverse('organisations:organisationcountry_detail', kwargs={'uuid': self.uuid.hex, })

    @memoize
    def get_last_modified_deep(self):
        last_modified_list = [self.last_modified, self.country.last_modified]

        last_modified = max(last_modified_list)
        return last_modified


class ActiveAdminRegionManager(models.Manager):
    """
    custom manager for using in chained field
    """

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class ExtraManager(models.Model):
    active_objects = ActiveAdminRegionManager()

    class Meta:
        abstract = True


class AdminRegion(AbstractBaseModel, ExtraManager):
    name = models.CharField(_("name"), max_length=255)
    homepage = models.URLField(_("homepage"), blank=True)
    organisation_country = models.ForeignKey(OrganisationCountry, verbose_name=_("country"), null=True,
                                             limit_choices_to={'is_active': True},
                                             on_delete=models.SET_NULL)
    email = models.OneToOneField(Email, verbose_name=_("email address"), blank=True, null=True,
                                 limit_choices_to={'email_type': REGION_EMAIL_TYPE},
                                 on_delete=models.SET_NULL)
    is_active = models.BooleanField(_('active'), default=True,
                                    help_text=_('Designates whether this region should be treated as '
                                                'active. Unselect this instead of deleting the region.'))
    slug = models.SlugField(_("Slug Name"), blank=True, unique=True,
                            help_text=_("Used for URLs, auto-generated from name if blank"), max_length=255)

    class Meta(AbstractBaseModel.Meta):
        verbose_name = _('Region')
        verbose_name_plural = _('Regions')
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('organisations:adminregion_detail', kwargs={'uuid': self.uuid.hex})


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
    organisations = organisations.annotate(distance=Distance('location', current_point))
    if order:
        return organisations.order_by('distance')
    else:
        return organisations


class Organisation(AbstractBaseModel):
    COORDINATES_TYPE_CHOICES = (
        # ('1', _('Unknown')),
        ('2', _('City/Village')),
        ('3', _('Exact')),
        ('4', _('Nearby')),
    )
    _center_type_choices = {}
    for choice in settings.CENTER_TYPE_CHOICES:
        _center_type_choices[choice[0]] = choice[1]

    def center_type_desc(self):
        return self._center_type_choices.get(self.center_type, '')

    _original_location = None

    name = models.CharField(_("name"), max_length=255)
    order = models.IntegerField(default=0, help_text=_('Overwrites the alphabetic order.'))
    name_native = models.CharField(_("name in native language"), max_length=255, blank=True)
    association = models.ForeignKey(Association, verbose_name=_("association"), default=default_association, null=True,
                                    limit_choices_to={'is_active': True},
                                    on_delete=models.CASCADE)
    organisation_country = ChainedForeignKey(OrganisationCountry, chained_field='association',
                                             chained_model_field="association", verbose_name=_("country"), blank=True,
                                             null=True, limit_choices_to={'is_active': True},
                                             on_delete=models.SET_NULL)
    admin_region = ChainedForeignKey(AdminRegion, chained_field='organisation_country',
                                     chained_model_field="organisation_country", on_delete=models.SET_NULL,
                                     verbose_name=_("admin region"), blank=True, null=True,
                                     limit_choices_to={'is_active': True})
    email = models.ForeignKey(Email, verbose_name=_("email address"), blank=True, null=True,
                              limit_choices_to={'email_type': CENTER_EMAIL_TYPE},
                              on_delete=models.SET_NULL)
    slug = models.SlugField(_("Slug Name"), blank=True, unique=True,
                            help_text=_("Used for URLs, auto-generated from name if blank"), max_length=255)
    homepage = models.URLField(_("homepage"), blank=True)
    source_urls = URLArrayField(blank=True, null=True, verbose_name=_('source urls'),
                                help_text=_("Newline separated list of URLs, which are redirected to the "
                                            "homepage"))
    google_plus_page = URLFieldEx(domain='plus.google.com', verbose_name=_("Google+ page"), blank=True)
    facebook_page = URLFieldEx(domain='www.facebook.com', verbose_name=_("Facebook page"), blank=True)
    twitter_page = URLFieldEx(domain='twitter.com', verbose_name=_("Twitter page"), blank=True)
    notes = models.TextField(_('notes'), blank=True, max_length=255)
    center_type = models.CharField(_('organisation type'), max_length=2, choices=settings.CENTER_TYPE_CHOICES,
                                   db_index=True)
    centerid = models.IntegerField(blank=True, help_text=_("id from the previous center DB (obsolete)"), null=True)
    founded = models.DateField(_("founded"), blank=True, null=True)
    coordinates_type = models.CharField(_('coordinates type'), max_length=1, choices=COORDINATES_TYPE_CHOICES,
                                        default='3', db_index=True, blank=True)
    location = PointField(_("location"), geography=True, blank=True, null=True)
    timezone = models.CharField(_('timezone'), choices=list(zip(common_timezones, common_timezones)), blank=True,
                                max_length=254)
    is_active = models.BooleanField(_('active'),
                                    default=True,
                                    help_text=_('Designates whether this organisation should be treated as '
                                                'active. Unselect this instead of deleting organisation.'))
    is_private = models.BooleanField(_("private"),
                                     help_text=_(
                                         'Designates whether this organisation data should be treated as private and '
                                         'only a telephone number should be displayed on public sites.'),
                                     default=False)
    uses_user_activation = models.BooleanField(_("uses activation"),
                                               help_text=_('Designates whether this organisation uses the new user '
                                                           'activation process.'),
                                               default=False)
    neighbour_distance = models.DecimalField(_("neighbour distance"),
                                             help_text=_('Distance used for neighbour calculations [km].'),
                                             max_digits=8, decimal_places=3, blank=True, null=True)
    transregional_distance = models.DecimalField(_("transregional distance"),
                                                 help_text=_(
                                                     'Distance used for calculations of transregional events [km].'),
                                                 max_digits=8, decimal_places=3, blank=True, null=True)
    is_live = models.BooleanField(_('live'),
                                  default=True,
                                  help_text=_('Designates whether this organisation is live. '
                                              'Unselect this for organisations which are prelive.'))

    class Meta(AbstractBaseModel.Meta):
        permissions = (
            ("access_all_organisations", "Can access all organisations"),
            # ("read_organisation", "Can read organisation data"),
        )
        required_db_features = ['gis_enabled']
        ordering = ['order', 'name']
        verbose_name = _('Organisation')
        verbose_name_plural = _('Organisations')

    def __init__(self, *args, **kwargs):
        """
        save original location that we can check if the location changed and update the timezone
        in pre_save if the location changed
        """
        super().__init__(*args, **kwargs)
        self._original_location = self.location

    def save(self, force_insert=False, force_update=False, *args, **kwargs):
        if self.timezone == '' and self.location != self._original_location:
            self.timezone = self.timezone_from_location

        super().save(force_insert, force_update, *args, **kwargs)
        self._original_location = self.location

    @property
    def neighbour_measure_distance(self):
        if self.neighbour_distance:
            return measure.Distance(**{'km': self.neighbour_distance})
        else:
            return None

    @property
    def transregional_measure_distance(self):
        if self.transregional_distance:
            return measure.Distance(**{'km': self.transregional_distance})
        else:
            return None

    @property
    def timezone_from_location(self):
        if self.location:
            try:
                tzid = TzWorld.objects.only('tzid').get(geom__contains=self.location).tzid
                # check if python timezone works for ..
                timezone(tzid)
                return tzid
            except ObjectDoesNotExist as e:
                logger.warning(e)
            except MultipleObjectsReturned as e:
                logger.exception(e)
            except UnknownTimeZoneError as e:
                logger.exception(e)
        return ""

    @property
    def local_datetime(self):
        if self.timezone:
            try:
                return localtime(now(), timezone(self.timezone)).strftime('%Y-%m-%d %H:%M:%S %z')
            except UnknownTimeZoneError as e:
                logger.error(e)
        return ""

    @memoize
    def get_last_modified_deep(self):
        last_modified_list = [self.last_modified]
        if hasattr(self, '_prefetched_objects_cache') and ('organisationaddress_set' in self._prefetched_objects_cache):
            last_modified_list += [obj.last_modified for obj in self.organisationaddress_set.all()]
        else:
            last_modified_list += self.organisationaddress_set.values_list("last_modified", flat=True)

        if hasattr(self, '_prefetched_objects_cache') and ('organisationphonenumber_set' in self._prefetched_objects_cache):
            last_modified_list += [obj.last_modified for obj in self.organisationphonenumber_set.all()]
        else:
            last_modified_list += self.organisationphonenumber_set.values_list("last_modified", flat=True)

        if hasattr(self, '_prefetched_objects_cache') and ('organisationpicture_set' in self._prefetched_objects_cache):
            last_modified_list += [obj.last_modified for obj in self.organisationpicture_set.all()]
        else:
            last_modified_list += self.organisationpicture_set.values_list("last_modified", flat=True)

        last_modified = max(last_modified_list)
        return last_modified

    def __str__(self):
        if self.organisation_country:
            if multiple_associations():
                return '%s, %s (%s)' % (self.name, self.association, self.organisation_country.country.iso2_code)
            else:
                return '%s (%s)' % (self.name, self.organisation_country.country.iso2_code)
        else:
            return self.name

    def get_near_organisations(self):
        if self.neighbour_distance is not None:
            return get_near_organisations(
                self.location, distance_from_point={'km': self.neighbour_distance},
                qs=Organisation.objects.filter(is_active=True, is_live=True).exclude(pk=self.pk))
        else:
            return get_near_organisations(
                self.location,
                qs=Organisation.objects.filter(is_active=True, is_live=True).exclude(pk=self.pk))[:10]

    def get_absolute_url(self):
        return reverse('organisations:organisation_detail', kwargs={'uuid': self.uuid.hex})

    @property
    def google_maps_url(self):
        if self.location:
            return "http://maps.google.de/maps?q=%f,+%f&iwloc=A" % (self.location.y, self.location.x)
        else:
            ""

    @mark_safe
    def google_maps_link(self):
        return '<a href="%s">%s</a>' % (self.google_maps_url, self.get_coordinates_type_display())

    google_maps_link.short_description = _('Maps')

    @mark_safe
    def homepage_link(self):
        if self.homepage:
            return '<a href="%s">%s</a>' % (self.homepage, self.homepage)
        else:
            return ''

    homepage_link.short_description = _('homepage')

    @classmethod
    def get_primary_or_none(cls, queryset, **kwargs):
        # the primary flag is not used instead return the type specified in kwargs or the first item
        if len(queryset) == 0:
            return None
        elif len(queryset) == 1:
            return queryset.first()
        else:
            try:
                attr, value = next(iter(kwargs.items()))
                for item in queryset:
                    if getattr(item, attr) == value:
                        return item
            except StopIteration:
                pass
            return queryset.first()

    @property
    def primary_address(self):
        return self.get_primary_or_none(self.organisationaddress_set.all(), address_type='physical')

    @property
    def primary_phone(self):
        return self.get_primary_or_none(self.organisationphonenumber_set.all(), phone_type='home')


def generate_filename(instance, filename):
    return 'organisation_image/%s/%s' % (
        instance.organisation.uuid.hex, get_filename(filename.encode('ascii', 'replace')))


class OrganisationPicture(AbstractBaseModel):
    MAX_PICTURE_SIZE = 5242880  # 5 MB
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)
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
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)
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
    phone_type = models.CharField(_("phone type"), help_text=_('Mobile, home, office, etc.'), choices=PHONE_CHOICES,
                                  max_length=20)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)

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


def default_unique_slug_generator(slug, model, obj=None):
    """
    search for existing slugs and create a new one with a not existing number
    after slug if necessary
    """

    if obj is not None:
        exists = model.objects.filter(slug=slug).exclude(pk=obj.pk).exists()
    else:
        exists = model.objects.filter(slug=slug).exists()
    if not exists:
        return slug

    slug_pattern = r'^%s-([0-9]+)$' % slug
    objects = model.objects.filter(slug__regex=slug_pattern)

    existing = set()
    slug_pattern = r'%s-(?P<no>[0-9]+)' % slug
    prog = re.compile(slug_pattern)
    for obj in objects:
        m = prog.match(obj.slug)  # we should always find a match, because of the filter
        result = m.groupdict()
        no = 0 if not result['no'] else result['no']
        existing.add(int(no))

    new_no = 1
    while new_no in existing:
        new_no += 1

    slug = "%s-%d" % (slug, new_no)
    return slug
