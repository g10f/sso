import locale


def strcoll(a, b):
    return locale.strcoll(str(a), str(b))
