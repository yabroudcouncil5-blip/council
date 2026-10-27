from django.db import models

class Page(models.Model):
    class Meta:
        verbose_name = 'صفحة'
        verbose_name_plural = 'صفحات الموقع'

    def __str__(self):
        return self.title

    slug = models.SlugField(unique=True, verbose_name='الرابط المختصر')
    title = models.CharField(max_length=200, verbose_name='موضوع الشكوى')
    body = models.TextField(verbose_name='المحتوى')
    published = models.BooleanField(default=False, verbose_name='منشور')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخر تحديث')

class NewsArticle(models.Model):
    class Meta:
        verbose_name = 'خبر أو إعلان'
        verbose_name_plural = 'الأخبار والإعلانات'

    def __str__(self):
        return self.title

    title = models.CharField(max_length=200, verbose_name='موضوع الشكوى')
    body = models.TextField(verbose_name='المحتوى')
    featured_image = models.FileField(upload_to='news/', blank=True, null=True, verbose_name='الصورة الرئيسية')
    published = models.BooleanField(default=False, verbose_name='منشور')
    published_at = models.DateTimeField(blank=True, null=True, verbose_name='تاريخ النشر')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')

class DepartmentPage(models.Model):
    class Meta:
        verbose_name = 'صفحة قسم'
        verbose_name_plural = 'صفحات الأقسام'

    def __str__(self):
        return self.name

    name = models.CharField(max_length=160, verbose_name='الاسم')
    description = models.TextField(blank=True, verbose_name='الوصف')
    contact = models.CharField(max_length=255, blank=True, verbose_name='وسيلة التواصل')
    published = models.BooleanField(default=False, verbose_name='منشور')
