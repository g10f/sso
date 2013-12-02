from django.conf.urls import patterns, url
from django.views.generic import TemplateView 
from .views import register, validation_confirm, UserRegistrationList, update_user_registration
from forms import UserRegistrationCreationForm
from tokens import default_token_generator
from . import default_username_generator


class RegistrationSite(object):
    """"
    Site with customizable Registrationform, token_generator and 
    username_generator
    """
    def __init__(self, 
                 form_cls=UserRegistrationCreationForm, 
                 token_generator=default_token_generator,
                 username_generator=default_username_generator):
        self.form_cls = form_cls
        self.token_generator = token_generator
        self.username_generator = username_generator
    
    def get_urls(self):
        urlpatterns = patterns('',
            # registration
            url(r'^register/validate/complete/$', TemplateView.as_view(template_name='registration/validation_complete.html'), name='validation_complete'),
            url(r'^register/validate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', validation_confirm, name='validation_confirm'),
            url(r'^register/$', register, {'form_cls': self.form_cls}, name='registration_register'),
            url(r'^register/done/$', TemplateView.as_view(template_name='registration/registration_done.html'), name='registration_done'),
            url(r'^register/closed/$', TemplateView.as_view(template_name='registration/registration_closed.html'), name='registration_disallowed'),
            url(r'^registrations/$', UserRegistrationList.as_view(), name='user_registration_list'),
            url(r'^registrations/(?P<pk>[^/]+)/$', update_user_registration, name="update_user_registration"), 
        )
        return urlpatterns 
    
    @property
    def urls(self):
        return self.get_urls(), 'registration', 'registration'
    
    
site = RegistrationSite()
