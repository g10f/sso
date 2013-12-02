import re
from django.utils.text import capfirst
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import get_user_model


def remove(name, *args):
    for arg in args:
        name = name.replace(arg, "")
    return name

def default_username_generator(first_name, last_name):
    """
    search for existing usernames and create a new one with a not existing number
    after first_name if necessary
    """
    remove_chars = [' ', '-']
    
    first_name = capfirst(remove(first_name, *remove_chars))
    last_name = capfirst(remove(last_name, *remove_chars))
    username = u"%s%s" % (first_name, last_name)
    
    try:
        get_user_model().objects.get(username=username)
    except ObjectDoesNotExist:
        return username
    
    username_pattern = r'^%s([0-9]+)%s$' % (first_name, last_name)
    users = get_user_model().objects.filter(username__regex=username_pattern)
    
    existing = set()
    username_pattern = r'%s(?P<no>[0-9]+)%s' % (first_name, last_name)
    prog = re.compile(username_pattern)
    for user in users:
        m = prog.match(user.username)  # we should alway find a match, because of the filter
        result = m.groupdict()
        no = 0 if not result['no'] else result['no']
        existing.add(int(no))

    new_no = 1
    while new_no in existing:
        new_no += 1

    username = u"%s%d%s" % (first_name, new_no, last_name)
    return username
