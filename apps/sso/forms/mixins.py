# -*- coding: utf-8 -*-
class UserRolesMixin(object):

    def update_user_m2m_fields(self, attribute_name, current_user):
        """
        get the new data from the form and then update or remove values from many2many fields.
        Adding and removing is done with respect to the permissions of the current user.
        Only administrable values of the current user are changed at the user
        """
        # first get the new values. This can be a queryset or a single object
        cd = self.cleaned_data.get(attribute_name)
        try:
            new_value_set = set(cd.values_list('id', flat=True))
        except AttributeError:
            # should be a single object instead of queryset
            new_value_set = set([cd.id]) if cd else set()
                                
        administrable_values = set(getattr(current_user, 'get_administrable_%s' % attribute_name)().values_list('id', flat=True)) 
        existing_values = set(getattr(self.user, '%s' % attribute_name).all().values_list('id', flat=True))
        remove_values = ((existing_values & administrable_values) - new_value_set)
        new_value_set = (new_value_set - existing_values)            

        user_attribute = getattr(self.user, '%s' % attribute_name)
        if remove_values:
            user_attribute.remove(*remove_values)
        if new_value_set:
            user_attribute.add(*new_value_set)
