import logging

from django.core.management.base import BaseCommand
from sso.access_requests.models import AccessRequest

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Cleanup Access Requests'  # @ReservedAssignment

    def handle(self, *args, **options):
        delete_expired_access_requests()


def delete_expired_access_requests():
    index = -1
    for index, access_request in enumerate(AccessRequest.open.get_expired()):
        logger.info(f"Deleting AccessRequest from user {access_request.user}. Last modified: {access_request.last_modified}")
        access_request.delete()
    logger.info(f"Deleted {index + 1} access_request(s)")
