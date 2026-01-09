# accounts/urls/admin_urls.py
from django.urls import path
from accounts.views.administrator_views import (
    # Dashboard Views
    dashboard,
    analytics,
    reports,
    
    # Academic Management
    educational_levels,
    educational_levels_list,
    educational_levels_crud,
    academic_years,
    academic_years_list,
    academic_years_crud,
    terms,
    terms_list,
    terms_crud,
    subjects,
    subjects_list,
    subjects_crud,
    class_levels,
    class_levels_list,
    class_levels_crud,
    stream_classes,
    stream_classes_list,
    stream_classes_crud,
    
    # Student Management
    students_list,
    students_add,
    students_by_class,
    student_status,
    parents_list,
    previous_schools,
    
    # Staff Management
    staff_list,
    staff_add,
    staff_roles,
    staff_assignments,
    
    # User Management
    users_list,
    users_add,
    users_roles,
    permissions,
    user_activity,
    
    # System Settings
    system_config,
    email_settings,
    sms_settings,
    notifications,
    backup,
    
    # Security & Logs
    audit_logs,
    login_history,
    security_settings,
    api_settings,
    
    # Reports & Analytics
    financial_reports,
    academic_reports,
    attendance_reports,
    custom_reports,
    export_data,
    
    # Help & Support
    documentation,
    faq,
    support_tickets,
    system_status,
    
    # Profile & Account Management
    profile_view,
    profile_update,
    profile_picture_update,
    profile_security,
    change_password,
    two_factor_settings,
    account_preferences,
    session_management,
    delete_account_request,
    activity_logs,
    
    # AJAX Endpoints
    ajax_get_streams,
    ajax_get_student_details,
)



urlpatterns = [
    # Dashboard URLs
    path('dashboard/', dashboard, name='admin_dashboard'),
    path('analytics/', analytics, name='admin_analytics'),
    path('reports/', reports, name='admin_reports'),
    
    # Academic Management URLs
    path('academic/levels/', educational_levels_list, name='admin_educational_levels_list'),
    path('academic/levels/crud/', educational_levels_crud, name='admin_educational_levels_crud'),
    path('academic/levels/legacy/', educational_levels, name='admin_educational_levels'),  # Legacy redirect
    
    path('academic/years/', academic_years_list, name='admin_academic_years_list'),
    path('academic/years/crud/', academic_years_crud, name='admin_academic_years_crud'),
    path('academic/years/legacy/', academic_years, name='admin_academic_years'),  # Legacy redirect
    
    path('academic/terms/', terms_list, name='admin_terms_list'),
    path('academic/terms/crud/', terms_crud, name='admin_terms_crud'),
    path('academic/terms/legacy/', terms, name='admin_terms'),  # Legacy redirect
    
    path('academic/subjects/', subjects_list, name='admin_subjects_list'),
    path('academic/subjects/crud/', subjects_crud, name='admin_subjects_crud'),
    path('academic/subjects/legacy/', subjects, name='admin_subjects'),  # Legacy redirect
    
    path('academic/classes/', class_levels_list, name='admin_class_levels_list'),
    path('academic/classes/crud/', class_levels_crud, name='admin_class_levels_crud'),
    path('academic/classes/legacy/', class_levels, name='admin_class_levels'),  # Legacy redirect
    
    path('academic/streams/', stream_classes_list, name='admin_stream_classes_list'),
    path('academic/streams/crud/', stream_classes_crud, name='admin_stream_classes_crud'),
    path('academic/streams/legacy/', stream_classes, name='admin_stream_classes'),  # Legacy redirect
    
    # Student Management URLs
    path('students/', students_list, name='admin_students_list'),
    path('students/add/', students_add, name='admin_students_add'),
    path('students/class/', students_by_class, name='admin_students_by_class'),
    path('students/status/', student_status, name='admin_student_status'),
    path('students/parents/', parents_list, name='admin_parents_list'),
    path('students/previous-schools/', previous_schools, name='admin_previous_schools'),
    
    # Staff Management URLs
    path('staff/', staff_list, name='admin_staff_list'),
    path('staff/add/', staff_add, name='admin_staff_add'),
    path('staff/roles/', staff_roles, name='admin_staff_roles'),
    path('staff/assignments/', staff_assignments, name='admin_staff_assignments'),
    
    # User Management URLs
    path('users/', users_list, name='admin_users_list'),
    path('users/add/', users_add, name='admin_users_add'),
    path('users/roles/', users_roles, name='admin_users_roles'),
    path('users/permissions/', permissions, name='admin_permissions'),
    path('users/activity/', user_activity, name='admin_user_activity'),
    
    # System Settings URLs
    path('settings/system/', system_config, name='admin_system_config'),
    path('settings/email/', email_settings, name='admin_email_settings'),
    path('settings/sms/', sms_settings, name='admin_sms_settings'),
    path('settings/notifications/', notifications, name='admin_notifications'),
    path('settings/backup/', backup, name='admin_backup'),
    
    # Security & Logs URLs
    path('security/audit-logs/', audit_logs, name='admin_audit_logs'),
    path('security/login-history/', login_history, name='admin_login_history'),
    path('security/settings/', security_settings, name='admin_security_settings'),
    path('security/api/', api_settings, name='admin_api_settings'),
    
    # Reports & Analytics URLs
    path('reports/financial/', financial_reports, name='admin_financial_reports'),
    path('reports/academic/', academic_reports, name='admin_academic_reports'),
    path('reports/attendance/', attendance_reports, name='admin_attendance_reports'),
    path('reports/custom/', custom_reports, name='admin_custom_reports'),
    path('reports/export/', export_data, name='admin_export_data'),
    
    # Help & Support URLs
    path('help/documentation/', documentation, name='admin_documentation'),
    path('help/faq/', faq, name='admin_faq'),
    path('help/support/', support_tickets, name='admin_support_tickets'),
    path('help/system-status/', system_status, name='admin_system_status'),
    
    # Profile & Account Management URLs
    path('account/profile/', profile_view, name='admin_profile'),
    path('account/profile/update/', profile_update, name='admin_profile_update'),
    path('account/profile/picture/', profile_picture_update, name='admin_profile_picture_update'),
    path('account/security/', profile_security, name='admin_security'),
    path('account/change-password/', change_password, name='admin_change_password'),
    path('account/two-factor/', two_factor_settings, name='admin_two_factor_settings'),
    path('account/preferences/', account_preferences, name='admin_preferences'),
    path('account/sessions/', session_management, name='admin_session_management'),
    path('account/delete-request/', delete_account_request, name='admin_delete_request'),
    path('account/activity-logs/', activity_logs, name='admin_activity_logs'),
    
    # AJAX/API Endpoints
    path('ajax/get-streams/', ajax_get_streams, name='admin_ajax_get_streams'),
    path('ajax/get-student-details/', ajax_get_student_details, name='admin_ajax_get_student_details'),
]