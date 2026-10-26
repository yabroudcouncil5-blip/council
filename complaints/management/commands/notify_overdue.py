from django.core.management.base import BaseCommand
from django.utils import timezone
from complaints.models import ComplaintAssignment, InternalNotification

class Command(BaseCommand):
    help = 'Create notifications for overdue active assignments.'
    def handle(self, *args, **options):
        count=0
        for assignment in ComplaintAssignment.objects.filter(due_at__lt=timezone.now()).exclude(status__in=['approved','cancelled']):
            if assignment.officer_id:
                InternalNotification.objects.get_or_create(user_id=assignment.officer_id, complaint=assignment.complaint, message=f'المهمة {assignment.complaint.reference} متأخرة')
                count += 1
        self.stdout.write(self.style.SUCCESS(f'Created or confirmed {count} overdue notifications'))
