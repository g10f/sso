from django.contrib.auth.base_user import BaseUserManager
from django.contrib.gis import forms
from django.contrib.gis.forms import GeometryField
from django.contrib.gis.geos import GEOSGeometry, GEOSException
from django.forms import fields
from django.utils.translation import gettext_lazy as _
from sso.forms import bootstrap


class EmailFieldLower(fields.EmailField):
    widget = bootstrap.EmailInput(attrs={'size': 50})

    def to_python(self, value):
        email = super().to_python(value).rstrip().lstrip()
        return BaseUserManager.normalize_email(email)

    def __init__(self, max_length=None, min_length=None, *args, **kwargs):
        if 'label' not in kwargs:
            kwargs['label'] = _('email address')
        super().__init__(max_length=max_length, min_length=min_length, *args, **kwargs)


class PointField(GeometryField):
    geom_type = 'POINT'

    def to_python(self, value):
        """Transform the value to a Geometry object."""
        if value in self.empty_values:
            return None

        if not isinstance(value, GEOSGeometry):
            try:
                value = GEOSGeometry(value)
            except (GEOSException, ValueError, TypeError):
                raise forms.ValidationError(self.error_messages['invalid_geom'], code='invalid_geom')
            # in django 2.0 wrong srid is set when using geojson
            value.srid = self.widget.map_srid

        return value
