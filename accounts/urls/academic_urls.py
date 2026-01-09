from django.urls import path
from accounts.views.academic_views import (
    academic_dashboard,
    academic_enter_results,
    academic_view_results,
    academic_performance_report,
    academic_print_results,
)

urlpatterns = [
    path('dashboard/', academic_dashboard, name='academic_dashboard'),
    path('enter-results/', academic_enter_results, name='academic_enter_results'),
    path('view-results/', academic_view_results, name='academic_view_results'),
    path('performance-report/', academic_performance_report, name='academic_performance_report'),
    path('print-results/', academic_print_results, name='academic_print_results'),
]
