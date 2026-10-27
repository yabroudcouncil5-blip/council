from .models import Complaint


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


def tracking_context(data):
    context = {'tracking_values': data}
    if 'reference' in data:
        context['tracking_result'] = tracking_result(data)
        if not context['tracking_result']:
            context['tracking_error'] = 'لم نعثر على شكوى بهذا الرقم. تأكد من الرقم المرجعي الذي حصلت عليه عند إرسال الشكوى، أو تواصل مع البلدية للمساعدة.'
    return context
