

class StreamingRouter(object):
    """
    A router to control all database operations on models in the
    streaming application.
    """
    def db_for_read(self, model, **hints):
        """
        Attempts to read streaming models go to streaming.
        """
        if model._meta.app_label == 'streaming':
            return 'streaming'
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write streaming models go to streaming.
        """
        if model._meta.app_label == 'streaming':
            return 'streaming'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in the streaming app is involved.
        """
        if obj1._meta.app_label == 'streaming' or \
           obj2._meta.app_label == 'streaming':
            return True
        return None

    def allow_syncdb(self, db, model):
        """
        syncdb is not used with streaming.
        """
        if (db == 'streaming') or (model._meta.app_label == 'streaming'):
            return False
        return None
