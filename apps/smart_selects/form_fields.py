from django.apps import apps
from django.forms import ChoiceField
from django.forms.models import ModelChoiceField
from smart_selects.widgets import ChainedSelect


class ChainedModelChoiceField(ModelChoiceField):
    def __init__(self, app_name, model_name, chain_field, model_field, show_all, auto_choose, manager=None, initial=None, *args, **kwargs):
        defaults = {
            'widget': ChainedSelect(app_name, model_name, chain_field, model_field, show_all, auto_choose, manager),
        }
        defaults.update(kwargs)
        if 'queryset' not in kwargs:
            queryset = apps.get_model(app_name, model_name).objects.all()
            super().__init__(queryset=queryset, initial=initial, *args, **defaults)
        else:
            super().__init__(initial=initial, *args, **defaults)

    def _get_choices(self):
        self.widget.queryset = self.queryset
        choices = super()._get_choices()
        return choices
    choices = property(_get_choices, ChoiceField.choices.fset)
