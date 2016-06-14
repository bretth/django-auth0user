from django.conf.urls import url

from . import views

app_name = 'auth0user'
urlpatterns = [
    url(r'^alogin/', views.alogin, name='alogin'),
]
