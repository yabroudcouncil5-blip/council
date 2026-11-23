from django.shortcuts import render, get_object_or_404
from .models import Page, NewsArticle, DepartmentPage, ExecutiveMember
from core.models import CouncilSettings, Department
from django.contrib import admin
from django.core.files.base import ContentFile
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.http import require_POST, require_safe
from PIL import Image, UnidentifiedImageError
from io import BytesIO
import uuid
import warnings
from .models import ContentImage
from complaints.tracking import tracking_context


@admin.site.admin_view
@require_POST
def upload_editor_image(request):
    if not any(request.user.has_perm('website.' + permission) for permission in ['add_page', 'change_page', 'add_newsarticle', 'change_newsarticle']):
        return JsonResponse({'error': 'لا تملك صلاحية تعديل محتوى الموقع.'}, status=403)
    upload = request.FILES.get('image')
    if not upload or upload.size > 5 * 1024 * 1024:
        return JsonResponse({'error': 'اختر صورة لا يزيد حجمها عن 5 ميغابايت.'}, status=400)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            image = Image.open(upload)
            if image.format not in {'JPEG', 'PNG', 'WEBP'} or image.width * image.height > 20_000_000:
                raise ValueError
            from PIL import ImageOps
            image = ImageOps.exif_transpose(image)
            image.thumbnail((2400, 2400))
            output = BytesIO()
            image.convert('RGBA' if 'A' in image.getbands() else 'RGB').save(output, 'WEBP', quality=88)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        return JsonResponse({'error': 'ارفع صورة PNG أو JPEG أو WebP سليمة، بأبعاد لا تتجاوز 20 مليون بكسل.'}, status=400)
    asset = ContentImage.objects.create(image=ContentFile(output.getvalue(), name=uuid.uuid4().hex + '.webp'))
    return JsonResponse({'url': '/website-images/' + asset.image.name.rsplit('/', 1)[-1]}, status=201)


def content_image(request, filename):
    asset = ContentImage.objects.filter(image='website/images/' + filename).first()
    if not asset:
        raise Http404
    try:
        response = FileResponse(asset.image.open('rb'), content_type='image/webp')
    except FileNotFoundError:
        raise Http404
    response['X-Content-Type-Options'] = 'nosniff'
    return response


def page(request, slug):
    item = get_object_or_404(Page, slug=slug, published=True)
    return render(request, 'website/page.html', {**ctx(), 'title': item.title, 'body': item.body})
def ctx():
    footer_pages = list(Page.objects.filter(published=True, show_in_footer=True).only('slug', 'title').order_by('title'))
    return {
        'council': CouncilSettings.objects.order_by('-updated_at').first() or {
            'name': 'بلدية يبرود', 'description': 'خدمة المدينة وأهلها بشفافية ومسؤولية.',
            'phone': '011-0000000', 'email': 'info@yabroud.gov.sy',
        },
        'footer_pages': footer_pages,
        'show_services_shortcuts': any(item.slug == 'services' for item in footer_pages),
    }


def home(request):
    context = {**ctx(), 'news': NewsArticle.objects.filter(published=True)[:3], **tracking_context(request.GET)}
    response = render(request, 'website/home.html', context)
    if 'reference' in request.GET:
        response['Cache-Control'] = 'no-store'
    return response

def about(request):
    return render(request, 'website/about.html', {
        **ctx(), 'city_page': Page.objects.filter(slug='about', published=True).first(),
    })


def news(request): return render(request,'website/news.html',{**ctx(),'news':NewsArticle.objects.filter(published=True)})
def news_detail(request, pk):
    item = get_object_or_404(NewsArticle, pk=pk, published=True)
    return render(request, 'website/news_detail.html', {**ctx(), 'item': item})


@require_safe
def news_image(request, pk):
    article = get_object_or_404(NewsArticle, pk=pk, published=True)
    return public_image_response(article.featured_image, 'news/')


@require_safe
def executive_member_photo(request, pk):
    member = get_object_or_404(ExecutiveMember, pk=pk, active=True)
    return public_image_response(member.photo, 'council/team/')


def public_image_response(field, directory):
    if not field or not field.name.startswith(directory):
        raise Http404
    try:
        stream = field.open('rb')
    except FileNotFoundError:
        raise Http404 from None

    try:
        with Image.open(stream, formats=('JPEG', 'PNG', 'WEBP', 'GIF')) as image:
            content_type = Image.MIME[image.format]
            image.verify()
        stream.seek(0)
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        stream.close()
        raise Http404 from None

    response = FileResponse(stream, content_type=content_type)
    response['X-Content-Type-Options'] = 'nosniff'
    return response


def departments(request): return render(request,'website/departments.html',{**ctx(),'departments':Department.objects.filter(active=True)})
def council(request):
    members = list(ExecutiveMember.objects.filter(active=True))
    for member in members:
        photo = member.photo
        member.has_public_photo = bool(
            photo and photo.name.startswith('council/team/') and photo.storage.exists(photo.name)
        )
    return render(request, 'website/council.html', {**ctx(), 'executive_members': members})

def contact(request): return render(request,'website/contact.html',ctx())
