from django.core.management.base import NoArgsCommand
from sso.accounts.models import Application, Role, ApplicationRole, User

class Command(NoArgsCommand):
    help = '...'  # @ReservedAssignment

    def handle_noargs(self, **options):
        cee_app_roles = []
        
        eu_app_roles = []
        
        user_role = Role.objects.get_or_create(name='User')[0]
        guest_role = Role.objects.get_or_create(name='Guest')[0]

        # Dharmashop Portal
        application = Application.objects.get_or_create(uuid='e4a281ef13e1484b93fe4b7cc66374c8')[0]    
        cee_app_roles += [ApplicationRole.objects.get_or_create(application=application, role=user_role)[0]]
        
        # Dharmashop EU 
        application = Application.objects.get_or_create(uuid='35efc492b8f54f1f86df9918e8cc2b3d')[0]    
        eu_dharmashop_user = ApplicationRole.objects.get_or_create(application=application, role=user_role)[0]
        eu_dharmashop_guest = ApplicationRole.objects.get_or_create(application=application, role=guest_role)[0]
        eu_app_roles += [eu_dharmashop_user, eu_dharmashop_guest]
        
        # Dharmashop CEE 
        application = Application.objects.get_or_create(uuid='2139dc55af8b42ec84a1ce9fd25fdf18')[0]    
        cee_dharmashop_user = ApplicationRole.objects.get_or_create(application=application, role=user_role)[0]
        cee_dharmashop_guest = ApplicationRole.objects.get_or_create(application=application, role=guest_role)[0]
        cee_app_roles += [cee_dharmashop_user, cee_dharmashop_guest]

        users = User.objects.filter(organisations__iso2_code__in=['CZ', 'SK', 'PL', 'RU', 'UA', 'RO', 'RS', 'HR', 'GR', 'BG', 'EE', 'LV']).\
                                            exclude(application_roles__in=[cee_dharmashop_user, cee_dharmashop_guest])
        for user in users:
            print user.get_full_name()
            for app_role in cee_app_roles:
                user.application_roles.add(app_role)
                #pass
                       
            for app_role in eu_app_roles:
                #pass
                user.application_roles.remove(app_role)
