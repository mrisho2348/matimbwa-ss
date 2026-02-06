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
    path('results/exam-sessions/<int:exam_session_id>/', exam_session_detail, name='admin_exam_session_detail'),
    path('results/exam-sessions/<int:exam_session_id>/papers/', manage_exam_papers, name='admin_manage_exam_papers'),
    path('results/exam-sessions/get-streams/', get_streams_for_exam_session, name='admin_get_streams_for_exam_session'),
    path('results/exam-sessions/stats/', get_exam_session_stats, name='admin_exam_session_stats'),
    path('exam-sessions/get-terms/', get_terms_for_academic_year, name='admin_get_terms_for_academic_year'),
    path('exam-sessions/get-streams/', get_streams_for_exam_session, name='admin_get_streams_for_exam_session'),
]