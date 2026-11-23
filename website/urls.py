from django.urls import path
from .views import home, about, news, news_detail, news_image, executive_member_photo, departments, council, contact, page
urlpatterns = [path('pages/<slug:slug>/', page, name='content-page')]
urlpatterns += [path('',home),path('about/',about),path('services/',page, {'slug': 'services'}, name='council-services'),path('news/',news),path('news/<int:pk>/',news_detail),path('departments/',departments),path('council/',council),path('contact/',contact)]

urlpatterns += [path("news/<int:pk>/image/", news_image, name="news-featured-image")]
urlpatterns += [path("council/team/<int:pk>/photo/", executive_member_photo, name="executive-member-photo")]
