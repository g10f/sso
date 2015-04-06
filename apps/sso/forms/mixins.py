# -*- coding: utf-8 -*-

def ids_from_objs(listobject):
    return set([x.id for x in listobject])

def ids_from_choices(listobject):
    return set([int(x) for x in listobject])

class UserRolesMixin(object): 
    def _update_user_m2m(self, new_value_set, administrable_values, attribute_name):
        """
        get the new data from the form and then update or remove values from many2many fields.
        Adding and removing is done with respect to the permissions of the current user.
        Only administrable values of the current user are changed at the user. The user object must have 
        
        a function: get_administrable_{{ attribute_name }}
        and an attribute: {{ attribute_name }}        
        """
        existing_values = set(getattr(self.user, '%s' % attribute_name).all().values_list('id', flat=True))
        remove_values = ((existing_values & administrable_values) - new_value_set)
        new_value_set = (new_value_set - existing_values)            
        
        user_attribute = getattr(self.user, '%s' % attribute_name)
        if remove_values:
            user_attribute.remove(*remove_values)
        if new_value_set:
            user_attribute.add(*new_value_set)

    def update_user_m2m_fields_from_list(self, attribute_name, current_user):
        """
        get the new values from a MultipleChoiceField and the existing from a list
        """
        new_value_set = ids_from_choices(self.cleaned_data.get(attribute_name))
        administrable_values = ids_from_objs(getattr(current_user, 'get_administrable_%s' % attribute_name)())
        
        self._update_user_m2m(new_value_set, administrable_values, attribute_name)

    def update_user_m2m_fields(self, attribute_name, current_user):
        """
        get the new values from a ModelMultipleChoiceField and the existing from a queryset
        """
        # first get the new values. This can be a queryset or a single object
        cd = self.cleaned_data.get(attribute_name)
        try:
            if isinstance(cd, list):  # role_profiles
                new_value_set = set(cd)
            else:  # queryset
                new_value_set = set(cd.values_list('id', flat=True))
        except AttributeError:
            # should be a single object instead of queryset
            new_value_set = {cd.id} if cd else set()
                                
        administrable_values = set(getattr(current_user, 'get_administrable_%s' % attribute_name)().values_list('id', flat=True))  
        self._update_user_m2m(new_value_set, administrable_values, attribute_name)
