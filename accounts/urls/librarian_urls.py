from django.urls import path
from accounts.views.librarian_views import (
    librarian_dashboard,
    librarian_manage_books,
    librarian_issue_books,
    librarian_return_books,
    librarian_reports,
)

urlpatterns = [
    path('dashboard/', librarian_dashboard, name='librarian_dashboard'),
    path('manage-books/', librarian_manage_books, name='librarian_manage_books'),
    path('issue-books/', librarian_issue_books, name='librarian_issue_books'),
    path('return-books/', librarian_return_books, name='librarian_return_books'),
    path('reports/', librarian_reports, name='librarian_reports'),
]
