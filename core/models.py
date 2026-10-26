from django.db import models

class CouncilSettings(models.Model):
    name = models.CharField(max_length=200, default='بلدية يبرود')
    description = models.TextField(blank=True)
    phone = models.CharField(max_length=80, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

class Department(models.Model):
    name = models.CharField(max_length=160, unique=True)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    members = models.ManyToManyField('auth.User', blank=True, related_name='council_departments')
    def __str__(self): return self.name

class ComplaintCategory(models.Model):
    name = models.CharField(max_length=120, unique=True)
    default_days = models.PositiveIntegerField(default=7)
    active = models.BooleanField(default=True)
    def __str__(self): return self.name

class AuditLog(models.Model):
    actor = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=120)
    target_type = models.CharField(max_length=120, blank=True)
    target_id = models.CharField(max_length=80, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
