from django.apps import apps
from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


def sidebar(request):
    def set_active_item(menu):
        # iterate menu and find the active menu item
        # if the item is inside a submenu, the submenu  is expanded and marked active
        for item in menu:
            if 'submenu' in item:
                if set_active_item(item['submenu']):
                    item['active'] = True
                    item['expanded'] = True
                    return True
            elif request.resolver_match.view_name in item['view_names']:
                item['active'] = True
                return True

    def reverse_url(menu):
        # reverse the 1. item in from view_names and add an 'url' attribute for creating
        # the link in the menu. Could also be done in the view
        for item in menu:
            if 'submenu' in item:
                reverse_url(item['submenu'])
            else:
                item['url'] = reverse(item['view_names'][0])

    def append_submenu(menu):
        if len(menu['submenu']) == 1:
            sidebar_nav.append(menu['submenu'][0])
        elif len(menu['submenu']) > 1:
            sidebar_nav.append(menu)

    user = request.user
    # Main menu
    sidebar_nav = []

    # for 404 response request.resolver_match is None
    if not user.is_authenticated or request.resolver_match is None:
        return sidebar_nav

    if user.is_staff:
        sidebar_nav.append({'view_names': ['admin:index'], 'icon': 'wrench', 'title': _('Administration')})

    # Application submenu
    ######################
    application_list = {'view_names': ['accounts:application_list', 'accounts:application_update', 'accounts:application_detail', 'accounts:client_update', 'accounts:client_add'],
                        'icon': 'list-task', 'title': _('Applications')}
    application_create = {'view_names': ['accounts:application_add'], 'icon': 'plus', 'title': _('Add Application')}

    application_submenu = {'name': 'applications', 'icon': 'grid-3x3-gap-fill', 'title': _('Applications'), 'submenu': []}
    if user.has_perm('accounts.view_application'):
        application_submenu['submenu'].append(application_list)
    if user.has_perm('accounts.add_application'):
        application_submenu['submenu'].append(application_create)

    # E-Mail submenu
    #################
    email_list = {'view_names': ['emails:groupemail_list', 'emails:groupemail_detail', 'emails:groupemail_update', 'emails:emailforward_create',
                                 'emails:emailforward_confirm_delete'],
                  'icon': 'list-task', 'title': _('Emails')}
    email_create = {'view_names': ['emails:groupemail_create'], 'icon': 'plus', 'title': _('Add Email')}

    email_submenu = {'name': 'emails', 'icon': 'envelope', 'title': _('E-Mails'), 'submenu': []}
    if settings.SSO_ORGANISATION_EMAIL_MANAGEMENT and user.is_groupemail_admin:
        email_submenu['submenu'].append(email_list)
    if settings.SSO_ORGANISATION_EMAIL_MANAGEMENT and user.has_perm('emails.add_groupemail'):
        email_submenu['submenu'].append(email_create)

    # Organisations submenu
    ########################
    country_list = {'view_names': ['organisations:organisationcountry_list', 'organisations:organisationcountry_update',
                                   'organisations:organisationcountry_detail'], 'icon': 'list-task', 'title': _('Countries')}
    region_list = {'view_names': ['organisations:adminregion_list', 'organisations:adminregion_update', 'organisations:adminregion_detail'],
                   'icon': 'list-task', 'title': _('Regions')}
    org_list = {'view_names': ['organisations:organisation_list', 'organisations:organisation_update', 'organisations:organisation_delete',
                               'organisations:organisation_detail', 'organisations:organisation_picture_update'],
                'icon': 'list-task', 'title': _('Organisations')}
    country_create = {'view_names': ['organisations:organisationcountry_create'], 'icon': 'plus', 'title': _('Add Country')}
    region_create = {'view_names': ['organisations:adminregion_create'], 'icon': 'plus', 'title': _('Add Region')}
    org_create = {'view_names': ['organisations:organisation_create'], 'icon': 'plus', 'title': _('Add Organisation')}
    my_org = {'view_names': ['organisations:my_organisation_detail'], 'icon': 'house', 'title': _('My Organisation')}
    orgs_submenu = {'name': 'organisations', 'icon': 'house', 'title': _('Organisations'), 'submenu': []}
    if user.organisations.exists:
        orgs_submenu['submenu'].append(my_org)
    if settings.SSO_COUNTRY_MANAGEMENT and user.is_authenticated:
        orgs_submenu['submenu'].append(country_list)
    if settings.SSO_REGION_MANAGEMENT and user.has_perm('organisations.change_adminregion'):
        orgs_submenu['submenu'].append(region_list)
    if user.is_authenticated:
        orgs_submenu['submenu'].append(org_list)
    if settings.SSO_COUNTRY_MANAGEMENT and user.has_perm('organisations.add_organisationcountry') and user.get_administrable_associations():
        orgs_submenu['submenu'].append(country_create)
    if settings.SSO_REGION_MANAGEMENT and user.has_perm('organisations.add_adminregion'):
        orgs_submenu['submenu'].append(region_create)
    if user.has_perm('organisations.add_organisation'):
        orgs_submenu['submenu'].append(org_create)

    # Accounts submenu
    ###################
    no_reg = user.get_count_of_registrationprofiles()
    no_orgchg = user.get_count_of_organisationchanges()
    no_ext = user.get_count_of_extend_access()
    registration_list = {'view_names': ['registration:user_registration_list', 'registration:update_user_registration',
                                        'registration:delete_user_registration', 'registration:process_user_registration'],
                         'icon': 'people', 'title': _('Registrations'), 'badge': no_reg}
    user_list = {'view_names': ['accounts:user_list', 'accounts:update_user', 'accounts:delete_user', 'accounts:organisation_detail',
                                'accounts:organisation_picture_update'], 'icon': 'people', 'title': _('Users')}
    roles_list = {'view_names': ['accounts:app_admin_user_list', 'accounts:app_admin_update_user'], 'icon': 'people', 'title': _('Roles')}
    org_changes_list = {'view_names': ['accounts:organisationchange_list', 'accounts:organisationchange_accept'], 'icon': 'arrow-left-right',
                        'title': _('Organisation Changes'), 'badge': no_orgchg}
    access_req_list = {'view_names': ['access_requests:extend_access_list', 'access_requests:extend_access_accept', 'access_requests:process_access_request'],
                       'icon': 'folder-plus', 'title': _('Access Requests'), 'badge': no_ext}
    user_create = {'view_names': ['accounts:add_user'], 'icon': 'person-plus', 'title': _('Add User')}

    accounts_submenu = {'name': 'accounts', 'icon': 'people', 'title': _('Accounts'), 'submenu': []}
    if (settings.REGISTRATION.get('OPEN', True) or no_reg > 0) and user.has_perm('registration.change_registrationprofile'):
        accounts_submenu['submenu'].append(registration_list)
    if user.is_user_admin:
        accounts_submenu['submenu'].append(user_list)
    if user.is_app_user_admin():
        accounts_submenu['submenu'].append(roles_list)
    if user.has_perm('accounts.change_user'):
        accounts_submenu['submenu'].append(org_changes_list)
    if apps.is_installed('sso.access_requests') and user.has_perm('accounts.change_user'):
        accounts_submenu['submenu'].append(access_req_list)
    if user.has_perms(['accounts.change_user', 'accounts.add_user']):
        accounts_submenu['submenu'].append(user_create)

    # my account items
    ##################
    my_account = {'view_names': ['accounts:profile', 'accounts:organisationchange_me', 'accounts:organisationchange_detail'], 'icon': 'person-circle',
                  'title': _('My Account')}
    my_emails = {'view_names': ['accounts:emails'], 'icon': 'envelope', 'title': _('My Email Addresses')}
    my_password = {'view_names': ['accounts:password_change'], 'icon': 'lock', 'title': _('Change password')}
    my_security = {'view_names': ['auth:mfa-detail', 'auth:mfa-update', 'auth:totp_add_device', 'auth:u2f_add_device'],
                   'icon': 'shield-lock', 'title': _('Security')}

    my_data_submenu = {'name': 'my-data', 'icon': 'person', 'title': _('Personal Data'), 'submenu': [my_account, my_password]}

    if not user.is_center:
        my_data_submenu['submenu'].append(my_emails)
    if user.is_mfa_enabled:
        my_data_submenu['submenu'].append(my_security)

    if user.has_perm('accounts.view_application'):
        append_submenu(application_submenu)
    append_submenu(email_submenu)
    append_submenu(orgs_submenu)
    append_submenu(accounts_submenu)
    append_submenu(my_data_submenu)

    set_active_item(sidebar_nav)
    reverse_url(sidebar_nav)

    return sidebar_nav
