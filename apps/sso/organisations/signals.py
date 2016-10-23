from django.db.models.signals import pre_save, post_delete
from django.utils.text import slugify

from django.dispatch.dispatcher import receiver
from sso.organisations.models import OrganisationAddress, OrganisationPhoneNumber, Organisation, default_unique_slug_generator, deactivate_center_account, AdminRegion
from sso.utils.loaddata import disable_for_loaddata


@receiver(post_delete, sender=Organisation)
@disable_for_loaddata
def post_delete_center_account(sender, instance, **kwargs):
    if instance.email:
        deactivate_center_account(instance.email)


@receiver(post_delete, sender=OrganisationPhoneNumber)
@disable_for_loaddata
def post_delete_phone(sender, instance, **kwargs):
    if instance:
        instance.organisation.save(update_fields=['last_modified'])


@receiver(post_delete, sender=OrganisationAddress)
@disable_for_loaddata
def post_delete_address(sender, instance, **kwargs):
    if instance:
        instance.organisation.save(update_fields=['last_modified'])


@receiver(pre_save)
def create_slug(sender, instance, raw, **kwargs):
    list_of_models = ('AdminRegion', 'Organisation')
    if sender.__name__ in list_of_models:  # this is the dynamic part you want
        if instance.slug == "":
            if raw:
                instance.slug = slugify(instance.name)
            else:
                instance.slug = default_unique_slug_generator(slugify(instance.name), sender, instance)
