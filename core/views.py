from django.shortcuts import render

# Create your views here.
from django.http import JsonResponse
from django.db import connection
from django.http import FileResponse, Http404
from .models import CouncilSettings


def council_logo(request, filename):
    council = CouncilSettings.objects.filter(logo='council/logos/' + filename).first()
    if not council or not council.logo:
        raise Http404
    try:
        response = FileResponse(council.logo.open('rb'))
    except FileNotFoundError:
        raise Http404
    response['X-Content-Type-Options'] = 'nosniff'
    return response

def health(request):
    try:
        with connection.cursor() as cursor: cursor.execute('SELECT 1')
        database = 'ok'
    except Exception: database = 'unavailable'
    return JsonResponse({'ok': database == 'ok', 'database': database})
