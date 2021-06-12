import logging

from django.core.cache.backends.memcached import PyMemcacheCache

logger = logging.getLogger(__name__)


class SSOCache(PyMemcacheCache):
    def __init__(self, server, params):
        server = server if server else ['127.0.0.1:11211']
        params = params if params is not None else {}
        default_options = {
            'no_delay': True,
            'ignore_exc': True,
            'max_pool_size': 4,
            'use_pooling': True,
            'connect_timeout': 1,
            'timeout': 1
        }
        params['OPTIONS'] = params.get('OPTIONS', default_options)
        params['TIMEOUT'] = params.get('TIMEOUT', 300)
        super().__init__(server, params)

    def get(self, key, default=None, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        val = self._cache.get(key, default)
        # if memcached is not reachable ('ignore_exc': True)
        # returns None instead of default
        if val is None and default is not None:
            logger.warning("memcached seems to be not reachable")
            return default
        return val
