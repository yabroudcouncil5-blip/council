from django.shortcuts import render

# Create your views here.
from django.http import JsonResponse
from django.db import connection
from django.http import FileResponse, Http404
from .models import CouncilSettings
from django.core.cache import cache
from django.http import HttpResponse
from django.utils.cache import get_conditional_response, patch_cache_control
from PIL import Image, ImageOps
from io import BytesIO
from hashlib import sha256


def council_logo(request, filename):
    council = CouncilSettings.objects.filter(logo='council/logos/' + filename).first()
    if not council or not council.logo:
        raise Http404
    thumbnail = request.GET.get('size') == '120'
    version = f'{council.logo.name}:{council.updated_at.isoformat()}:{thumbnail}:1'
    etag = '"' + sha256(version.encode()).hexdigest() + '"'
    response = get_conditional_response(request, etag=etag)
    if response is not None:
        response['ETag'] = etag
        patch_cache_control(response, public=True, max_age=86400)
        return response
    try:
        if thumbnail:
            key = 'council-logo:' + etag.strip('"')
            data = cache.get(key)
            if data is None:
                with council.logo.open('rb') as source, Image.open(source) as image:
                    image = ImageOps.exif_transpose(image)
                    image.thumbnail((120, 120), Image.Resampling.LANCZOS)
                    output = BytesIO()
                    image.convert('RGBA').save(output, 'WEBP', quality=90)
                    data = output.getvalue()
                cache.set(key, data, timeout=86400)
            response = HttpResponse(data, content_type='image/webp')
        else:
            response = FileResponse(council.logo.open('rb'))
    except FileNotFoundError:
        raise Http404
    response['ETag'] = etag
    patch_cache_control(response, public=True, max_age=86400)
    response['X-Content-Type-Options'] = 'nosniff'
    return response

def health(request):
    try:
        with connection.cursor() as cursor: cursor.execute('SELECT 1')
        database = 'ok'
    except Exception: database = 'unavailable'
    return JsonResponse({'ok': database == 'ok', 'database': database})
