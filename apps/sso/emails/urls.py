from django.urls import path
from sso.emails import views

app_name = 'emails'

urlpatterns = [
    path('group/', views.GroupEmailList.as_view(), name='groupemail_list'),
    path('group/<sso.uuid:uuid>/', views.GroupEmailDetailView.as_view(), name='groupemail_detail'),
    path('group/<sso.uuid:uuid>/update/', views.GroupEmailUpdateView.as_view(), name='groupemail_update'),
    path('group/add/', views.GroupEmailCreateView.as_view(), name='groupemail_create'),
    path('group/<sso.uuid:uuid>/forward/add/', views.GroupEmailForwardCreateView.as_view(),
         name='emailforward_create'),
    path('group/<sso.uuid:uuid>/forward/<int:pk>/', views.GroupEmailForwardDeleteView.as_view(),
         name="emailforward_confirm_delete"),
]
