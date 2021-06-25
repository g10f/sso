import logging
from base64 import b64encode
from pathlib import Path

import reversion
from sorl.thumbnail import get_thumbnail

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.crypto import salted_hmac
from sso.accounts.models import User

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Migrate pictures to standard format'  # @ReservedAssignment

    def add_arguments(self, parser):
        parser.add_argument('-m', '--max', action='store', dest='maximum', type=int, default=10, help='maximum number of pictures to migrate')

    def handle(self, *args, **options):
        migrate_pictures(options['maximum'])


def get_format(file_extension):
    if file_extension == '.jpg' or file_extension == '.jpeg':
        return 'JPEG'
    elif file_extension == '.png':
        return 'PNG'
    elif file_extension == '.gif':
        return 'GIF'
    elif file_extension == '.webp':
        return 'WEBP'
    else:
        from django.conf import settings
        from sorl.thumbnail.conf import settings, defaults as default_settings

        return getattr(settings, 'THUMBNAIL_FORMAT', default_settings.THUMBNAIL_FORMAT)


def migrate_pictures(maximum):
    key_salt = 'sso.forms.clean_base64_picture'
    index = 0
    for user in User.objects.filter(is_active=True).exclude(picture=''):
        picture_path = Path(user.picture.path)
        if len(picture_path.stem) < 9 and picture_path.is_file():
            with reversion.create_revision():
                try:
                    thumbnail = get_thumbnail(user.picture, f"{User.PICTURE_WIDTH}x{User.PICTURE_HEIGHT}", crop="center", quality=100,
                                              format=get_format(picture_path.suffix))
                    image_content = thumbnail.read()
                    name = "%s%s" % (salted_hmac(key_salt, b64encode(image_content)).hexdigest(), Path(str(thumbnail)).suffix)
                    # user.picture.delete(save=False) # files will be deleted in cleanup_users
                    user.picture = ContentFile(image_content, name=name)
                    user.save(update_fields=['picture', 'last_modified'])
                    reversion.set_comment(f"update {user} from migrate_pictures task")

                    for dimension in ["30x30", "60x60", "120x120", "240x240", "480x480"]:
                        get_thumbnail(user.picture, dimension, crop="center")

                    index += 1
                    logger.info(user)
                    if index >= maximum:
                        break
                except Exception as e:
                    logger.error(f"error migrating user {user}. {e}")
