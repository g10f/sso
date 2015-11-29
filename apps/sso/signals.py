import django.dispatch

default_roles = django.dispatch.Signal(providing_args=["user", "app_roles", "role_profiles"])
update_or_create_organisation_account = django.dispatch.Signal(providing_args=["organisation", "old_email_value", "new_email_value"])