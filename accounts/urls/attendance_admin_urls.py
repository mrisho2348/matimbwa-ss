# attendance/urls.py
from django.urls import path
from accounts.views.attendance_admin_views import *

urlpatterns = [
    # Main attendance management pages
 
    path('sessions/', AttendanceSessionListView.as_view(), name='attendance_session_list'),
    path('create/', CreateAttendanceSessionView.as_view(), name='attendance_create'),
    
    # API endpoints for AJAX operations
    path('api/sessions/', GetAttendanceSessionsAPI.as_view(), name='admin_get_attendance_sessions'),
    path('api/session/create/', CreateAttendanceSessionAPI.as_view(), name='admin_attendance_crud'),
    path('api/session/<int:session_id>/', AttendanceSessionDetailAPI.as_view(), name='admin_get_attendance_details'),
    path('api/session/<int:session_id>/delete/', DeleteAttendanceSessionAPI.as_view(), name='admin_delete_attendance_session'),
    path('api/session/<int:session_id>/edit/', EditAttendanceSessionAPI.as_view(), name='admin_edit_attendance_session'), 
    path('students/', StudentAttendanceListView.as_view(), name='student_attendance_list'),
    path('student/<int:student_id>/report/', StudentAttendanceReportView.as_view(), name='student_attendance_report'),
    path('student/<int:student_id>/download-pdf/', DownloadAttendancePDFView.as_view(), name='download_attendance_pdf'),
    # Edit session page
    path('edit/<int:session_id>/', EditAttendanceSessionView.as_view(), name='edit_attendance_session'),
    path('edit-session/<int:session_id>/', EditAttendanceSessionView.as_view(),   name='admin_edit_attendance_session'),    
    # Edit attendance session API
    path('api/edit-session/<int:session_id>/',  EditAttendanceSessionAPI.as_view(),  name='admin_edit_attendance_session_api'),
     # API to get session data for editing
    path('api/edit-session/<int:session_id>/',     GetEditAttendanceSessionAPI.as_view(), name='admin_get_edit_attendance_session_api'),
    path('api/update-session/<int:session_id>/',    UpdateAttendanceSessionAPI.as_view(),  name='admin_update_attendance_session_api'),
    # Data loading endpoints
    path('api/streams/class/<int:class_id>/', GetStreamsForClassAPI.as_view(), name='admin_get_streams_for_class'),
    path('api/subjects/class/<int:class_id>/', GetSubjectsForClassAPI.as_view(), name='admin_get_subjects_by_class'),
    path('api/students/class/<int:class_id>/stream/<int:stream_id>/', GetStudentsByClassStreamAPI.as_view(), name='admin_get_students_by_class_stream'),
    

    
    # Reports
    path('reports/daily/', DailyAttendanceReportView.as_view(), name='attendance_report_daily'),
    path('reports/daily/export-pdf/', ExportDailyAttendancePDFView.as_view(), name='export_daily_attendance_pdf'),
    path('reports/monthly/', MonthlyAttendanceReportView.as_view(), name='attendance_report_monthly'),
    path('reports/monthly/export/pdf/', ExportMonthlyAttendancePDFView.as_view(), name='attendance_report_monthly_pdf'),
     # API endpoints
    path('api/week-details/', GetWeekAttendanceDetailsAPI.as_view(), name='api_week_details'),
    path('api/class-details/', GetClassAttendanceDetailsAPI.as_view(), name='api_class_details'),
     path('attendance-report/weekly-pdf/', WeeklyAttendancePDFView.as_view(), name='attendance_report_weekly_pdf'),
    
    # Class monthly PDF report
    path('attendance-report/class-monthly-pdf/', ClassMonthlyAttendancePDFView.as_view(), name='attendance_report_class_monthly_pdf'),
    path('reports/student/<int:student_id>/', StudentAttendanceReportView.as_view(), name='attendance_report_student'),
    path('reports/class/<int:class_id>/', ClassAttendanceReportView.as_view(), name='attendance_report_class'),
    

]