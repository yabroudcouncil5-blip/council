from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.conf import settings

class Complaint(models.Model):
    STATUS = [('submitted','تم الاستلام'),('under_review','قيد المراجعة'),('assigned','تمت الإحالة'),('in_progress','قيد المعالجة'),('final_review','قيد التحقق النهائي'),('completed','تمت المعالجة'),('closed','أغلقت دون معالجة')]
    reference = models.CharField(max_length=24, unique=True, editable=False)
    tracking_hash = models.CharField(max_length=128)
    title = models.CharField(max_length=200)
    description = models.TextField()
    name = models.CharField(max_length=160, blank=True)
    phone = models.CharField(max_length=80, blank=True)
    email = models.EmailField(blank=True)
    category = models.ForeignKey('core.ComplaintCategory', null=True, blank=True, on_delete=models.SET_NULL)
    location = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=30, choices=STATUS, default='submitted')
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    @staticmethod
    def hash_tracking(value): return make_password(value)
    def verify_tracking(self, value): return check_password(value, self.tracking_hash)

class ComplaintStatusHistory(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(max_length=30)
    public_message = models.TextField(blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

class ComplaintAssignment(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='assignments')
    department = models.ForeignKey('core.Department', on_delete=models.PROTECT)
    officer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=30, default='assigned')
    priority = models.CharField(max_length=20, default='medium')
    due_at = models.DateTimeField(null=True, blank=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

class AssignmentAction(models.Model):
    assignment = models.ForeignKey(ComplaintAssignment, on_delete=models.CASCADE, related_name='actions')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    internal_action = models.TextField()
    public_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class ComplaintAttachment(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='complaints/%Y/%m/')
    original_name = models.CharField(max_length=255)
    visibility = models.CharField(max_length=20, default='internal')
    uploaded_at = models.DateTimeField(auto_now_add=True)

class RecoveryRequest(models.Model):
    complaint_reference = models.CharField(max_length=24, blank=True)
    explanation = models.TextField()
    contact = models.CharField(max_length=160, blank=True)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

class ComplaintReview(models.Model):
    DECISIONS = [('returned','Returned for Further Work'),('additional_assignment','Additional Assignment'),('approved','Approved'),('closed','Closed')]
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='reviews')
    assignment = models.ForeignKey(ComplaintAssignment, null=True, blank=True, on_delete=models.CASCADE)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    decision = models.CharField(max_length=30, choices=DECISIONS)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class ComplaintPublication(models.Model):
    VISIBILITY = [('private','Private'),('tracked','Tracked only'),('public','Public')]
    complaint = models.OneToOneField(Complaint, on_delete=models.CASCADE, related_name='publication')
    summary = models.TextField()
    visibility = models.CharField(max_length=20, choices=VISIBILITY, default='private')
    approved = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

class InternalNotification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.CharField(max_length=255)
    complaint = models.ForeignKey(Complaint, null=True, blank=True, on_delete=models.CASCADE)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

# Create your models here.
