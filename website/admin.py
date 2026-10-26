from django.contrib import admin
from .models import Page, NewsArticle, DepartmentPage
admin.site.register([Page, NewsArticle, DepartmentPage])
