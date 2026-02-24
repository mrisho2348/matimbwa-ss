# results/urls.py
from django.urls import path
from accounts.views.hostel_admin_views import *

urlpatterns = [
  
    # accounts/urls/admin_urls.py

    # Add these with your other management URLs
    path('hostels/', hostels_list, name='admin_hostels_list'),
    path('hostels/crud/', hostels_crud, name='admin_hostels_crud'),

    # accounts/urls/admin_urls.py

    # Add these with your other hostel URLs
    path('hostels/rooms/', hostel_rooms_list, name='admin_hostel_rooms_list'),
    path('hostels/rooms/crud/', hostel_rooms_crud, name='admin_hostel_rooms_crud'),
    path('hostels/<int:hostel_id>/rooms/', hostel_rooms_by_hostel, name='admin_hostel_rooms_by_hostel'),

    # accounts/urls/admin_urls.py

    # Add these with your other hostel URLs
    path('hostels/beds/', beds_list, name='admin_beds_list'),
    path('hostels/beds/crud/', beds_crud, name='admin_beds_crud'),
    path('hostels/rooms/<int:room_id>/beds/', beds_by_room, name='admin_beds_by_room'),
    path('hostels/<int:hostel_id>/rooms/', hostel_rooms_by_hostel, name='admin_hostel_rooms_by_hostel'),

    # List View
    path('allocations/', student_hostel_allocations_list, name='admin_student_allocations_list'),
    
    # Single Operations
    path('allocations/create/', student_allocation_create, name='admin_student_allocation_create'),
    path('allocations/<int:pk>/', student_allocation_detail, name='admin_student_allocation_detail'),
    path('allocations/<int:pk>/edit/', student_allocation_edit, name='admin_student_allocation_edit'),
    path('allocations/delete/', student_allocation_delete, name='admin_student_allocation_delete'),
    path('allocations/toggle/', student_allocation_toggle, name='admin_student_allocation_toggle'),
    
    # Bulk Operations
    path('allocations/bulk/', student_allocation_bulk, name='admin_student_allocation_bulk'),
    path('allocations/bulk/create/', student_allocation_bulk_create, name='admin_student_allocation_bulk_create'),
    path('allocations/bulk/remove/', student_allocation_bulk_remove, name='admin_student_allocation_bulk_remove'),
    
    # AJAX endpoints
    path('api/students/available/', get_available_students, name='admin_get_available_students'),
    path('api/hostels/<int:hostel_id>/rooms/', get_available_rooms, name='admin_get_available_rooms'),
    path('api/rooms/<int:room_id>/beds/', get_available_beds, name='admin_get_available_beds'),
    path('api/check-availability/', check_availability, name='admin_check_availability'),

    # Add these to your urls.py

    # Hostel Installment Plan URLs
    path('installment-plans/', hostel_installment_plans_list, name='admin_hostel_installment_plans_list'),
    path('installment-plans/create/', hostel_installment_plan_create, name='admin_hostel_installment_plan_create'),
    path('installment-plans/<int:pk>/', hostel_installment_plan_detail, name='admin_hostel_installment_plan_detail'),
    path('installment-plans/<int:pk>/edit/', hostel_installment_plan_edit, name='admin_hostel_installment_plan_edit'),
    path('installment-plans/delete/', hostel_installment_plan_delete, name='admin_hostel_installment_plan_delete'),
    path('installment-plans/by-hostel/<int:hostel_id>/', get_installment_plans_by_hostel, name='admin_get_installment_plans_by_hostel'),

    # Hostel Payment URLs
    path('hostel/payments/', hostel_payments_list, name='admin_hostel_payments_list'),
    path('hostel/payments/create/', hostel_payment_create, name='admin_hostel_payment_create'),
    path('hostel/payments/<int:pk>/', hostel_payment_detail, name='admin_hostel_payment_detail'),
    path('hostel/payments/student/<int:student_id>/', student_payment_history, name='admin_student_payment_history'),
    path('hostel/payments/allocation/<int:allocation_id>/', allocation_payments, name='admin_allocation_payments'),
    path('hostel/payments/process/', process_payment, name='admin_process_payment'),
    path('hostel/payments/refund/', process_refund, name='admin_process_refund'),
    path('hostel/payments/balance/<int:student_id>/', student_balance_info, name='admin_student_balance_info'),

        # Hostel Students
    path('hostel/<int:hostel_id>/students/', hostel_students_list, name='admin_hostel_students'),  
    path('hostel/rooms/', hostel_rooms_list, name='admin_hostel_rooms_list'),    
    path('hostel/beds/', beds_list, name='admin_hostel_beds_list'),

    path('single/hostel/rooms/', single_hostel_rooms_list, name='admin_single_hostel_rooms_list'),
    path('single/hostel/payments/', hostel_student_payments_list, name='admin_hostel_student_payments_list'),
    path('single/hostel/installments/', hostel_installment_list, name='admin_hostel_installment_list'),
    path('single/hostel/allocate/', hostel_student_allocation, name='admin_hostel_student_allocation'),
    path('api/hostel/room/<int:room_id>/details/', get_hostel_room_details, name='get_hostel_room_details'),
    path('api/hostel/<int:hostel_id>/payment-summary/',get_hostel_payment_summary, name='get_hostel_payment_summary'),

    # Add these to your urlpatterns

    path('hostel/room/create/', hostel_room_create, name='admin_hostel_room_create'),
    path('hostel/room/<int:room_id>/edit/', hostel_room_edit, name='admin_hostel_room_edit'),
    path('hostel/room/<int:room_id>/detail/', hostel_room_detail, name='admin_hostel_room_detail'),
        # API endpoints for room management
    path('api/hostel/check-room-number/', api_check_room_number, name='api_check_room_number'),
    path('api/hostel/room/<int:room_id>/delete/', api_delete_room, name='api_delete_room'),
   

        # Hostel Payments Export URLs
    path('hostel/payments/export/excel/', hostel_payments_export_excel, name='admin_hostel_payments_export_excel'),
    path('hostel/payments/export/pdf/', hostel_payments_export_pdf,  name='admin_hostel_payments_export_pdf'),
    path('hostel/payment/<int:pk>/receipt/pdf/', hostel_payment_receipt_pdf,  name='admin_hostel_payment_receipt_pdf'),
    path('allocations/<int:allocation_id>/payments/export/pdf/', allocation_payments_export_pdf, name='admin_allocation_payments_export_pdf'),
    path('payment/<int:transaction_id>/receipt/pdf/', single_transaction_payment_export_pdf, name='admin_single_allocation_transaction_payments_export_pdf'),

]