from django.db import models
from django.core.exceptions import ObjectDoesNotExist
#from django.dispatch import receiver
#from django.db.models import signals
from django.utils.translation import pgettext_lazy, ugettext_lazy as _

from l10n.models import Country

from sso.models import AbstractBaseModel, AddressMixin, PhoneNumberMixin, ensure_single_primary

import logging

logger = logging.getLogger(__name__)


class AdminRegion(AbstractBaseModel):
    name = models.CharField(_("name"), max_length=255)

    class Meta(AbstractBaseModel.Meta):
        ordering = ['name']

    def __unicode__(self):
        return u"%s" % (self.name)


class Organisation(AbstractBaseModel):
    CENTER_TYPE_CHOICES = (
            ('1', _('Buddhist Center')),
            ('2', _('Buddhist Group')),
            ('3', _('Buddhist Retreat')),            
            ('7', _('Buddhist Center & Retreat')),            
            ('16', _('Buddhist Group & Retreat')),            
            )
    _center_type_choices = {}
    for choice in CENTER_TYPE_CHOICES:
        _center_type_choices[choice[0]] = choice[1]

    def center_type_desc(self):
        return self._center_type_choices.get(self.center_type, '')

    name = models.CharField(_("name"), blank=True, max_length=255)
    country = models.ForeignKey(Country, verbose_name=_("country"), blank=True, null=True, limit_choices_to={'active': True})
    email = models.EmailField(_('e-mail address'), blank=True)
    homepage = models.URLField(_("homepage"), blank=True,)
    notes = models.TextField(_('notes'), blank=True, max_length=255)
    center_type = models.CharField(_('center type'), max_length=2, choices=CENTER_TYPE_CHOICES, db_index=True)    
    centerid = models.IntegerField(blank=True, null=True)
    founded = models.DateField(_("founded"), blank=True, null=True)
    latitude = models.DecimalField(_("latitude"), max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(_("longitude"), max_digits=9, decimal_places=6, blank=True, null=True)
    is_active = models.BooleanField(_('active'), default=True,
        help_text=_('Designates whether this buddhist center should be treated as '
                    'active. Unselect this instead of deleting buddhist center.'))
    is_private = models.BooleanField(_("private"), 
        help_text=_('Designates whether this buddhist center data should be treated as private and '
                    'only a telephone number should be displayed on public sites.'), default=False)
    admin_region = models.ForeignKey(AdminRegion, blank=True, null=True)
    #history = HistoricalRecords()
    
    class Meta:
        ordering = ['name']
        verbose_name = _('Buddhist Center')
        verbose_name_plural = _('Buddhist Centers')
    
    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.country.iso2_code)

    @models.permalink
    def get_absolute_url(self):
        return ('organisations:buddhistcenter_detail', (), {'slug': self.uuid, })
     
    def google_maps_link(self):
        if self.latitude and self.longitude:
            return u'<a href="http://maps.google.de/maps?q=%f,+%f&iwloc=A">%s</a>' % (self.latitude, self.longitude, 'google maps link')
        else:
            return ''
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
            ('post', _('Post address')),
            ('meditation', _('Meditation')),
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
        #unique_together = (("organisation", "phone_type"),)
        pass

    @classmethod
    def ensure_single_primary(cls, organisation):
        ensure_single_primary(organisation.organisationphonenumber_set.all())


# TODO: user adress, phone numbet ? 
"""
@receiver(signals.pre_delete, sender=OrganisationAddress)
def pre_delete_address(sender, **kwargs):
    address = kwargs.get('instance')
    if address.primary:
        try:
            # if we delete the primary address we
            # make the first address we find the primary address
            _address = address.organisation.organisationaddress_set.exclude(id=address.id)[0]
            _address.primary = True
            _address.save() 
        except IndexError:
            # buddhistcenter without other addresses (standard use case)
            pass
"""
