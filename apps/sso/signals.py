import django.dispatch

# you can modify the app_roles and role_profiles
default_roles = django.dispatch.Signal(providing_args=["user", "app_roles", "role_profiles"])

# an organisation was created or updated, you can do whatever action you like
update_or_create_organisation_account = django.dispatch.Signal(providing_args=["organisation", "old_email_value", "new_email_value", "user"])

# the validation of a user was extended
extend_user_validity = django.dispatch.Signal(providing_args=["user"])

# a user m2m field was updated in the frontend application
user_m2m_field_updated = django.dispatch.Signal(providing_args=["user", "attribute_name", "delete_pk_list", "add_pk_list"])