from django.core.management.base import NoArgsCommand
from sso.accounts.models import User, Application, Role, ApplicationRole

DHARMA_SHOP_HOME = 'e4a281ef13e1484b93fe4b7cc66374c8'
DHARMA_SHOP_EU = '35efc492b8f54f1f86df9918e8cc2b3d'
DHARMA_SHOP_CEE = '2139dc55af8b42ec84a1ce9fd25fdf18'
DHARMA_SHOP_NA = '97d58b7ddcf24b1ba7c85b151d2a69c5'
DHARMA_SHOP_HU = '3d2ec652335f40c6922dcaf7569ea916'
DHARMA_SHOP_SA = 'cab4c46224394346b5d51867fead42f0'
DHARMA_SHOP_AU = 'bcae7e305ba24095bcb0cbc6ffc33944'


DHARMASHOPS_UUIDS = [
    '35efc492b8f54f1f86df9918e8cc2b3d',
    '2139dc55af8b42ec84a1ce9fd25fdf18',
    '97d58b7ddcf24b1ba7c85b151d2a69c5',
    '3d2ec652335f40c6922dcaf7569ea916',
    'cab4c46224394346b5d51867fead42f0',
    'bcae7e305ba24095bcb0cbc6ffc33944'
]

class Command(NoArgsCommand):
    help = '...'  # @ReservedAssignment
    
    def handle_noargs(self, **options):
        user_role = Role.objects.get_or_create(name='User')[0]
        guest_role = Role.objects.get_or_create(name='Guest')[0]

        dharma_shop_home_app = Application.objects.get_or_create(uuid=DHARMA_SHOP_HOME)[0]
        dharma_shop_home_user_role = ApplicationRole.objects.get_or_create(application=dharma_shop_home_app, role=user_role)[0]
        
        app_roles = []
        
        for uuid in DHARMASHOPS_UUIDS:
            application = Application.objects.get_or_create(uuid=uuid)[0]
            app_role = ApplicationRole.objects.get_or_create(application=application, role=guest_role)[0]
            app_roles.append(app_role)
        
        # select all users which have already the dharmashop_home role and one guest role for a regional shop
        q = User.objects.filter(application_roles=dharma_shop_home_user_role).filter(application_roles__in=app_roles)
        
        # select all users having an organisation and not the standard roles
        users = User.objects.filter(organisations__isnull=False).filter(is_active=True).exclude(pk__in=[o.id for o in q])
        
        for user in users:
            print user.get_full_name()
            user.add_default_roles()
