from django.urls import path
from django.views.i18n import set_language

urlpatterns = [
    path('setlang/', set_language),
]
