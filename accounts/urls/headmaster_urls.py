from django.urls import path
from accounts.views.headmaster_views import (
    headmaster_dashboard,
    headmaster_manage_staff,
    headmaster_manage_students,
    headmaster_view_reports,
    headmaster_approvals,
)

urlpatterns = [
    path('dashboard/', headmaster_dashboard, name='headmaster_dashboard'),
    path('manage-staff/', headmaster_manage_staff, name='headmaster_manage_staff'),
    path('manage-students/', headmaster_manage_students, name='headmaster_manage_students'),
    path('reports/', headmaster_view_reports, name='headmaster_view_reports'),
    path('approvals/', headmaster_approvals, name='headmaster_approvals'),
]
