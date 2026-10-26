from django.urls import path
from .views import home, simple, news, departments, contact
urlpatterns = [path('',home),path('about/',lambda r:simple(r,'about')),path('services/',lambda r:simple(r,'services')),path('news/',news),path('departments/',departments),path('contact/',contact)]
