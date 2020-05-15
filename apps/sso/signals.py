import django.dispatch

# you can modify the admins
user_admins = django.dispatch.Signal(providing_args=["organisations", "admins"])

# you can modify the app_roles and role_profiles
default_roles = django.dispatch.Signal(providing_args=["user", "app_roles", "role_profiles"])

# an organisation was created or updated, you can do whatever action you like
update_or_create_organisation_account = django.dispatch.Signal(providing_args=["organisation", "old_email_value", "new_email_value", "user"])

# a user m2m field was updated in the frontend application
user_m2m_field_updated = django.dispatch.Signal(providing_args=["user", "attribute_name", "delete_pk_list", "add_pk_list"])

# a user want's to change the organisation
user_organisation_change_request = django.dispatch.Signal(providing_args=["organisation_change"])

# a user has finished registration with the email validation
user_registration_completed = django.dispatch.Signal(providing_args=["user_registration"])

# a user requests extended access
user_access_request = django.dispatch.Signal(providing_args=["access_request"])
