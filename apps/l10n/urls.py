from django.conf.urls import patterns

urlpatterns = patterns(
    '',
    (r'^setlang/$', 'django.views.i18n.set_language', {}, 'satchmo_set_language'),
)
