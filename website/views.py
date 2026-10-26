from django.shortcuts import render
from .models import Page, NewsArticle, DepartmentPage
from core.models import CouncilSettings, Department
def ctx(): return {'council': CouncilSettings.objects.first() or {'name':'بلدية يبرود','description':'خدمة المدينة وأهلها بشفافية ومسؤولية.','phone':'011-0000000','email':'info@yabroud.gov.sy'}}
def home(request): return render(request,'website/home.html',{**ctx(),'news':NewsArticle.objects.filter(published=True)[:3]})
def simple(request, slug):
    item=Page.objects.filter(slug=slug,published=True).first(); fallback={'about':('عن البلدية','تعمل بلدية يبرود على تقديم الخدمات البلدية وتحسين المدينة.'),'services':('الخدمات البلدية','النظافة والبيئة، الطرق والإنارة، المياه والصرف الصحي، والخدمات الإدارية.')}; title,body=(item.title,item.body) if item else fallback.get(slug,('بلدية يبرود','المحتوى قيد التحديث.')); return render(request,'website/page.html',{**ctx(),'title':title,'body':body})
def news(request): return render(request,'website/news.html',{**ctx(),'news':NewsArticle.objects.filter(published=True)})
def departments(request): return render(request,'website/departments.html',{**ctx(),'departments':Department.objects.filter(active=True)})
def contact(request): return render(request,'website/contact.html',ctx())
