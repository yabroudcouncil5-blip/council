from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.conf import settings

class Complaint(models.Model):
    class Meta:
        verbose_name = 'شكوى'
        verbose_name_plural = 'الشكاوى'

    def __str__(self):
        return self.reference + " · " + self.title

    STATUS = [('submitted','تم الاستلام'),('under_review','قيد المراجعة'),('assigned','تمت الإحالة'),('in_progress','قيد المعالجة'),('final_review','قيد التحقق النهائي'),('completed','تمت المعالجة'),('closed','أغلقت دون معالجة')]
    reference = models.CharField(max_length=24, unique=True, editable=False, verbose_name='الرقم المرجعي')
    tracking_hash = models.CharField(max_length=128, verbose_name='بصمة رمز التتبع')
    title = models.CharField(max_length=200, verbose_name='موضوع الشكوى')
    description = models.TextField(verbose_name='الوصف')
    name = models.CharField(max_length=160, blank=True, verbose_name='الاسم')
    phone = models.CharField(max_length=80, blank=True, verbose_name='رقم الهاتف')
    email = models.EmailField(blank=True, verbose_name='البريد الإلكتروني')
    category = models.ForeignKey('core.ComplaintCategory', null=True, blank=True, on_delete=models.SET_NULL, verbose_name='التصنيف')
    location = models.CharField(max_length=255, blank=True, verbose_name='الموقع')
    status = models.CharField(max_length=30, choices=STATUS, default='submitted', verbose_name='الحالة')
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الاستلام')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخر تحديث')
    @staticmethod
    def hash_tracking(value): return make_password(value)
    def verify_tracking(self, value): return check_password(value, self.tracking_hash)

class ComplaintStatusHistory(models.Model):
    class Meta:
        verbose_name = 'تحديث حالة'
        verbose_name_plural = 'سجل الحالات'

    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='status_history', verbose_name='الشكوى')
    status = models.CharField(max_length=30, verbose_name='الحالة')
    public_message = models.TextField(blank=True, verbose_name='الرسالة للمواطن')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='الموظف')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')

class ComplaintAssignment(models.Model):
    class Meta:
        verbose_name = 'إحالة'
        verbose_name_plural = 'الإحالات'

    def __str__(self):
        return f"{self.complaint.reference} · {self.department.name}"

    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='assignments', verbose_name='الشكوى')
    department = models.ForeignKey('core.Department', on_delete=models.PROTECT, verbose_name='القسم المختص')
    officer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='الموظف المسؤول')
    status = models.CharField(max_length=30, default='assigned', verbose_name='الحالة')
    priority = models.CharField(max_length=20, default='medium', verbose_name='الأولوية')
    due_at = models.DateTimeField(null=True, blank=True, verbose_name='الموعد المحدد')
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإحالة')

class AssignmentAction(models.Model):
    class Meta:
        verbose_name = 'إجراء تنفيذي'
        verbose_name_plural = 'إجراءات التنفيذ'

    assignment = models.ForeignKey(ComplaintAssignment, on_delete=models.CASCADE, related_name='actions', verbose_name='الإحالة')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name='الموظف')
    internal_action = models.TextField(verbose_name='الإجراء الداخلي')
    public_message = models.TextField(blank=True, verbose_name='الرسالة للمواطن')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')

class ComplaintAttachment(models.Model):
    class Meta:
        verbose_name = 'مرفق'
        verbose_name_plural = 'المرفقات'

    def __str__(self):
        return self.original_name

    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='attachments', verbose_name='الشكوى')
    file = models.FileField(upload_to='complaints/%Y/%m/', verbose_name='الملف')
    original_name = models.CharField(max_length=255, verbose_name='اسم الملف الأصلي')
    visibility = models.CharField(max_length=20, default='internal', verbose_name='نطاق الظهور')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الرفع')

class RecoveryRequest(models.Model):
    class Meta:
        verbose_name = 'طلب استعادة'
        verbose_name_plural = 'طلبات استعادة التتبع'

    def __str__(self):
        return self.complaint_reference or f"طلب #{self.pk}"

    complaint_reference = models.CharField(max_length=24, blank=True, verbose_name='الرقم المرجعي للشكوى')
    explanation = models.TextField(verbose_name='تفاصيل طلب الاستعادة')
    contact = models.CharField(max_length=160, blank=True, verbose_name='وسيلة التواصل')
    status = models.CharField(max_length=20, default='pending', verbose_name='الحالة')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')

class ComplaintReview(models.Model):
    class Meta:
        verbose_name = 'مراجعة'
        verbose_name_plural = 'المراجعات والاعتماد'

    def __str__(self):
        return f"{self.complaint.reference} · {self.get_decision_display()}"

    DECISIONS = [('returned','إعادة للاستكمال'),('additional_assignment','إحالة إضافية'),('approved','اعتماد'),('closed','إغلاق')]
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='reviews', verbose_name='الشكوى')
    assignment = models.ForeignKey(ComplaintAssignment, null=True, blank=True, on_delete=models.CASCADE, verbose_name='الإحالة')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name='المراجع')
    decision = models.CharField(max_length=30, choices=DECISIONS, verbose_name='قرار المراجعة')
    reason = models.TextField(blank=True, verbose_name='الملاحظات والأسباب')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')

class ComplaintPublication(models.Model):
    class Meta:
        verbose_name = 'نتيجة معالجة'
        verbose_name_plural = 'نتائج المعالجة والنشر'

    def __str__(self):
        return self.complaint.reference

    VISIBILITY = [('private','داخلي'),('tracked','لصاحب الشكوى'),('public','عام')]
    complaint = models.OneToOneField(Complaint, on_delete=models.CASCADE, related_name='publication', verbose_name='الشكوى')
    summary = models.TextField(verbose_name='ملخص المعالجة')
    visibility = models.CharField(max_length=20, choices=VISIBILITY, default='private', verbose_name='نطاق الظهور')
    approved = models.BooleanField(default=False, verbose_name='معتمد للنشر')
    published_at = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ النشر')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='اعتمد بواسطة')

class InternalNotification(models.Model):
    class Meta:
        verbose_name = 'تنبيه'
        verbose_name_plural = 'التنبيهات الداخلية'

    def __str__(self):
        return self.message

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='الموظف المستلم')
    message = models.CharField(max_length=255, verbose_name='نص التنبيه')
    complaint = models.ForeignKey(Complaint, null=True, blank=True, on_delete=models.CASCADE, verbose_name='الشكوى')
    read = models.BooleanField(default=False, verbose_name='مقروء')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')

# Create your models here.
