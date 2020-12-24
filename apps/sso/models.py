import logging
import os
import re
import uuid
from io import BytesIO
from mimetypes import guess_extension

from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import fields
from django.forms import forms
from django.forms.models import model_to_dict
from django.utils.crypto import get_random_string
from django.utils.text import get_valid_filename
from django.utils.translation import gettext_lazy as _

from l10n.models import Country, AdminArea

logger = logging.getLogger(__name__)


def get_filename(filename):
    return os.path.normpath(get_valid_filename(os.path.basename(filename)))


def transpose_image(picture):
    # copied from ImageOps.exif_transpose but avoiding to create a copy if not
    # transposed
    # argument is a UploadedFile Object instead of Image
    # exif is only in TIFF and JPEG available
    if picture.image.format not in ['JPEG', 'TIFF']:
        return picture

    exif = picture.image.getexif()
    orientation = exif.get(0x0112)
    method = {
        2: Image.FLIP_LEFT_RIGHT,
        3: Image.ROTATE_180,
        4: Image.FLIP_TOP_BOTTOM,
        5: Image.TRANSPOSE,
        6: Image.ROTATE_270,
        7: Image.TRANSVERSE,
        8: Image.ROTATE_90,
    }.get(orientation)
    if method is not None:
        image = Image.open(picture.file)
        transposed_image = image.transpose(method)
        del exif[0x0112]
        transposed_image.info["exif"] = exif.tobytes()
        # create a new UploadedFile
        f = BytesIO()
        transposed_image.save(f, image.format)
        picture = InMemoryUploadedFile(
            file=f,
            field_name=picture.field_name,
            name=picture.name,
            content_type=picture.content_type,
            size=f.tell(),
            charset=picture.charset,
            content_type_extra=picture.content_type_extra
        )
        picture.image = transposed_image
        return picture

    return picture


def clean_picture(picture, max_upload_size):
    from django.template.defaultfilters import filesizeformat
    if picture and hasattr(picture, 'content_type'):
        base_content_type = picture.content_type.split('/')[0]
        if base_content_type in ['image']:
            if picture.size > max_upload_size:
                raise forms.ValidationError(
                    _('Please keep filesize under %(filesize)s. Current filesize %(current_filesize)s') %
                    {'filesize': filesizeformat(max_upload_size),
                     'current_filesize': filesizeformat(picture.size)})
            # mimetypes.guess_extension return jpe which is quite uncommon for jpeg
            if picture.content_type == 'image/jpeg':
                file_ext = '.jpg'
            else:
                file_ext = guess_extension(picture.content_type)
            picture.name = "%s%s" % (
                get_random_string(7, allowed_chars='abcdefghijklmnopqrstuvwxyz0123456789'), file_ext)
            try:
                picture = transpose_image(picture)
            except Exception as e:
                logger.warning("Transpose image failed: ", e)
        else:
            raise forms.ValidationError(_('File type is not supported'))
    return picture


class CaseInsensitiveEmailField(fields.EmailField):

    def db_type(self, connection):
        return "citext"


class AbstractBaseModelManager(models.Manager):
    def get_by_natural_key(self, uuid):
        return self.get(uuid=uuid)


class AbstractBaseModel(models.Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=True)
    last_modified = models.DateTimeField(_('last modified'), auto_now=True)
    objects = AbstractBaseModelManager()

    class Meta:
        abstract = True
        # ordering = ['name']
        get_latest_by = 'last_modified'

    def natural_key(self):
        return self.uuid,


def ensure_single_primary(queryset):
    """
    ensure that at most one item of the queryset is primary
    """
    primary_items = queryset.filter(primary=True)
    if primary_items.count() > 1:
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
    street_address = models.TextField(_('street address'), blank=True,
                                      help_text=_('Full street address, with house number, street name, P.O. box, and '
                                                  'extended street address information.'), max_length=512)
    city = models.CharField(_("city"), max_length=100)  # , help_text=_('City or locality')
    city_native = models.CharField(_("city in native language"), max_length=100, blank=True)
    postal_code = models.CharField(_("postal code"), max_length=30, blank=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, verbose_name=_("country"),
                                limit_choices_to={'active': True})
    region = models.CharField(_("region"), help_text=_('State or region'), blank=True, max_length=100)
    primary = models.BooleanField(_("primary"), default=False)

    # formatted  : formatted Address for mail http://tools.ietf.org/html/draft-ietf-scim-core-schema-03

    class Meta:
        abstract = True
        verbose_name = _("address")
        verbose_name_plural = _("addresses")
        ordering = ['addressee']

    def __str__(self):
        return self.addressee


phone_re = re.compile(
    r'^\+\d{1,3}' + r'((-?\d+)|(\s?\(\d+\)\s?)|\s?\d+){1,9}$'
)
validate_phone = RegexValidator(phone_re, _("Enter a valid phone number i.e. +49 (531) 123456"), 'invalid')


class PhoneNumberMixin(models.Model):
    phone = models.CharField(_("phone number"), max_length=30, validators=[validate_phone])
    primary = models.BooleanField(_("primary"), default=False)

    class Meta:
        abstract = True
        ordering = ['-primary']
        verbose_name = _("phone number")
        verbose_name_plural = _("phone numbers")

    def __str__(self):
        return self.phone


def update_object_from_dict(destination, source_dict, key_mapping=None):
    """
    check if the values in the destination object differ from
    the values in the source_dict and update if needed

    key_mapping can be a simple mapping of key names or
    a mapping of key names to a tuple with a key name and a transformation
    for the value,
    for example {'key': ('new_key', lambda x : x + 2), ..}
    """
    if not key_mapping: key_mapping = {}
    field_names = [f.name for f in destination._meta.fields]
    new_object = True if destination.pk is None else False
    updated = False

    for key in source_dict:
        field_name = key
        transformation = None

        if key in key_mapping:
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


def map_dict2dict(mapping, source_dict, with_defaults=False):
    new_dict = {}
    for key, value in mapping.items():
        if key in source_dict:
            if isinstance(value, dict):
                new_key = value['name']
                parser = value.get('parser', None)
                if parser is not None:
                    try:
                        new_value = parser(source_dict[key])
                    except Exception as e:
                        logger.exception('could not parse value: %s' % source_dict[key])
                        raise e
                else:
                    new_value = source_dict[key]

                validate = value.get('validate', None)
                if validate is not None:
                    if not validate(new_value):
                        raise ValueError("\"%s\" is not valid for %s" % (new_value, new_key))
            else:
                new_key = value
                new_value = source_dict[key]

            new_dict[new_key] = new_value
        elif with_defaults:
            # use default if no value in source_dict
            try:
                if isinstance(value, dict):
                    new_key = value['name']
                    new_value = value['default']
                    new_dict[new_key] = new_value
            except KeyError:
                pass

    return new_dict


def update_object_from_object(destination, source, exclude=None):
    if not exclude: exclude = ['id']
    source_dict = model_to_dict(source, exclude=exclude)
    update_object_from_dict(destination, source_dict)
