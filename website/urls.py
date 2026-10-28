from django.urls import path
from .views import home, simple, news, departments, council, contact, page
urlpatterns = [path('pages/<slug:slug>/', page, name='content-page')]
urlpatterns += [path('',home),path('about/',lambda r:simple(r,'about')),path('services/',lambda r:simple(r,'services')),path('news/',news),path('departments/',departments),path('council/',council),path('contact/',contact)]
