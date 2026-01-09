"""
Dashboard URLs configuration
Routes for all dashboard views for different user roles
"""

from django.urls import path, include


# Combine all patterns with prefixes by including per-role url modules
urlpatterns = [
    path('admin/', include('accounts.urls.hod_urls')),
    path('academic/', include('accounts.urls.academic_urls')),
    path('headmaster/', include('accounts.urls.headmaster_urls')),
    path('accountant/', include('accounts.urls.accountant_urls')),
    path('librarian/', include('accounts.urls.librarian_urls')),
    path('secretary/', include('accounts.urls.secretary_urls')),
    path('staff/', include('accounts.urls.staff_urls')),
    path('student/', include('accounts.urls.student_urls')),
    path('administrator/', include('accounts.urls.administrator_urls')),
]
