"""
    sso
    ~~~~~~~~

    An OpenIDConnect Provider with User, Client and Organisation Management and
    a JSON-LD/Hydra based API

    :copyright: (c) 2021 by Gunnar Scherf.
    :license: BSD, see LICENSE for details.
"""

__author__ = 'Gunnar Scherf <gunnar@g10f.de>'
__version__ = '3.3.0'


# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app as celery_app  # noqa
