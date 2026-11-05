from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import RelatedFieldWidgetWrapper
from django.contrib.auth.models import Permission, User
from django.test import RequestFactory, TestCase

from complaints.models import Complaint, ComplaintAssignment, ComplaintReview
from core.models import ComplaintCategory, Department


class AdminSelectionSimplificationTests(TestCase):
    """Related selectors must not double as reference-data management tools."""

    @classmethod
    def setUpTestData(cls):
        cls.superadmin = User.objects.create_superuser('reference-admin', password='test-password')
        cls.reviewer = User.objects.create_user('reference-reviewer', is_staff=True)
        cls.reviewer.user_permissions.add(*Permission.objects.filter(
            content_type__app_label__in=['core', 'complaints', 'auth'],
        ))
        cls.department = Department.objects.create(name='الطرق والإنارة')
        cls.department.members.add(cls.reviewer)
        cls.category = ComplaintCategory.objects.create(name='إنارة')
        cls.complaint = Complaint.objects.create(
            reference='YBC-SELECTORS-1', title='مصباح معطل',
            description='تفاصيل الشكوى', tracking_hash='', category=cls.category,
        )

    def request_for(self, user):
        request = RequestFactory().get('/admin/')
        request.user = user
        return request

    def assert_selection_only(self, field):
        widget = field.widget
        if isinstance(widget, RelatedFieldWidgetWrapper):
            for operation in ('add', 'change', 'delete', 'view'):
                self.assertFalse(getattr(widget, f'can_{operation}_related'))

    def test_complaint_and_assignment_selectors_have_no_related_shortcuts(self):
        for user in (self.superadmin, self.reviewer):
            request = self.request_for(user)
            for model, obj, names in (
                (Complaint, self.complaint, ('category',)),
                (ComplaintAssignment, None, ('complaint', 'department')),
            ):
                with self.subTest(user=user.username, model=model.__name__):
                    form = admin.site._registry[model].get_form(request, obj)()
                    for name in names:
                        self.assert_selection_only(form.fields[name])

    def test_inline_assignment_choices_are_validated_and_selectors_are_simple(self):
        request = self.request_for(self.superadmin)
        complaint_admin = admin.site._registry[Complaint]
        inline = next(item for item in complaint_admin.get_inline_instances(request, self.complaint)
                      if item.model is ComplaintAssignment)
        form = inline.get_formset(request, self.complaint).form()
        self.assert_selection_only(form.fields['department'])
        for name in ('status', 'priority'):
            self.assertIsInstance(form.fields[name], forms.ChoiceField)
            self.assertTrue(list(form.fields[name].choices))
        self.assertEqual(form.fields['due_at'].widget.input_type, 'datetime-local')

    def test_rendered_complaint_has_no_related_record_management_links(self):
        self.client.force_login(self.superadmin)
        response = self.client.get(f'/admin/complaints/complaint/{self.complaint.pk}/change/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'related-widget-wrapper-link')

    def test_only_superadmin_can_mutate_reference_records_even_with_granted_permissions(self):
        self.client.force_login(self.reviewer)
        for model, obj, data in (
            ('department', self.department, {'name': 'تعديل غير مسموح', 'description': '', 'active': 'on'}),
            ('complaintcategory', self.category, {'name': 'تعديل غير مسموح', 'default_days': 7, 'active': 'on'}),
        ):
            original_name = obj.name
            with self.subTest(model=model):
                base = f'/admin/core/{model}/'
                self.assertEqual(self.client.post(base + 'add/', data).status_code, 403)
                self.assertEqual(self.client.post(base + f'{obj.pk}/change/', data).status_code, 403)
                self.assertEqual(self.client.post(base + f'{obj.pk}/delete/', {'post': 'yes'}).status_code, 403)
                obj.refresh_from_db()
                self.assertEqual(obj.name, original_name)

    def test_authorized_staff_can_view_existing_reference_records(self):
        self.client.force_login(self.reviewer)
        for model, obj in (('department', self.department), ('complaintcategory', self.category)):
            with self.subTest(model=model):
                response = self.client.get(f'/admin/core/{model}/{obj.pk}/change/')
                self.assertContains(response, obj.name)
                self.assertNotContains(response, 'name="_save"')

    def test_superadmin_manages_reference_records_on_dedicated_pages(self):
        self.client.force_login(self.superadmin)
        for model, model_class, data in (
            ('department', Department, {'name': 'قسم جديد', 'description': '', 'active': 'on'}),
            ('complaintcategory', ComplaintCategory, {'name': 'تصنيف جديد', 'default_days': 5, 'active': 'on'}),
        ):
            with self.subTest(model=model):
                base = f'/admin/core/{model}/'
                self.assertEqual(self.client.post(base + 'add/', data).status_code, 302)
                created = model_class.objects.get(name=data['name'])
                changed = {**data, 'name': data['name'] + ' محدث'}
                self.assertEqual(self.client.post(base + f'{created.pk}/change/', changed).status_code, 302)
                created.refresh_from_db()
                self.assertEqual(created.name, changed['name'])
                self.assertEqual(self.client.post(base + f'{created.pk}/delete/', {'post': 'yes'}).status_code, 302)
                self.assertFalse(model_class.objects.filter(pk=created.pk).exists())

    def test_reference_view_access_is_not_granted_to_unprivileged_staff(self):
        limited = User.objects.create_user('reference-limited', is_staff=True)
        self.client.force_login(limited)
        for model in ('department', 'complaintcategory'):
            with self.subTest(model=model):
                self.assertEqual(self.client.get(f'/admin/core/{model}/').status_code, 403)

    def test_staff_can_still_assign_an_existing_department_without_changing_its_definition(self):
        request = self.request_for(self.reviewer)
        form_class = admin.site._registry[ComplaintAssignment].get_form(request)
        form = form_class(data={
            'complaint': self.complaint.pk, 'department': self.department.pk,
            'status': 'assigned', 'priority': 'medium', 'due_at': '',
        })
        self.assertTrue(form.is_valid(), form.errors)
        assignment = form.save()
        self.assertEqual(assignment.department_id, self.department.pk)
        self.assertIsNone(assignment.officer_id)
        self.department.refresh_from_db()
        self.assertEqual(self.department.name, 'الطرق والإنارة')

    def test_new_inline_review_uses_current_user_and_preserves_existing_reviewer(self):
        request = self.request_for(self.reviewer)
        complaint_admin = admin.site._registry[Complaint]
        inline = next(item for item in complaint_admin.get_inline_instances(request, self.complaint)
                      if item.model is ComplaintReview)
        formset_class = inline.get_formset(request, self.complaint)
        prefix = formset_class.get_default_prefix()
        formset = formset_class(data={
            f'{prefix}-TOTAL_FORMS': '1', f'{prefix}-INITIAL_FORMS': '0',
            f'{prefix}-MIN_NUM_FORMS': '0', f'{prefix}-MAX_NUM_FORMS': '1000',
            f'{prefix}-0-decision': 'approved', f'{prefix}-0-reason': 'تم التحقق',
            # A forged reviewer value must not be accepted from the browser.
            f'{prefix}-0-reviewer': self.superadmin.pk,
        }, instance=self.complaint)
        self.assertTrue(formset.is_valid(), formset.errors)
        formset.save()
        review = self.complaint.reviews.get()
        self.assertEqual(review.reviewer_id, self.reviewer.pk)
        self.assertNotIn('reviewer', formset.forms[0].fields)

        other_request = self.request_for(self.superadmin)
        editing_class = inline.get_formset(other_request, self.complaint)
        editing = editing_class(data={
            f'{prefix}-TOTAL_FORMS': '1', f'{prefix}-INITIAL_FORMS': '1',
            f'{prefix}-MIN_NUM_FORMS': '0', f'{prefix}-MAX_NUM_FORMS': '1000',
            f'{prefix}-0-id': review.pk, f'{prefix}-0-decision': 'approved',
            f'{prefix}-0-reason': 'ملاحظة إضافية', f'{prefix}-0-reviewer': self.superadmin.pk,
        }, instance=self.complaint)
        self.assertTrue(editing.is_valid(), editing.errors)
        editing.save()
        review.refresh_from_db()
        self.assertEqual(review.reviewer_id, self.reviewer.pk)
