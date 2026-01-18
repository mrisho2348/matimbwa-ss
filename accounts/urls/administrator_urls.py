# accounts/urls/admin_urls.py
from django.urls import path
from accounts.views.administrator_views import *


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
        path('api/class-levels/', get_class_levels, name='get_class_levels'),
    path('academic/terms/', terms_list, name='admin_terms_list'),
    path('academic/terms/crud/', terms_crud, name='admin_terms_crud'),
    path('academic/terms/legacy/', terms, name='admin_terms'),  # Legacy redirect
     path('export/', get_students_export, name='students_export'),
    path('class-statistics/', get_class_statistics, name='class_statistics'),
    path('bulk-update-status/', bulk_update_student_status, name='students_bulk_update_status'),
    path('bulk-move/', bulk_move_students, name='bulk_move_students'),
    path('academic/subjects/', subjects_list, name='admin_subjects_list'),
    path('academic/subjects/crud/', subjects_crud, name='admin_subjects_crud'),
    path('academic/subjects/legacy/', subjects, name='admin_subjects'),  # Legacy redirect
    path('ajax/students/delete/', delete_student, name='admin_delete_student'),
    path('academic/classes/', class_levels_list, name='admin_class_levels_list'),
    path('academic/classes/crud/', class_levels_crud, name='admin_class_levels_crud'),
    path('academic/classes/legacy/', class_levels, name='admin_class_levels'),  # Legacy redirect
      path('ajax/students/toggle-status/', toggle_student_status, name='admin_toggle_student_status'),
    path('academic/streams/', stream_classes_list, name='admin_stream_classes_list'),
    path('academic/streams/crud/', stream_classes_crud, name='admin_stream_classes_crud'),
    path('academic/streams/legacy/', stream_classes, name='admin_stream_classes'),  # Legacy redirect
    path('get-streams-by-class/', get_streams_by_class, name='admin_get_streams_by_class'),
    path('admin/bulk-toggle-student-status/', bulk_toggle_student_status,   name='admin_bulk_toggle_student_status'),
    path('get-subjects-by-education-level/', get_subjects_by_class, name='admin_get_subjects_by_class'),   
    path('ajax/class-levels-by-education-level/', get_class_levels_by_education_level, name='admin_get_class_levels_by_education_level'),
    # Student Management URLs
    path('students/', students_list, name='admin_students_list'),
    path('students/add/', students_add, name='admin_students_add'),
    path('students/by-class/', students_by_class, name='admin_students_by_class'),
    path('students/status/', student_status, name='admin_student_status'),
    path('students/<int:student_id>/edit/', student_edit, name='admin_student_edit'),
    path('students/<int:id>/delete/', student_delete, name='admin_student_delete'),
    path('students/<int:id>/detail/', student_detail, name='admin_student_detail'),
    path('students/ajax/', students_ajax, name='students_ajax'),
    
    # Parent URLs
    path('parents/', parents_list, name='admin_parents_list'),
    path('parents/add/', add_parent, name='admin_parents_add'),
    path('parents/<int:parent_id>/edit/', parent_edit, name='admin_parent_edit'),
    path('parents/delete/', parent_delete, name='admin_parent_delete'),
    path('parents/<int:parent_id>/view/', parent_detail, name='admin_view_parent'),
    path('parents/<int:parent_id>/remove-student/<int:student_id>/',remove_student_from_parent, name='admin_remove_student_from_parent'),
    path('parents/<int:parent_id>/add-student/', add_student_to_parent,  name='admin_add_student_to_parent'),
    
     # Parent management URLs
    path('students/<int:student_id>/parents/add/', add_parent_to_student,  name='admin_add_parent_to_student'),    
    path('<int:student_id>/parent/<int:parent_id>/update-fee-responsibility/', update_parent_fee_responsibility,  name='admin_update_parent_fee_responsibility'),
    path('<int:student_id>/parent/<int:parent_id>/edit/', edit_parent, name='admin_edit_parent'),
    path('<int:student_id>/parent/<int:parent_id>/delete/', delete_parent, name='admin_delete_parent'),
    path('student/<int:student_id>/remove-subject/', remove_student_subject, name='admin_remove_student_subject'),
    path('student/<int:student_id>/remove-parent/', remove_parent_from_student, name='admin_remove_parent_from_student'), 
    path('student/<int:student_id>/add-subjects/', add_optional_subjects, name='admin_add_optional_subjects'),
    # AJAX endpoints for parent operations
    path('<int:student_id>/parent/save/', save_parent, name='admin_save_parent'),
    path('<int:student_id>/parent/<int:parent_id>/update/', update_parent, name='admin_update_parent'),
    
    # Previous Schools URLs
    path('previous-schools/', previous_schools_list, name='admin_previous_schools_list'),
    path('previous-schools/crud/', previous_schools_crud, name='admin_previous_schools_crud'),
    
    # Staff Management URLs
    path('staffs/', staffs_list, name='admin_staffs_list'),
    path('staffs/crud/', staffs_crud, name='admin_staffs_crud'),
    path('staffs/<int:staff_id>/view/', view_staff, name='admin_view_staff'),
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