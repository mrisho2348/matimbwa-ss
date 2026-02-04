"""
Per-role URL modules package for accounts app.

This package exposes `urlpatterns` so `include('accounts.urls')` works
even though per-role modules live under `accounts/urls/`.

Each per-role module (e.g. `academic_urls`) defines its own `urlpatterns`.
The main `urlpatterns` below includes them under the appropriate prefixes.
"""

from django.urls import path, include

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
    path('attendance/', include('accounts.urls.attendance_admin_urls')),
    path('library/', include('accounts.urls.library_admin_urls')),
]

__all__ = [
    'urlpatterns',
]
