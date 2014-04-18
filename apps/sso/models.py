# -*- coding: utf-8 -*-
from django.db import models
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import pgettext_lazy

from l10n.models import Country, AdminArea
from smart_selects.db_fields import ChainedForeignKey
from sso.fields import UUIDField

class AbstractBaseModelManager(models.Manager):
    def get_by_natural_key(self, uuid):
        return self.get(uuid=uuid)


class AbstractBaseModel(models.Model):
    uuid = UUIDField(version=4, unique=True, editable=True)
    last_modified = models.DateTimeField(_('last modified'), auto_now=True, default=now)
    objects = AbstractBaseModelManager()
    
    class Meta:
        abstract = True
        #ordering = ['name']
        get_latest_by = 'last_modified'

    def natural_key(self):
        return (self.uuid, )


class AddressMixin(models.Model):
    """
    Address information
    see i.e. http://tools.ietf.org/html/draft-ietf-scim-core-schema-03 or http://schema.org/PostalAddress
    """
    ADDRESSTYPE_CHOICES = (
            ('home', pgettext_lazy('address', 'Home')),
            ('work', _('Business')),
            ('other', _('Other')),            
            )
    _addresstype_choices = {}
    for choice in ADDRESSTYPE_CHOICES:
        _addresstype_choices[choice[0]] = choice[1]
    
    def get_addresstype_desc(self):
        return self._addresstype_choices.get(self.address_type)
        
    address_type = models.CharField(_("address type"), choices=ADDRESSTYPE_CHOICES, max_length=20)
    addressee = models.CharField(_("addressee"), max_length=80)
    street_address = models.TextField(_('street address'), blank=True, help_text=_('Full street address, with house number, street name, P.O. box, and extended street address information.'), max_length=512)
    city = models.CharField(_("city"), max_length=100)  # , help_text=_('City or locality')
    postal_code = models.CharField(_("postal code"), max_length=30, blank=True)  # , help_text=_('Zipcode or postal code') 
    country = models.ForeignKey(Country, verbose_name=_("country"), limit_choices_to={'active': True})
    state = ChainedForeignKey(AdminArea, chained_field='country', chained_model_field="country", verbose_name=_("State"), 
                                                      help_text=_('State or region'), blank=True, null=True)    
    primary = models.BooleanField(_("primary"), default=False)
    #history = HistoricalRecords()
    
    #formatted  : formatted Address for mail http://tools.ietf.org/html/draft-ietf-scim-core-schema-03
    
    class Meta:
        abstract = True
        verbose_name = _("address")
        verbose_name_plural = _("addresses")
        ordering = ['addressee']

    def __unicode__(self):
        return u"%s" % (self.addressee)
    

class PhoneNumberMixin(models.Model): 
    PHONE_CHOICES = [
        ('home', pgettext_lazy('phone number', 'Home')),  # with translation context 
        ('mobile', _('Mobile')),
        ('work', _('Business')),
        ('fax', _('Fax')),
        ('pager', _('Pager')),
        ('other', _('Other')),
    ]
    _phone_choices = {}
    for choice in PHONE_CHOICES:
        _phone_choices[choice[0]] = choice[1]
   
    phone_type = models.CharField(_("phone type"), help_text=_('Mobile, home, office, etc.'), choices=PHONE_CHOICES, max_length=20)
    phone = models.CharField(_("phone number"), max_length=30,)
    primary = models.BooleanField(_("primary"), default=False)
    #history = HistoricalRecords()

    class Meta:
        abstract = True
        ordering = ['-primary']
        verbose_name = _("phone number")
        verbose_name_plural = _("phone numbers")

    def __unicode__(self):
        return u'%s: %s' % (self.phone_type_desc(), self.phone)
    
    def phone_type_desc(self):
        if self.phone_type:
            return self._phone_choices[self.phone_type]
        else:
            return ""
