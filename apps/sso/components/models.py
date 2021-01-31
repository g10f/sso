import logging

from django.db import models
from django.utils.translation import gettext_lazy as _
from sso.models import AbstractBaseModel

logger = logging.getLogger(__name__)


class Component(AbstractBaseModel):
    name = models.CharField(_('name'), db_index=True, max_length=255)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        get_latest_by = "created_at"

    def __str__(self):
        return f"{self.name}.{self.uuid.hex}"


class ComponentConfig(AbstractBaseModel):
    component = models.ForeignKey(Component, on_delete=models.CASCADE)
    name = models.CharField(_('name'), max_length=255)
    value = models.TextField(_('value'), max_length=4000)

    class Meta:
        unique_together = (("component", "name"),)
        get_latest_by = "-component__created_at"
        ordering = ['-component__created_at']

    def __str__(self):
        return f"{self.name}"
