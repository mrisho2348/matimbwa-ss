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

    path('streams/<int:stream_id>/students/', stream_students, name='admin_stream_students'),
    path('streams/<int:stream_id>/students/remove/', remove_student_from_stream, name='admin_remove_student_from_stream'),
    path('stream/<int:stream_id>/students/bulk-remove/', bulk_remove_students_from_stream, name='admin_bulk_remove_students_from_stream'),
    path('streams/<int:stream_id>/students/add/', add_student_to_stream, name='admin_add_student_to_stream'),

    path('departments/', department_management, name='admin_department_management'),
    path('departments/crud/', departments_crud, name='admin_departments_crud'),
    path('departments/<int:department_id>/', view_department, name='admin_view_department'),
    path('departments/<int:department_id>/assign-staff/', assign_staff_to_department,   name='admin_assign_staff_to_department'),

        
    path('department/<int:department_id>/staff/', department_staff_assignment,  name='admin_department_staff'),
    path('department/<int:department_id>/staff/add/', add_staff_to_department,   name='admin_add_staff_to_department'),
    path('department/<int:department_id>/staff/remove/', remove_staff_from_department,   name='admin_remove_staff_from_department'),
    path('department/<int:department_id>/staff/bulk-remove/', bulk_remove_staff_from_department,   name='admin_bulk_remove_staff_from_department'),

    # Student Management URLs
    path('students/', students_list, name='admin_students_list'),
    path('students/add/', students_add, name='admin_students_add'),
     # Main view
    path('admin/students/by-class/', students_by_class, name='admin_students_by_class'),
    
    # API endpoints
    path('api/students/', students_api, name='students_api'),
    path('api/statistics/', statistics_api, name='statistics_api'),
    path('students/status/', student_status, name='admin_student_status'),
    path('export/students/excel/', export_students_excel, name='export_students_excel'),
    path('export/students/pdf/', export_students_pdf, name='export_students_pdf'),
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
    path('staff-roles/', staff_roles_list, name='admin_staff_roles'),
    path('staff-roles/crud/', staff_roles_crud, name='admin_staff_roles_crud'),
    path('teaching-assignments/', teaching_assignments_list, name='admin_teaching_assignments_list'),
    path('teaching-assignments/crud/', teaching_assignments_crud, name='admin_teaching_assignments_crud'),
    path('teaching-assignments/details/', get_assignment_details, name='admin_get_assignment_details'),
    path('teaching-assignments/streams/', get_streams_for_class, name='admin_get_streams_for_class'),   

    
    # Profile & Account Management URLs
    path('account/profile/', profile_view, name='admin_profile'),
    path('account/profile/update/', profile_update, name='admin_profile_update'),
    path('account/profile/picture/', profile_picture_update, name='admin_profile_picture_update'),
    
    path('account/change-password/', change_password, name='admin_change_password'),
   
    
    # AJAX/API Endpoints
    path('ajax/get-streams/', ajax_get_streams, name='admin_ajax_get_streams'),
    path('ajax/get-student-details/', ajax_get_student_details, name='admin_ajax_get_student_details'),

    # Add these URLs with your other academic management URLs
    path('academic/combinations/', combinations_list, name='admin_combinations_list'),
    path('academic/combinations/crud/', combinations_crud, name='admin_combinations_crud'),

       # Student Combination Assignment
    path('students/<int:student_id>/assign-combination/', assign_student_combination, name='admin_assign_student_combination'),
    path('students/<int:student_id>/assign-combination/ajax/', assign_student_combination_ajax, name='admin_assign_student_combination_ajax'),

    # Add these URLs to your existing admin_urls.py
    path('students/combinations/', student_combinations_list, name='admin_student_combinations_list'),
    path('students/combinations/assign/', assign_student_combination, name='admin_assign_student_combination'),
    path('students/combinations/details/', get_combination_details_ajax, name='admin_get_combination_details_ajax'),

     path('combination/<int:combination_id>/students/', combination_students, name='admin_combination_students'),
     path('combinations/<int:combination_id>/pdf-report/', combination_pdf_report, name='admin_combination_pdf_report'),

        # Student Status Management
    path('students/status/', student_status, name='admin_student_status'),
    path('students/status/change/', student_status_change, name='admin_student_status_change'),
    path('students/status/toggle/', student_toggle_active, name='admin_student_toggle_active'),
    path('students/status/bulk-update/', student_bulk_status_update, name='admin_student_bulk_status_update'),

    path('students/status/export/excel/', export_students_status_excel, name='admin_export_students_status_excel'),
    path('students/status/export/pdf/', export_students_status_pdf, name='admin_export_students_status_pdf'),

      # Student Promotion Management
    path('students/promotion/', student_promotion, name='admin_student_promotion'),
    path('students/promotion/get-students/', get_students_for_promotion, name='get_students_for_promotion'),
    path('students/promotion/execute/', execute_promotion, name='admin_execute_promotion'),
    path('students/promotion/remove-from-class/', remove_from_class, name='admin_remove_from_class'),

    

]