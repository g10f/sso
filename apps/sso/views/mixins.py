from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from django.utils.encoding import force_str
from django.utils.html import format_html


class MessagesMixin(object):
    @property
    def msg_dict(self):
        return {'name': force_str(self.model._meta.verbose_name), 'obj': force_str(self.object)}

    def add_message(self, message, level=messages.SUCCESS):
        msg = format_html(message, **self.msg_dict)
        messages.add_message(self.request, level=level, message=msg, fail_silently=True)

    def delete_message(self):
        self.add_message(format_html(_('The {name} "{obj}" was deleted successfully.'), **self.msg_dict), level=messages.WARNING)

    def update_and_continue_message(self):
        self.add_message(format_html(_('The {name} "{obj}" was saved successfully. You may edit it again below.'), **self.msg_dict))

    def update_message(self):
        self.add_message(format_html(_('The {name} "{obj}" was saved successfully.'), **self.msg_dict))

    def create_and_continue_message(self):
        self.add_message(format_html(_('The {name} "{obj}" was created successfully. You may edit it again below.'), **self.msg_dict))

    def create_message(self):
        self.add_message(format_html(_('The {name} "{obj}" was created successfully.'), **self.msg_dict))
