from django.db.models.query_utils import Q

from sso.signals import user_m2m_field_updated


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
            if user_attribute.through._meta.auto_created:
                user_attribute.remove(*remove_values)
            else:
                # ManyRelatedManager does not supports add and remove when using a custom through Model
                filters = Q(**{user_attribute.source_field_name: self.user}) & \
                          Q(**{'%s__in' % user_attribute.target_field_name: remove_values})
                user_attribute.through.objects.filter(filters).delete()
        if new_value_set:
            if user_attribute.through._meta.auto_created:
                user_attribute.add(*new_value_set)
            else:
                # ManyRelatedManager does not supports add and remove when using a custom through Model
                user_attribute.through.objects.bulk_create([
                    user_attribute.through(**{
                        '%s_id' % user_attribute.source_field_name: self.user.id,
                        '%s_id' % user_attribute.target_field_name: obj_id,
                    })
                    for obj_id in new_value_set
                ])

        if remove_values or new_value_set:
            # enable brand specific modification
            user_m2m_field_updated.send_robust(sender=self.__class__, user=self.user, attribute_name=attribute_name,
                                               delete_pk_list=list(remove_values), add_pk_list=list(new_value_set))

    def update_user_m2m_fields(self, attribute_name, current_user, admin_attribute_format='get_administrable_%s'):
        """
        get the new values from a ModelMultipleChoiceField and the existing from a queryset
        """
        # first get the new values. This can be a queryset or a single object
        cd = self.cleaned_data.get(attribute_name)
        try:
            if isinstance(cd, list):  # role_profiles
                new_value_set = set([int(x) for x in cd])  # convert strings list to int set
            else:  # queryset
                new_value_set = set(cd.values_list('id', flat=True))
        except AttributeError:
            # should be a single object instead of queryset
            new_value_set = {cd.id} if cd else set()
                                
        administrable_values = set(getattr(current_user, admin_attribute_format % attribute_name)().values_list('id', flat=True))
        self._update_user_m2m(new_value_set, administrable_values, attribute_name)
