# -*- coding: utf-8 -*-
from django.db import models
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from django.forms.models import model_to_dict

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
        # ordering = ['name']
        get_latest_by = 'last_modified'

    def natural_key(self):
        return (self.uuid, )


def ensure_single_primary(queryset):
    """
    ensure that at most one item of the queryset is primary
    """
    primary_items = queryset.filter(primary=True)
    if (primary_items.count() > 1):
        for item in primary_items[1:]:
            item.primary = False
            item.save()
    elif primary_items.count() == 0:
        item = queryset.first()
        if item:
            item.primary = True
            item.save()


class AddressMixin(models.Model):
    """
    Address information
    see i.e. http://tools.ietf.org/html/draft-ietf-scim-core-schema-03 or http://schema.org/PostalAddress
    """
    addressee = models.CharField(_("addressee"), max_length=80)
    street_address = models.TextField(_('street address'), blank=True, help_text=_('Full street address, with house number, street name, P.O. box, and extended street address information.'), max_length=512)
    city = models.CharField(_("city"), max_length=100)  # , help_text=_('City or locality')
    postal_code = models.CharField(_("postal code"), max_length=30, blank=True)  # , help_text=_('Zipcode or postal code') 
    country = models.ForeignKey(Country, verbose_name=_("country"), limit_choices_to={'active': True})
    state = ChainedForeignKey(AdminArea, chained_field='country', chained_model_field="country", verbose_name=_("State"), 
                              help_text=_('State or region'), blank=True, null=True)    
    primary = models.BooleanField(_("primary"), default=False)
    # history = HistoricalRecords()
    
    # formatted  : formatted Address for mail http://tools.ietf.org/html/draft-ietf-scim-core-schema-03
    
    class Meta:
        abstract = True
        verbose_name = _("address")
        verbose_name_plural = _("addresses")
        ordering = ['addressee']

    def __unicode__(self):
        return u"%s" % (self.addressee)
    

class PhoneNumberMixin(models.Model): 
    phone = models.CharField(_("phone number"), max_length=30,)
    primary = models.BooleanField(_("primary"), default=False)
    # history = HistoricalRecords()

    class Meta:
        abstract = True
        ordering = ['-primary']
        verbose_name = _("phone number")
        verbose_name_plural = _("phone numbers")

    def __unicode__(self):
        return u'%s: %s' % (self.get_phone_type_display(), self.phone)
    

def update_object_from_dict(destination, source_dict, key_mapping={}):
    """
    check if the values in the destination object differ from
    the values in the source_dict and update if needed
    
    key_mapping can be a simple mapping of key names or
    a mapping of key names to a tuple with a key name and a transformation
    for the value, 
    for example {'key': ('new_key', lambda x : x + 2), ..}
    """
    field_names = [f.name for f in destination._meta.fields]
    new_object = True if destination.pk is None else False
    updated = False
            
    for key in source_dict:
        field_name = key
        transformation = None

        if key in key_mapping:
            field_name = key_mapping[key]            
            if isinstance(key_mapping[key], tuple):
                (field_name, transformation) = key_mapping[key]
            else:
                field_name = key_mapping[key]
             
        if field_name in field_names:
            if transformation is None:
                new_value = source_dict[key]
            else:
                new_value = transformation(source_dict[key])
                
            if new_object:
                setattr(destination, field_name, new_value)
            else:
                old_value = getattr(destination, field_name)                
                if old_value != new_value:
                    setattr(destination, field_name, new_value)
                    updated = True
    if updated or new_object:
        destination.save()


def filter_dict_from_kls(destination, source_dict, prefix=''):
    field_names = [f.name for f in destination._meta.fields]
    filtered_dict = {}    
    for field_name in field_names:
        key = '%s%s' % (prefix, field_name)
        if key in source_dict:
            filtered_dict[field_name] = source_dict[key]
    return filtered_dict
    

def update_object_from_object(destination, source, exclude=['id']):
    source_dict = model_to_dict(source, exclude=exclude)
    update_object_from_dict(destination, source_dict)
