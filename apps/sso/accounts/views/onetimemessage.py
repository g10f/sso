# -*- coding: utf-8 -*-
import logging

from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.views.generic import DetailView
from django.utils.decorators import method_decorator

from sso.accounts.models import OneTimeMessage

logger = logging.getLogger(__name__)

class OneTimeMessageView(DetailView):
    model = OneTimeMessage
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.user != request.user:
            raise PermissionDenied()
        
        self.object.delete()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)
