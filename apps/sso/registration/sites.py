from django.urls import path
from django.views.generic import TemplateView
from . import default_username_generator
from .forms import UserSelfRegistrationForm
from .tokens import default_token_generator
from .views import validation_confirm, UserRegistrationList, UserRegistrationDeleteView, \
    update_user_registration, RegistrationSendMailFormView, UserSelfRegistrationFormPreview  # , register


class RegistrationSite(object):
    """"
    Site with customizable Registrationform, token_generator and
    username_generator
    """

    def __init__(self, form_cls=UserSelfRegistrationForm, token_generator=default_token_generator,
                 username_generator=default_username_generator):
        self.form_cls = form_cls
        self.token_generator = token_generator
        self.username_generator = username_generator

    def get_urls(self):
        urlpatterns = [
            # registration
            path('register/validate/complete/', TemplateView.as_view(template_name='registration/validation_complete.html'), name='validation_complete'),
            path('register/validate/complete2/', TemplateView.as_view(template_name='registration/validation_complete2.html'), name='validation_complete2'),
            path('register/validate/<slug:uidb64>/<slug:token>/', validation_confirm, name='validation_confirm'),
            path('register/', UserSelfRegistrationFormPreview(self.form_cls), name='registration_register'),
            path('register/done/', TemplateView.as_view(template_name='registration/registration_done.html'), name='registration_done'),
            path('register/closed/', TemplateView.as_view(template_name='registration/registration_closed.html'), name='registration_disallowed'),
            path('registrations/', UserRegistrationList.as_view(), name='user_registration_list'),
            path('registrations/<int:pk>/', update_user_registration, name="update_user_registration"),
            path('registrations/delete/<int:pk>/', UserRegistrationDeleteView.as_view(), name="delete_user_registration"),
            path('registrations/process/<int:pk>/<slug:action>/', RegistrationSendMailFormView.as_view(), name="process_user_registration"),
        ]
        return urlpatterns

    @property
    def urls(self):
        return self.get_urls(), 'registration', 'registration'


site = RegistrationSite()
