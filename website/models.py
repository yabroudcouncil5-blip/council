from django.db import models

class Page(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=200)
    body = models.TextField()
    published = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

class NewsArticle(models.Model):
    title = models.CharField(max_length=200)
    body = models.TextField()
    featured_image = models.FileField(upload_to='news/', blank=True, null=True)
    published = models.BooleanField(default=False)
    published_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class DepartmentPage(models.Model):
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    contact = models.CharField(max_length=255, blank=True)
    published = models.BooleanField(default=False)
