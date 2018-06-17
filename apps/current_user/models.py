from django.db import models
from django.conf import settings

from . import registration


class CurrentUserField(models.ForeignKey):
    def __init__(self, created_by_only=False, **kwargs):
        # remove kwargs for migration, because we have fixed values below
        # and otherwise get multiple keywords error
        kwargs.pop('null', None)
        kwargs.pop('to', None)
        self.created_by_only = created_by_only
        super().__init__(settings.AUTH_USER_MODEL, null=True, **kwargs)

    def contribute_to_class(self, cls, name):
        super().contribute_to_class(cls, name)
        registry = registration.FieldRegistry()
        registry.add_field(cls, self)
