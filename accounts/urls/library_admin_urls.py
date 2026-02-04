from django.urls import path
from accounts.views.library_admin_views import *

urlpatterns = [
    # Book Categories URLs
    path('book-categories/', book_categories_list, name='admin_book_categories_list'),
    path('book-categories/crud/', book_categories_crud, name='admin_book_categories_crud'),
    path('books/', books_list, name='admin_books_list'),
    path('books/crud/', books_crud, name='admin_books_crud'),
]