import django.dispatch

# you can modify the app_roles and role_profiles
default_roles = django.dispatch.Signal(providing_args=["user", "app_roles", "role_profiles"])

# an organisation was created or updated, you can do whatever action you like
update_or_create_organisation_account = django.dispatch.Signal(providing_args=["organisation", "old_email_value", "new_email_value"])

# the validation of a user was extended
extend_user_validity = django.dispatch.Signal(providing_args=["user"])

# the validation of a user was extended
extend_user_validity = django.dispatch.Signal(providing_args=["user"])