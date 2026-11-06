from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import PermissionDenied

# Create your views here.
import secrets
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .models import Complaint, ComplaintStatusHistory
from django.core.validators import validate_email
from website.views import ctx
from .tracking import tracking_result, tracking_context


def complaint_form(request):
    """Render the public complaint form."""
    from core.models import ComplaintCategory
    return render(request, 'complaints/submit.html', {
        **ctx(),
        'categories': ComplaintCategory.objects.filter(active=True).order_by('name'),
    })


@require_http_methods(['GET', 'POST'])
def tracking_form(request):
    """Render the public complaint tracking form."""
    data = request.POST if request.method == 'POST' else request.GET
    context = {**ctx(), **tracking_context(data)}
    template = 'complaints/includes/tracking_result.html' if request.GET.get('partial') == '1' else 'complaints/track.html'
    response = render(request, template, context)
    response['Cache-Control'] = 'no-store'
    return response

@require_http_methods(['POST'])
def submit_complaint(request):
    data = request.POST
    if not data.get('title') or not data.get('description'): return JsonResponse({'error':'العنوان والوصف مطلوبان'}, status=400)
    if data.get('email'):
        try: validate_email(data['email'])
        except Exception: return JsonResponse({'error':'البريد الإلكتروني غير صحيح'}, status=400)
    uploads = request.FILES.getlist('photos') or ([request.FILES['photo']] if request.FILES.get('photo') else [])
    if any(upload.size > 5 * 1024 * 1024 or upload.content_type not in {'image/jpeg','image/png','image/webp'} for upload in uploads): return JsonResponse({'error':'الصور يجب أن تكون JPEG أو PNG أو WebP وأقل من 5 ميغابايت لكل صورة'}, status=400)
    year = __import__('datetime').datetime.now().year
    reference = None
    for _ in range(10):
        candidate = f"YBC-{year}-{secrets.randbelow(900000)+100000:06d}"
        if not Complaint.objects.filter(reference=candidate).exists(): reference = candidate; break
    if not reference: return JsonResponse({'error':'تعذر إنشاء رقم مرجعي، حاول مجدداً'}, status=503)
    from core.models import ComplaintCategory
    category = ComplaintCategory.objects.filter(pk=data.get('category')).first() if data.get('category') else None
    complaint = Complaint.objects.create(reference=reference, tracking_hash='', title=data['title'], description=data['description'], name=data.get('name',''), phone=data.get('phone',''), email=data.get('email',''), category=category, location=data.get('location',''))
    from .models import ComplaintStatusHistory
    ComplaintStatusHistory.objects.create(complaint=complaint, status=complaint.status, public_message='تم استلام الشكوى')
    if uploads:
        from .models import ComplaintAttachment
        for upload in uploads: ComplaintAttachment.objects.create(complaint=complaint, file=upload, original_name=upload.name)
    return JsonResponse({'reference': complaint.reference, 'status': complaint.status}, status=201)

@require_http_methods(['GET', 'POST'])
def track_complaint(request):
    result = tracking_result(request.POST if request.method == 'POST' else request.GET)
    response = JsonResponse(result if result else {'error': 'بيانات التتبع غير صحيحة'}, status=200 if result else 404, json_dumps_params={'ensure_ascii': False})
    response['Cache-Control'] = 'no-store'
    return response

@require_http_methods(['POST'])
def recovery_request(request):
    from .models import RecoveryRequest
    if not request.POST.get('explanation'): return JsonResponse({'error':'يرجى شرح تفاصيل الشكوى'}, status=400)
    item = RecoveryRequest.objects.create(complaint_reference=request.POST.get('reference',''), explanation=request.POST['explanation'], contact=request.POST.get('contact',''))
    return JsonResponse({'id': item.id, 'status': item.status}, status=201)

@login_required
def review_queue(request):
    if not request.user.is_staff: return JsonResponse({'error':'غير مصرح'}, status=403)
    from .workflow import complaints_for
    queryset = complaints_for(request.user).order_by('-submitted_at')
    return JsonResponse({'complaints': list(queryset.values('id','reference','title','status','submitted_at'))})

@login_required
def staff_dashboard(request):
    if not request.user.is_staff: return JsonResponse({'error':'غير مصرح'}, status=403)
    from django.contrib import admin
    from django.db.models import Q
    from .models import ComplaintAssignment, InternalNotification
    assignments = ComplaintAssignment.objects.filter(
        Q(officer=request.user) | Q(department__members=request.user)
    ).select_related('complaint', 'department').distinct().order_by('-assigned_at')
    return render(request, 'staff/dashboard.html', {
        **admin.site.each_context(request), 'title': 'مهام القسم',
        'assignments': assignments,
        'notifications': InternalNotification.objects.filter(user=request.user, read=False)[:10],
    })

@login_required
@require_http_methods(['POST'])
@transaction.atomic
def assign_complaint(request):
    return _workflow_api(request, 'assign')

@login_required
@require_http_methods(['POST'])
@transaction.atomic
def action_submission(request):
    from .models import ComplaintAssignment
    assignment_id = request.POST.get('assignment_id', '')
    if not assignment_id.isdecimal():
        return JsonResponse({'error': 'اختر إحالة صحيحة'}, status=400)
    assignment = get_object_or_404(ComplaintAssignment, pk=assignment_id)
    return _workflow_api(request, 'start' if request.POST.get('action') == 'start' else 'submit', complaint_id=assignment.complaint_id)

@login_required
@require_http_methods(['POST'])
@transaction.atomic
def final_review(request):
    return _workflow_api(request, request.POST.get('decision'))

@login_required
@require_http_methods(['POST'])
def publish_resolution(request):
    return _workflow_api(request, 'publish')


def _workflow_api(request, action, complaint_id=None):
    from .workflow import WorkflowError, transition
    try:
        complaint, assignment = transition(
            complaint_id or request.POST.get('complaint_id'), request.user, action,
            department_id=request.POST.get('department_id'), assignment_id=request.POST.get('assignment_id'),
            internal_note=request.POST.get('internal_action') or request.POST.get('reason', ''),
            public_message=request.POST.get('public_message') or request.POST.get('summary', ''),
            evidence_ids=request.POST.getlist('evidence_ids'), uploads=request.FILES.getlist('evidence'),
            priority=request.POST.get('priority', 'medium'), due_at=request.POST.get('due_at'),
            version=request.POST.get('version'), confirm=request.POST.get('confirm') in {'1', 'on', 'true'},
        )
    except PermissionDenied:
        return JsonResponse({'error': 'غير مصرح بهذا الإجراء'}, status=403)
    except WorkflowError as error:
        return JsonResponse({'error': error.message}, status=error.status)
    except (Complaint.DoesNotExist, ValueError, TypeError):
        return JsonResponse({'error': 'بيانات الشكوى أو الإحالة غير صحيحة'}, status=400)
    return JsonResponse({'reference': complaint.reference, 'status': complaint.status,
                         'status_label': complaint.get_status_display(),
                         'assignment_id': assignment.pk if assignment else None}, status=201 if action in {'assign', 'submit', 'publish'} else 200)


@login_required
@require_http_methods(['POST'])
def complaint_transition(request, complaint_id):
    from django.contrib import admin, messages
    from .workflow import WorkflowError, complaints_for, transition, can_review, available_actions
    from .workflow_forms import ComplaintWorkflowForm
    complaint = get_object_or_404(complaints_for(request.user), pk=complaint_id)
    form = ComplaintWorkflowForm(request.POST, request.FILES, complaint=complaint, user=request.user)
    status = 400
    if form.is_valid():
        data = form.cleaned_data
        try:
            complaint, _ = transition(
                complaint.pk, request.user, data['action'],
                department_id=data['department'].pk if data.get('department') else None,
                internal_note=data.get('internal_note', ''), public_message=data.get('public_message', ''),
                priority=data.get('priority') or 'medium', due_at=data.get('due_at'),
                evidence_ids=[item.pk for item in data.get('evidence_ids', [])],
                uploads=data.get('evidence') or [],
                version=data['version'], confirm=data.get('confirm', False),
            )
        except WorkflowError as error:
            form.add_error(None, error.message)
            status = error.status
        else:
            messages.success(request, 'تم حفظ الإجراء وتحديث مرحلة الشكوى وسجل التتبع تلقائياً.')
            return redirect('admin:complaints_complaint_change', complaint.pk)
    return render(request, 'complaints/admin/workflow_error.html', {
        **admin.site.each_context(request), 'title': 'مراجعة الإجراء',
        'workflow_complaint': complaint, 'workflow_form': form,
        'workflow_actions': available_actions(request.user, complaint),
        'workflow_reviewer': can_review(request.user),
        'workflow_evidence': complaint.attachments.filter(source='staff'),
    }, status=status)


def complaint_evidence(request, attachment_id):
    """Serve previews in production too; private uploads require case access."""
    from django.http import FileResponse, Http404
    from pathlib import Path
    from .models import ComplaintAttachment
    from .workflow import complaints_for, TERMINAL
    item = get_object_or_404(ComplaintAttachment.objects.select_related('complaint'), pk=attachment_id)
    publication = getattr(item.complaint, 'publication', None)
    public = bool(item.source == 'staff' and item.visibility in {'public', 'tracked'}
                  and item.complaint.status in TERMINAL and publication and publication.approved
                  and publication.visibility in {'tracked', 'public'} and publication.published_at
                  and item.uploaded_at <= publication.published_at)
    if not public and not (request.user.is_authenticated and complaints_for(request.user).filter(pk=item.complaint_id).exists()):
        raise Http404
    content_types = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
                     '.webp': 'image/webp', '.gif': 'image/gif', '.pdf': 'application/pdf'}
    content_type = content_types.get(Path(item.file.name).suffix.lower(), 'application/octet-stream')
    if request.GET.get('preview') == '1' and content_type.startswith('image/'):
        from django.core.cache import cache
        from django.http import HttpResponse
        from hashlib import sha256
        from io import BytesIO
        from PIL import Image, ImageOps, UnidentifiedImageError
        key = 'evidence-preview:' + sha256(f'{item.pk}:{item.file.name}'.encode()).hexdigest()
        thumbnail = cache.get(key)
        if thumbnail is None:
            try:
                with item.file.open('rb') as source, Image.open(source) as image:
                    if image.width * image.height <= 20_000_000:
                        image = ImageOps.exif_transpose(image)
                        image.thumbnail((960, 960), Image.Resampling.LANCZOS)
                        output = BytesIO()
                        image.convert('RGB').save(output, 'WEBP', quality=78, method=4)
                        thumbnail = output.getvalue()
                        cache.set(key, thumbnail, 3600)
            except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError):
                pass
        if thumbnail:
            response = HttpResponse(thumbnail, content_type='image/webp')
            response['Cache-Control'] = 'private, no-store'
            response['X-Content-Type-Options'] = 'nosniff'
            return response
    try:
        response = FileResponse(item.file.open('rb'), content_type=content_type,
                                as_attachment=content_type == 'application/octet-stream',
                                filename=item.original_name or Path(item.file.name).name)
    except (FileNotFoundError, ValueError):
        raise Http404('ملف الدليل غير متاح في التخزين.')
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    response['X-Frame-Options'] = 'SAMEORIGIN'
    return response

def public_resolutions(request):
    from .models import ComplaintPublication
    rows=ComplaintPublication.objects.filter(approved=True, visibility='public', complaint__status__in=['completed', 'closed']).select_related('complaint')
    return JsonResponse({'results':[{'reference':p.complaint.reference,'title':p.complaint.title,'summary':p.summary,'published_at':p.published_at.isoformat() if p.published_at else None} for p in rows]})

@login_required
def complaint_workflow(request):
    """Old workspace URLs now use the canonical complaint list/detail pages."""
    if not request.user.is_staff:
        return JsonResponse({'error': 'غير مصرح'}, status=403)
    complaint_id = request.GET.get('complaint') or request.POST.get('complaint_id')
    if complaint_id and complaint_id.isdecimal():
        return redirect('admin:complaints_complaint_change', complaint_id)
    return redirect('admin:complaints_complaint_changelist')

@login_required
def dashboard_report(request):
    if not request.user.is_staff:
        return JsonResponse({'error': 'غير مصرح'}, status=403)
    from django.contrib import admin
    from django.db.models import Count, Q
    from django.utils import timezone
    from core.models import Department
    from .models import ComplaintAssignment, InternalNotification

    now = timezone.now()
    counts = dict(Complaint.objects.values_list('status').annotate(total=Count('id')))
    assignment_counts = dict(ComplaintAssignment.objects.values_list('status').annotate(total=Count('id')))
    overdue = ComplaintAssignment.objects.filter(due_at__lt=now).exclude(status__in=['approved', 'cancelled'])
    total = sum(counts.values())
    completed = counts.get('completed', 0)
    assignment_labels = [
        ('assigned', 'مسندة'), ('in_progress', 'قيد التنفيذ'),
        ('submitted', 'بانتظار الاعتماد'), ('approved', 'معتمدة'),
        ('returned', 'معادة للاستكمال'), ('cancelled', 'ملغاة'),
    ]
    department_rows = Department.objects.annotate(
        total=Count('complaintassignment'),
        approved=Count('complaintassignment', filter=Q(complaintassignment__status='approved')),
        overdue=Count('complaintassignment', filter=Q(complaintassignment__due_at__lt=now) & ~Q(complaintassignment__status__in=['approved', 'cancelled'])),
    ).order_by('-total', 'name')
    context = {
        **admin.site.each_context(request),
        'title': 'التقارير والمتابعة',
        'total_complaints': total,
        'open_complaints': total - completed - counts.get('closed', 0),
        'completion_rate': round(completed * 100 / total) if total else 0,
        'total_assignments': sum(assignment_counts.values()),
        'overdue_count': overdue.count(),
        'unread_notifications': InternalNotification.objects.filter(user=request.user, read=False).count(),
        'complaint_rows': [{'label': label, 'status': status, 'count': counts.get(status, 0),
                            'percent': round(counts.get(status, 0) * 100 / total) if total else 0}
                           for status, label in Complaint.STATUS],
        'assignment_rows': [{'label': dict(assignment_labels).get(status, status), 'count': count}
                            for status, count in sorted(assignment_counts.items())],
        'departments': department_rows,
        'overdue_assignments': overdue.select_related('complaint', 'department', 'officer').order_by('due_at')[:20],
        'generated_at': now,
    }
    return render(request, 'staff/reports.html', context)
