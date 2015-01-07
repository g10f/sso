import re
from django.utils.text import capfirst
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import get_user_model


def remove(name, *args):
    for arg in args:
        name = name.replace(arg, "")
    return name


def default_username_generator(first_name, last_name, user=None):
    """
    search for existing usernames and create a new one with a not existing number
    after first_name if necessary
    """
    remove_chars = [' ', '-']
    
    first_name = capfirst(remove(first_name, *remove_chars))
    last_name = capfirst(remove(last_name, *remove_chars))
    username = u"%s%s" % (first_name, last_name)
    username = username[:29]  # max 30 chars

    if user is not None:
        exists = get_user_model().objects.filter(username=username).exclude(pk=user.pk).exists()
    else:
        exists = get_user_model().objects.filter(username=username).exists()
    if not exists:
        return username
    
    username_pattern = r'^%s([0-9]+)$' % username
    users = get_user_model().objects.filter(username__regex=username_pattern)
    
    existing = set()
    username_pattern = r'%s(?P<no>[0-9]+)' % username
    prog = re.compile(username_pattern)
    for user in users:
        m = prog.match(user.username)  # we should alway find a match, because of the filter
        result = m.groupdict()
        no = 0 if not result['no'] else result['no']
        existing.add(int(no))

    new_no = 1
    while new_no in existing:
        new_no += 1

    username = u"%s%d" % (username, new_no)
    return username
