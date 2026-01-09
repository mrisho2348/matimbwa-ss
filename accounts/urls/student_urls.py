from django.urls import path
from accounts.views.student_views import (
    student_dashboard,
    student_view_results,
    student_view_timetable,
    student_view_profile,
    student_attendance_record,
)

urlpatterns = [
    path('dashboard/', student_dashboard, name='student_dashboard'),
    path('view-results/', student_view_results, name='student_view_results'),
    path('view-timetable/', student_view_timetable, name='student_view_timetable'),
    path('view-profile/', student_view_profile, name='student_view_profile'),
    path('attendance-record/', student_attendance_record, name='student_attendance_record'),
]
