from django.urls import path
from accounts.views.secretary_views import (
    secretary_dashboard,
    secretary_manage_documents,
    secretary_manage_correspondence,
    secretary_schedule_meetings,
    secretary_staff_records,
    secretary_student_records,
)

urlpatterns = [
    path('dashboard/', secretary_dashboard, name='secretary_dashboard'),
    path('manage-documents/', secretary_manage_documents, name='secretary_manage_documents'),
    path('manage-correspondence/', secretary_manage_correspondence, name='secretary_manage_correspondence'),
    path('schedule-meetings/', secretary_schedule_meetings, name='secretary_schedule_meetings'),
    path('staff-records/', secretary_staff_records, name='secretary_staff_records'),
    path('student-records/', secretary_student_records, name='secretary_student_records'),
]
