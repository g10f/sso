import logging

from django.contrib.auth.decorators import permission_required
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import DeleteView
from sso.auth.decorators import admin_login_required
from ..models.application import UserNote
from ...oauth2.models import allowed_hosts
from ...utils.url import get_safe_redirect_uri, update_url

logger = logging.getLogger(__name__)

USERNOTES_TAB = "#!tab!notes"


class UserNoteDeleteView(DeleteView):
    slug_field = slug_url_kwarg = 'uuid'
    model = UserNote

    @method_decorator(admin_login_required)
    @method_decorator(permission_required('accounts.delete_usernote', raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        # additionally check if the user is admin of the user
        self.object = self.get_object()
        if not request.user.has_user_access(self.object.uuid):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        redirect_uri = get_safe_redirect_uri(self.request, allowed_hosts())
        if redirect_uri is None:
            redirect_uri = reverse('accounts:update_user', args=[self.object.user.uuid.hex])
        return redirect_uri + USERNOTES_TAB

    def get_object(self, queryset=None):
        if hasattr(self, 'object'):
            return self.object
        return super().get_object(queryset=None)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cancel_url'] = reverse('accounts:update_user', args=[self.object.user.uuid.hex])
        context['usernotes_tab'] = USERNOTES_TAB
        return context
