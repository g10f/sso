from django.contrib.auth.decorators import permission_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.generic import FormView
from sso.auth.decorators import admin_login_required
from sso.forms.sendmail import SendMailForm


class SendMailFormView(FormView):
    model = None
    email_messages = {}
    action_breadcrumbs = {}
    action_txts = {}
    success_url = None
    template_name = None
    cancel_url = None

    def __init__(self, form_class=SendMailForm, *args, **kwargs):
        # form_class should be a Form class, not an instance.
        self.form_class = form_class
        self.instance = None
        super().__init__(*args, **kwargs)

    def get_cancel_url(self):
        return self.cancel_url

    @method_decorator(admin_login_required)
    @method_decorator(permission_required('accounts.change_user'))
    def dispatch(self, request, *args, **kwargs):
        self.instance = get_object_or_404(self.model, pk=self.kwargs['pk'])
        # check if admin has access to the specific user
        if not request.user.has_user_access(self.instance.user.uuid):
            raise PermissionDenied
        self.extra_context = {'action_txt': self.action_txts[self.kwargs['action']],
                              'action_breadcrumb': self.action_breadcrumbs[self.kwargs['action']],
                              'cancel_url': self.get_cancel_url()}
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.instance
        kwargs['request'] = self.request
        return kwargs

    def get_initial(self):
        reply_to_email = self.request.user.primary_email().email
        message, subject = self.email_messages[self.kwargs['action']](self.instance.user, self.request, reply_to_email)
        return {'message': message, 'subject': subject}

    def form_valid(self, form):
        self.instance.process(self.kwargs['action'], self.request.user)
        message = form.cleaned_data['message']
        subject = form.cleaned_data['subject']
        self.instance.user.email_user(subject, message, reply_to=[self.request.user.primary_email().email])
        return super().form_valid(form)
