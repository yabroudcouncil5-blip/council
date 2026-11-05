from .models import Complaint


def tracking_result(data):
    # Normalize copy/paste spacing, Arabic digits, and common reference separators.
    reference = data.get('reference', '').strip().translate(str.maketrans('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹–—', '01234567890123456789--')).upper()
    complaint = Complaint.objects.filter(reference=reference).first()
    if not complaint:
        return None
    labels = dict(Complaint.STATUS)
    publication = getattr(complaint, 'publication', None)
    is_public = bool(publication and publication.approved and publication.visibility in {'tracked', 'public'})
    public_events = list(complaint.status_history.order_by('created_at', 'pk'))
    known = {(event.status, event.created_at) for event in public_events}
    for assignment in complaint.assignments.select_related('department').order_by('assigned_at', 'pk'):
        if not any(event.status == 'assigned' and event.created_at >= assignment.assigned_at for event in public_events):
            public_events.append(type('PublicEvent', (), {
                'status': 'assigned',
                'public_message': f'تمت إحالة الشكوى إلى قسم {assignment.department.name}',
                'created_at': assignment.assigned_at,
            })())
    public_events.sort(key=lambda event: (event.created_at, getattr(event, 'pk', 0)))
    if not public_events:
        public_events.append(type('PublicEvent', (), {
            'status': 'submitted', 'public_message': 'تم استلام الشكوى', 'created_at': complaint.submitted_at,
        })())
    visible_status = complaint.get_status_display()
    if not is_public and complaint.status in {'completed', 'closed'}:
        visible_status = labels.get('final_review', 'قيد التحقق النهائي')
        public_events = [event for event in public_events if event.status not in {'completed', 'closed'}]
    evidence = []
    if is_public:
        evidence = [item.file.url for item in complaint.attachments.all() if item.file and item.visibility in {'tracked', 'public'}]
    result = {
        'reference': complaint.reference,
        'status': visible_status,
        'submitted_at': complaint.submitted_at.isoformat(),
        'timeline': [
            {'status': labels.get(item.status, item.status), 'public_message': item.public_message, 'created_at': item.created_at}
            for item in public_events
        ],
    }
    if evidence:
        result['evidence'] = evidence
    return result


def tracking_context(data):
    context = {'tracking_values': data}
    if 'reference' in data:
        context['tracking_result'] = tracking_result(data)
        if not context['tracking_result']:
            context['tracking_error'] = 'لم نعثر على شكوى بهذا الرقم. تأكد من الرقم المرجعي الذي حصلت عليه عند إرسال الشكوى، أو تواصل مع البلدية للمساعدة.'
    return context
