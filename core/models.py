from django.db import models

class CouncilSettings(models.Model):
    class Meta:
        verbose_name = 'بيانات البلدية'
        verbose_name_plural = 'بيانات البلدية'

    def __str__(self):
        return self.name

    name = models.CharField(max_length=200, default='بلدية يبرود', verbose_name='الاسم')
    logo = models.ImageField(upload_to='council/logos/', blank=True, verbose_name='شعار البلدية', help_text='ارفع صورة للشعار بصيغة PNG أو JPEG أو WebP.')
    description = models.TextField(blank=True, verbose_name='الوصف')
    phone = models.CharField(max_length=80, blank=True, verbose_name='رقم الهاتف')
    email = models.EmailField(blank=True, verbose_name='البريد الإلكتروني')
    address = models.CharField(max_length=255, blank=True, verbose_name='العنوان')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخر تحديث')

class Department(models.Model):
    class Meta:
        verbose_name = 'قسم'
        verbose_name_plural = 'الأقسام'

    name = models.CharField(max_length=160, unique=True, verbose_name='الاسم')
    description = models.TextField(blank=True, verbose_name='الوصف')
    active = models.BooleanField(default=True, verbose_name='نشط')
    members = models.ManyToManyField('auth.User', blank=True, related_name='council_departments', verbose_name='أعضاء القسم')
    def __str__(self): return self.name

class ComplaintCategory(models.Model):
    class Meta:
        verbose_name = 'تصنيف شكوى'
        verbose_name_plural = 'تصنيفات الشكاوى'

    name = models.CharField(max_length=120, unique=True, verbose_name='الاسم')
    default_days = models.PositiveIntegerField(default=7, verbose_name='مدة المعالجة الافتراضية بالأيام')
    active = models.BooleanField(default=True, verbose_name='نشط')
    def __str__(self): return self.name

class AuditLog(models.Model):
    class Meta:
        verbose_name = 'حدث تدقيق'
        verbose_name_plural = 'سجل التدقيق'

    actor = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL, verbose_name='الموظف')
    action = models.CharField(max_length=120, verbose_name='الإجراء')
    target_type = models.CharField(max_length=120, blank=True, verbose_name='نوع السجل')
    target_id = models.CharField(max_length=80, blank=True, verbose_name='معرف السجل')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='تفاصيل إضافية')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
