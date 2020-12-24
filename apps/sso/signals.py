import django.dispatch

# you can modify the admins
user_admins = django.dispatch.Signal()

# you can modify the app_roles and role_profiles
default_roles = django.dispatch.Signal()

# an organisation was created or updated, you can do whatever action you like
update_or_create_organisation_account = django.dispatch.Signal()

# the validation of a user was extended
extend_user_validity = django.dispatch.Signal()

# a user m2m field was updated in the frontend application
user_m2m_field_updated = django.dispatch.Signal()

# a user want's to change the organisation
user_organisation_change_request = django.dispatch.Signal()

# a user has finished registration with the email validation
user_registration_completed = django.dispatch.Signal()

# a user requests extended access
user_access_request = django.dispatch.Signal()
