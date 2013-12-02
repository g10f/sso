class FieldRegistry(object):
    _registry = {}

    def add_field(self, model, field):
        reg = self.__class__._registry.setdefault(model, [])
        reg.append(field)

    def get_fields(self, model):
        return self.__class__._registry.get(model, [])

    def __contains__(self, model):
        return model in self.__class__._registry
