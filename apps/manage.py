#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    DIRNAME = os.path.dirname(__file__)
    sys.path.insert(0, DIRNAME)
    
    os.environ["DJANGO_SETTINGS_MODULE"] = 'sso.settings'

    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

    #from django.contrib.contenttypes.management import update_all_contenttypes
    #update_all_contenttypes(verbosity=2, interactive=True)
