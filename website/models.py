from django.db import models


class ContentImage(models.Model):
    image = models.ImageField(upload_to='website/images/')
    created_at = models.DateTimeField(auto_now_add=True)

class ExecutiveMember(models.Model):
    class Meta:
        verbose_name = 'عضو الفريق التنفيذي'
        verbose_name_plural = 'الفريق التنفيذي'
        ordering = ('display_order', 'id')

    def __str__(self):
        return self.name

    name = models.CharField(max_length=160, verbose_name='الاسم')
    role = models.CharField(max_length=180, verbose_name='المسمى الوظيفي')
    bio = models.TextField(verbose_name='نبذة قصيرة')
    photo = models.ImageField(upload_to='council/team/', blank=True, verbose_name='صورة العضو')
    display_order = models.PositiveIntegerField(default=0, verbose_name='ترتيب العرض')
    active = models.BooleanField(default=True, verbose_name='ظاهر على الموقع')

class Page(models.Model):
    class Meta:
        verbose_name = 'صفحة'
        verbose_name_plural = 'صفحات الموقع'

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return '/' + self.slug + '/' if self.slug in {'about', 'services'} else '/pages/' + self.slug + '/'

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
