from django.shortcuts import render

# Create your views here.
import secrets
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .models import Complaint
from django.core.validators import validate_email
from website.views import ctx


def tracking_result(data):
    # Normalize copy/paste spacing, Arabic digits, and common reference separators.
    reference = data.get('reference', '').strip().translate(str.maketrans('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹–—', '01234567890123456789--')).upper()
    complaint = Complaint.objects.filter(reference=reference).first()
    if not complaint:
        return None
    labels = dict(Complaint.STATUS)
    return {
        'reference': complaint.reference,
        'status': complaint.get_status_display(),
        'submitted_at': complaint.submitted_at.isoformat(),
        'timeline': [
            {'status': labels.get(item.status, item.status), 'public_message': item.public_message, 'created_at': item.created_at}
            for item in complaint.status_history.order_by('created_at', 'pk')
        ],
    }


def complaint_form(request):
    """Render the public complaint form."""
    from core.models import ComplaintCategory
    return render(request, 'complaints/submit.html', {
        **ctx(),
        'categories': ComplaintCategory.objects.filter(active=True).order_by('name'),
    })


def tracking_form(request):
    """Render the public complaint tracking form."""
    context = {**ctx(), 'tracking_values': request.POST}
    if request.method == 'POST':
        context['tracking_result'] = tracking_result(request.POST)
        if not context['tracking_result']:
            context['tracking_error'] = 'لم نعثر على شكوى بهذا الرقم. تأكد من الرقم المرجعي الذي حصلت عليه عند إرسال الشكوى، أو تواصل مع البلدية للمساعدة.'
    response = render(request, 'complaints/track.html', context)
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

@require_http_methods(['POST'])
def track_complaint(request):
    result = tracking_result(request.POST)
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
    queryset=Complaint.objects.order_by('-submitted_at')
    if request.user.groups.filter(name='Department Officer').exists(): queryset=queryset.filter(assignments__officer=request.user).distinct()
    return JsonResponse({'complaints': list(queryset.values('id','reference','title','status','submitted_at'))})

@login_required
def staff_dashboard(request):
    if not request.user.is_staff: return JsonResponse({'error':'غير مصرح'}, status=403)
    from .models import ComplaintAssignment, InternalNotification
    assignments = ComplaintAssignment.objects.filter(officer=request.user).select_related('complaint','department')
    return render(request, 'staff/dashboard.html', {'assignments': assignments, 'notifications': InternalNotification.objects.filter(user=request.user, read=False)[:10]})

@login_required
@require_http_methods(['POST'])
@transaction.atomic
def assign_complaint(request):
    if not request.user.is_staff: return JsonResponse({'error':'غير مصرح'}, status=403)
    from core.models import Department
    from .models import ComplaintAssignment, InternalNotification
    complaint=Complaint.objects.get(pk=request.POST['complaint_id']); department=Department.objects.get(pk=request.POST['department_id'])
    assignment=ComplaintAssignment.objects.create(complaint=complaint, department=department, officer_id=request.POST.get('officer_id') or None, priority=request.POST.get('priority','medium'))
    complaint.status='assigned'; complaint.save(update_fields=['status','updated_at'])
    if assignment.officer_id: InternalNotification.objects.create(user_id=assignment.officer_id, complaint=complaint, message=f'تم إسناد الشكوى {complaint.reference} إليك')
    return JsonResponse({'assignment_id':assignment.id,'status':assignment.status}, status=201)

@login_required
@require_http_methods(['POST'])
@transaction.atomic
def action_submission(request):
    from .models import AssignmentAction, ComplaintAssignment
    assignment=ComplaintAssignment.objects.select_related('complaint').get(pk=request.POST['assignment_id'])
    if assignment.officer_id != request.user.id and not request.user.is_superuser and not request.user.groups.filter(name='Department Manager').exists(): return JsonResponse({'error':'غير مصرح'}, status=403)
    action=AssignmentAction.objects.create(assignment=assignment, actor=request.user, internal_action=request.POST.get('internal_action',''), public_message=request.POST.get('public_message',''))
    assignment.status='submitted'; assignment.save(update_fields=['status'])
    assignment.complaint.status='final_review'; assignment.complaint.save(update_fields=['status','updated_at'])
    return JsonResponse({'action_id':action.id,'status':assignment.status}, status=201)

@login_required
@require_http_methods(['POST'])
@transaction.atomic
def final_review(request):
    if not request.user.is_staff: return JsonResponse({'error':'غير مصرح'}, status=403)
    from .models import ComplaintAssignment, ComplaintReview, ComplaintPublication
    complaint=Complaint.objects.get(pk=request.POST['complaint_id']); decision=request.POST['decision']; assignment=ComplaintAssignment.objects.filter(complaint=complaint, pk=request.POST.get('assignment_id')).first() if request.POST.get('assignment_id') else None
    if assignment and decision == 'approved': assignment.status='approved'; assignment.save(update_fields=['status'])
    if assignment and decision == 'returned': assignment.status='returned'; assignment.save(update_fields=['status'])
    ComplaintReview.objects.create(complaint=complaint, assignment=assignment, reviewer=request.user, decision=decision, reason=request.POST.get('reason',''))
    if decision == 'closed':
        if complaint.assignments.exclude(status__in=['approved','cancelled']).exists(): return JsonResponse({'error':'لا يمكن إغلاق الشكوى قبل اعتماد جميع المهام'}, status=409)
        complaint.status='completed'; complaint.save(update_fields=['status','updated_at'])
    return JsonResponse({'status':complaint.status})

@login_required
@require_http_methods(['POST'])
def publish_resolution(request):
    if not request.user.is_staff: return JsonResponse({'error':'غير مصرح'}, status=403)
    from .models import ComplaintPublication
    complaint=Complaint.objects.get(pk=request.POST['complaint_id']); publication, _=ComplaintPublication.objects.update_or_create(complaint=complaint, defaults={'summary':request.POST.get('summary',''),'visibility':request.POST.get('visibility','private'),'approved':True,'approved_by':request.user})
    return JsonResponse({'publication_id':publication.id,'approved':publication.approved}, status=201)

def public_resolutions(request):
    from .models import ComplaintPublication
    rows=ComplaintPublication.objects.filter(approved=True, visibility='public', complaint__status='completed').select_related('complaint')
    return JsonResponse({'results':[{'reference':p.complaint.reference,'title':p.complaint.title,'summary':p.summary,'published_at':p.published_at.isoformat() if p.published_at else None} for p in rows]})

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
