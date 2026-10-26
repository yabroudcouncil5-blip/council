from django.shortcuts import render

# Create your views here.
from django.http import JsonResponse
from django.db import connection

def health(request):
    try:
        with connection.cursor() as cursor: cursor.execute('SELECT 1')
        database = 'ok'
    except Exception: database = 'unavailable'
    return JsonResponse({'ok': database == 'ok', 'database': database})
