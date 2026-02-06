from django.urls import path
from accounts.views.library_admin_views import *

urlpatterns = [
    # Book Categories URLs
    path('book-categories/', book_categories_list, name='admin_book_categories_list'),
    path('book-categories/crud/', book_categories_crud, name='admin_book_categories_crud'),
    path('books/', books_list, name='admin_books_list'),
    path('books/crud/', books_crud, name='admin_books_crud'),
    path('books/get/<int:book_id>/', get_book_data, name='admin_get_book_data'),
    path('book-copies/', book_copies_list, name='admin_book_copies_list'),
    path('book-copies/book/<int:book_id>/', book_copies_list, name='admin_book_copies_by_book'),
    path('book-copies/crud/', book_copies_crud, name='admin_book_copies_crud'),
    path('book-copies/get/<int:copy_id>/', get_copy_data, name='admin_get_copy_data'),
    path('book-borrows/<int:id>/edit/', admin_edit_book_borrow, name='admin_edit_book_borrow'), 
    path('borrowing-rules/', borrowing_rules_list, name='admin_borrowing_rules_list'),
    path('borrowing-rules/crud/', borrowing_rules_crud, name='admin_borrowing_rules_crud'),
    path('borrowing-rules/get/<int:rule_id>/', get_borrowing_rule_data, name='admin_get_borrowing_rule_data'),
      # Book Borrow URLs
    path('book-borrows/', book_borrows_list, name='admin_book_borrows_list'),
    path('book-borrows/create/', create_book_borrow_view, name='admin_create_book_borrow'),
    path('book-borrows/crud/', book_borrows_crud, name='admin_book_borrows_crud'),
    path('book-borrows/<int:id>/view/', view_book_borrow, name='admin_view_book_borrow'),
     path('issued-books-report/', issued_books_report_view, name='admin_issued_books_report'),
    path('issued-books-report/pdf/', export_issued_books_pdf, name='admin_export_issued_books_pdf'),
    path('book-borrows/return/<int:borrow_id>/', return_book_borrow_view, name='admin_return_book_borrow'),
    path('book-borrows/renew/<int:borrow_id>/', renew_book_borrow_view, name='admin_renew_book_borrow'),
    path('book-borrows/get/', get_borrow_data, name='admin_get_borrow_data'),
    path('book-borrows/fine-payment/<int:borrow_id>/', fine_payment_view, name='admin_fine_payment'),
    path('book-borrows/export/', export_book_borrows, name='admin_export_book_borrows'),
    path('book-borrows/get-copies/', get_book_copies, name='admin_get_book_copies'),
    path('book-borrows/get-borrower-info/', get_borrower_info, name='admin_get_borrower_info'),
    path('reports/returned-books/', returned_books_report_view, name='admin_returned_books_report'),    
    path('reports/returned-books/export-pdf/', export_returned_books_pdf,  name='admin_export_returned_books_pdf'),
    path('reports/overdue-books/', overdue_books_report_view, name='admin_overdue_books_report'),    
    path('reports/overdue-books/export-pdf/', export_overdue_books_pdf,  name='admin_export_overdue_books_pdf'),
    path('borrow/<int:borrow_id>/export-pdf/', export_borrow_details_pdf, name='admin_export_borrow_details_pdf'),
    
]