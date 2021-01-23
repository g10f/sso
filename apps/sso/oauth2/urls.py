from django.urls import path
from . import views

app_name = 'oauth2'

urlpatterns = [
    path('authorize/', views.authorize, name='authorize'),
    path('revoke/', views.revoke, name='revoke'),
    path('certs/', views.CertsView.as_view(), name='certs'),
    path('jwks/', views.JwksView.as_view(), name='jwks'),
    path('token/', views.TokenView.as_view(), name='token'),
    path('tokeninfo/', views.tokeninfo, name='tokeninfo'),
    path('introspect/', views.introspect, name='introspect'),
    path('approval/', views.approval, name='approval'),
    path('error/', views.ErrorView.as_view(), name='oauth2_error'),
    path('session/', views.SessionView.as_view(template_name="oauth2/session.html"), name='session'),
    path('session/init/', views.session_init, name='session_init'),
    path('client/<int:object_id>/', views.client_details, name='client.details.json'),
]
