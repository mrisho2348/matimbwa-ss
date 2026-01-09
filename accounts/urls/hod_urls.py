from django.urls import path
from accounts.views.hod_views import (
    admin_dashboard,
    hod_manage_staff,
    hod_manage_students,
    hod_manage_results,
    hod_system_settings,
)

urlpatterns = [
    path('dashboard/', admin_dashboard, name='admin_dashboard'),
    path('manage-staff/', hod_manage_staff, name='hod_manage_staff'),
    path('manage-students/', hod_manage_students, name='hod_manage_students'),
    path('manage-results/', hod_manage_results, name='hod_manage_results'),
    path('system-settings/', hod_system_settings, name='hod_system_settings'),
]
