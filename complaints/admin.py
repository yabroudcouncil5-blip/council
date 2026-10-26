from django.contrib import admin
from .models import Complaint, ComplaintAssignment, AssignmentAction, ComplaintAttachment, RecoveryRequest, ComplaintReview, ComplaintPublication, InternalNotification
admin.site.register([Complaint, ComplaintAssignment, AssignmentAction, ComplaintAttachment, RecoveryRequest, ComplaintReview, ComplaintPublication, InternalNotification])

# Register your models here.
