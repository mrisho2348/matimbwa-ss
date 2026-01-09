from django.urls import path
from accounts.views.staff_views import (
    staff_dashboard,
    staff_mark_attendance,
    staff_enter_results,
    staff_view_classes,
    staff_view_reports,
)

urlpatterns = [
    path('dashboard/', staff_dashboard, name='staff_dashboard'),
    path('mark-attendance/', staff_mark_attendance, name='staff_mark_attendance'),
    path('enter-results/', staff_enter_results, name='staff_enter_results'),
    path('view-classes/', staff_view_classes, name='staff_view_classes'),
    path('view-reports/', staff_view_reports, name='staff_view_reports'),
]
