"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import health, council_logo
from website.views import upload_editor_image, content_image
from complaints.views import complaint_form, tracking_form, submit_complaint, track_complaint, recovery_request, review_queue, assign_complaint, action_submission, final_review, publish_resolution, public_resolutions, dashboard_report, staff_dashboard
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/website/upload-image/', upload_editor_image, name='editor-image-upload'),
    path('website-images/<str:filename>', content_image, name='website-content-image'),
    path('media/council/logos/<path:filename>', council_logo, name='council-logo'),
    path('admin/', admin.site.urls),
    path('', include('website.urls')),
    path('health/', health),
    path('complaints/submit/', complaint_form),
    path('complaints/track/', tracking_form),
    path('api/complaints/', submit_complaint),
    path('api/complaints/track/', track_complaint),
    path('api/complaints/recovery/', recovery_request),
    path('staff/review-queue/', review_queue),
    path('staff/dashboard/', staff_dashboard),
    path('staff/assign/', assign_complaint),
    path('staff/action/', action_submission),
    path('staff/final-review/', final_review),
    path('staff/publish/', publish_resolution),
    path('api/public/resolutions/', public_resolutions),
    path('staff/reports/', dashboard_report),
    path('staff/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('staff/logout/', auth_views.LogoutView.as_view(), name='logout'),
]
admin.site.site_header = 'إدارة بلدية يبرود'
admin.site.site_title = 'إدارة بلدية يبرود'
admin.site.index_title = 'لوحة الإدارة'
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
