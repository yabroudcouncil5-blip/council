from django.contrib import admin
from .models import CouncilSettings, Department, ComplaintCategory, AuditLog
admin.site.register([CouncilSettings, Department, ComplaintCategory, AuditLog])

# Register your models here.
