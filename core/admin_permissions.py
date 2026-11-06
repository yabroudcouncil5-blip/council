def _has_any(user, *permissions):
    return user.is_superuser or any(user.has_perm(permission) for permission in permissions)


def can_view_dashboard(request):
    return request.user.is_staff


def can_view_reports(request):
    from complaints.workflow import can_review
    return can_review(request.user) or _has_any(request.user, 'complaints.view_complaintassignment', 'complaints.view_complaint')


def can_view_complaints(request):
    from complaints.workflow import can_review, complaints_for
    return can_review(request.user) or complaints_for(request.user).exists()


def can_view_assignments(request):
    return _has_any(request.user, 'complaints.view_complaintassignment', 'complaints.add_complaintassignment')


def can_view_departments(request):
    return _has_any(request.user, 'core.view_department', 'core.change_department')


def can_view_executive_team(request):
    return _has_any(request.user, 'website.view_executivemember', 'website.change_executivemember')


def can_view_news(request):
    return _has_any(request.user, 'website.view_newsarticle', 'website.add_newsarticle')


def can_view_pages(request):
    return _has_any(request.user, 'website.view_page', 'website.change_page')


def can_view_council_settings(request):
    return _has_any(request.user, 'core.view_councilsettings', 'core.change_councilsettings')


def can_view_users(request):
    return _has_any(request.user, 'auth.view_user', 'auth.change_user')
