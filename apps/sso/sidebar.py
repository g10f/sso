from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from sso.auth.utils import get_device_classes
from django.apps import apps


def sidebar(request):
    def set_active_item():
        for item in sidebar_nav:
            if 'submenue' in item:
                for subitem in item['submenue']:
                    if subitem['url'] == request.path:
                        subitem['active'] = True
                        item['active'] = True
                        item['expanded'] = True
                        return

    def append_submenue(menue):
        if len(menue['submenue']) == 1:
            sidebar_nav.append(menue['submenue'][0])
        elif len(menue['submenue']) > 1:
            sidebar_nav.append(menue)

    user = request.user
    # Main menue
    sidebar_nav = []
    if not user.is_authenticated:
        return sidebar_nav

    if user.is_staff:
        sidebar_nav.append({'url': reverse('admin:index'), 'icon': 'wrench', 'title': _('Administration')})

    # E-Mail submenue
    #################
    email_list = {'url': reverse('emails:groupemail_list'), 'icon': 'list-task', 'title': _('Emails')}
    email_create = {'url': reverse('emails:groupemail_create'), 'icon': 'plus', 'title': _('Add Email')}

    email_submenue = {'name': 'emails', 'icon': 'envelope', 'title': _('E-Mails'), 'submenue': []}
    if settings.SSO_ORGANISATION_EMAIL_MANAGEMENT and user.is_groupemail_admin:
        email_submenue['submenue'].append(email_list)
    if settings.SSO_ORGANISATION_EMAIL_MANAGEMENT and user.has_perm('emails.add_groupemail'):
        email_submenue['submenue'].append(email_create)

    # Organisations submenue
    ########################
    country_list = {'url': reverse('organisations:organisationcountry_list'), 'icon': 'list-task', 'title': _('Countries')}
    region_list = {'url': reverse('organisations:adminregion_list'), 'icon': 'list-task', 'title': _('Regions')}
    org_list = {'url': reverse('organisations:organisation_list'), 'icon': 'list-task', 'title': _('Organisations')}
    country_create = {'url': reverse('organisations:organisationcountry_create'), 'icon': 'plus', 'title': _('Add Country')}
    region_create = {'url': reverse('organisations:adminregion_create'), 'icon': 'plus', 'title': _('Add Region')}
    org_create = {'url': reverse('organisations:organisation_create'), 'icon': 'plus', 'title': _('Add Organisation')}
    my_org = {'url': reverse('organisations:my_organisation_detail'), 'icon': 'house', 'title': _('My Organisation')}
    orgs_submenue = {'name': 'organisations', 'icon': 'house', 'title': _('Organisations'), 'submenue': []}
    if user.organisations.exists:
        orgs_submenue['submenue'].append(my_org)
    if settings.SSO_COUNTRY_MANAGEMENT and user.is_authenticated:
        orgs_submenue['submenue'].append(country_list)
    if settings.SSO_REGION_MANAGEMENT and user.has_perm('organisations.change_adminregion'):
        orgs_submenue['submenue'].append(region_list)
    if user.is_authenticated:
        orgs_submenue['submenue'].append(org_list)
    if settings.SSO_COUNTRY_MANAGEMENT and user.has_perm('organisations.add_organisationcountry') and user.get_administrable_associations():
        orgs_submenue['submenue'].append(country_create)
    if settings.SSO_REGION_MANAGEMENT and user.has_perm('organisations.add_adminregion'):
        orgs_submenue['submenue'].append(region_create)
    if user.has_perm('organisations.add_organisation'):
        orgs_submenue['submenue'].append(org_create)

    # Accounts submenue
    ###################
    no_reg = user.get_count_of_registrationprofiles()
    no_orgchg = user.get_count_of_organisationchanges()
    no_ext = user.get_count_of_extend_access()
    registration_list = {'url': reverse('registration:user_registration_list'), 'icon': 'people', 'title': _('Registrations'), 'badge': no_reg}
    user_list = {'url': reverse('accounts:user_list'), 'icon': 'people', 'title': _('Users')}
    roles_list = {'url': reverse('accounts:app_admin_user_list'), 'icon': 'people', 'title': _('Roles')}
    org_changes_list = {'url': reverse('accounts:organisationchange_list'), 'icon': 'arrow-left-right', 'title': _('Organisation Changes'), 'badge': no_orgchg}
    access_req_list = {'url': reverse('access_requests:extend_access_list'), 'icon': 'folder-plus', 'title': _('Access Requests'), 'badge': no_ext}
    user_create = {'url': reverse('accounts:add_user'), 'icon': 'person-plus', 'title': _('Add User')}

    accounts_submenue = {'name': 'accounts', 'icon': 'people', 'title': _('Accounts'), 'submenue': []}
    if (settings.REGISTRATION.get('OPEN', True) or no_reg > 0) and user.has_perm('registration.change_registrationprofile'):
        accounts_submenue['submenue'].append(registration_list)
    if user.is_user_admin:
        accounts_submenue['submenue'].append(user_list)
    if user.is_app_admin():
        accounts_submenue['submenue'].append(roles_list)
    if user.has_perm('accounts.change_user'):
        accounts_submenue['submenue'].append(org_changes_list)
    if apps.is_installed('sso.access_requests') and user.has_perm('accounts.change_user'):
        accounts_submenue['submenue'].append(access_req_list)
    if user.has_perms(['accounts.change_user', 'accounts.add_user']):
        accounts_submenue['submenue'].append(user_create)

    # my account items
    ##################
    my_account = {'url': reverse('accounts:profile'), 'icon': 'person-circle', 'title': _('My Account')}
    my_emails = {'url': reverse('accounts:emails'), 'icon': 'envelope', 'title': _('My Email Addresses')}
    my_password = {'url': reverse('accounts:password_change'), 'icon': 'lock', 'title': _('Change password')}
    my_security = {'url': reverse('auth:mfa-detail'), 'icon': 'shield-lock', 'title': _('Security')}

    my_data_submenue = {'name': 'my-data', 'icon': 'person', 'title': _('Personal Data'), 'submenue': [my_account, my_password]}

    if not user.is_center:
        my_data_submenue['submenue'].append(my_emails)
    if get_device_classes() and (not settings.SSO_ADMIN_ONLY_2F or user.is_user_admin or user.is_organisation_admin or user.is_staff):
        my_data_submenue['submenue'].append(my_security)

    append_submenue(email_submenue)
    append_submenue(orgs_submenue)
    append_submenue(accounts_submenue)
    append_submenue(my_data_submenue)

    set_active_item()

    return sidebar_nav
