from django.urls import path
from .views import impersonate_user

app_name = 'impersonate'

urlpatterns = [
    path('<int:pk>/', impersonate_user, name="impersonate_user"),
]
