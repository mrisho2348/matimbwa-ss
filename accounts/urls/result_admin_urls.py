# results/urls.py
from django.urls import path
from accounts.views.result_admin_views import *

urlpatterns = [
    path('grading-scales/', grading_scales_list, name='admin_grading_scales_list'),
    path('grading-scales/crud/', grading_scales_crud, name='admin_grading_scales_crud'),
    path('division-scales/', division_scales_list, name='admin_division_scales_list'),
    path('division-scales/crud/', division_scales_crud, name='admin_division_scales_crud'),
    path('division-scales/by-level/', get_division_scales_by_level, name='admin_get_division_scales_by_level'),
    path('division-scales/calculate/', calculate_division, name='admin_calculate_division'),
    path('division-scales/validate/', validate_division_scales, name='admin_validate_division_scales'),
    path('academic/exam-types/', exam_types_list, name='admin_exam_types_list'),
    path('academic/exam-types/crud/', exam_types_crud, name='admin_exam_types_crud'),
    path('results/exam-sessions/', exam_sessions_list, name='admin_exam_sessions_list'),
    path('results/exam-sessions/crud/', exam_sessions_crud, name='admin_exam_sessions_crud'),
    path('exam-sessions/<int:exam_session_id>/', exam_session_detail, name='admin_exam_session_detail'),    
    path('results/exam-sessions/get-streams/', get_streams_for_exam_session, name='admin_get_streams_for_exam_session'),
    path('results/exam-sessions/stats/', get_exam_session_stats, name='admin_exam_session_stats'),
    path('exam-sessions/get-terms/', get_terms_for_academic_year, name='admin_get_terms_for_academic_year'),
    path('exam-sessions/get-streams/', get_streams_for_exam_session, name='admin_get_streams_for_exam_session'),
    path('exam-sessions/data/', admin_exam_sessions_data, name='admin_exam_sessions_data'),
    path('exam-sessions/details/', get_exam_session_by_id, name='admin_get_exam_session_by_id'),

        # New Excel/PDF functionality URLs
    path('download-excel-template/<int:exam_session_id>/<int:subject_id>/', download_excel_template, name='download_excel_template'),
    path('upload-excel-marks/', upload_excel_marks, name='upload_excel_marks'),
    path('download-pdf-report/<int:exam_session_id>/<int:subject_id>/', download_pdf_report, name='download_pdf_report'),
      # Student Results Management
    path('exam-sessions/<int:exam_session_id>/manage-result/', manage_results,  name='manage_results'),    
    # AJAX endpoints
    path('save-results/', save_student_results, name='save_student_results'),
    path('save-multiple-results/',  save_multiple_results, name='save_multiple_results'),
    path('exam-sessions/<int:exam_session_id>/subject/<int:subject_id>/entry/', subject_results_entry,   name='admin_subject_results_entry' ),

    path('exam-sessions/<int:exam_session_id>/download-excel-template/', download_session_excel_template, name='download_session_excel_template'),
    path('exam-sessions/upload-session-excel/', upload_session_excel, name='upload_session_excel'),
    # In your urls.py
    path('exam-sessions/<int:exam_session_id>/download-excel-report/', download_session_excel_report, name='download_session_excel_report'),
    path('exam-sessions/<int:exam_session_id>/download-summary/', download_session_summary, name='download_session_summary'),

]