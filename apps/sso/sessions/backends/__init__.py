
key_map = {
    #  "_auth_user_backend": "", # Authentication with session is always from sso.auth.backends.EmailBackend
    "_auth_device_id": "dev",  # custom
    "_auth_user_hash": "auh",  # custom, used in get_user
    "_auth_user_id": "sub",
    "_session_expiry": "sxp",
    "_auth_date": "iat"
}
inv_key_map = {v: k for k, v in key_map.items()}


def map_keys(source, _mapping):
    dest = {}
    for (keyname, value) in source.items():
        new_keyname = _mapping.get(keyname)
        if new_keyname:
            dest[new_keyname] = value
        else:
            dest[keyname] = value
    return dest


