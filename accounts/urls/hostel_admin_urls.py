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

    # Student Hostel Allocation URLs
    path('allocations/', student_hostel_allocations_list, name='admin_student_allocations_list'),
    path('allocations/crud/', student_hostel_allocations_crud, name='admin_student_allocations_crud'),
    path('allocations/<int:allocation_id>/details/', allocation_details, name='admin_allocation_details'),
    path('allocations/students/available/', get_available_students, name='admin_get_available_students'),
    path('allocations/hostels/<int:hostel_id>/available-rooms/', get_available_rooms, name='admin_get_available_rooms'),
    path('allocations/rooms/<int:room_id>/available-beds/', get_available_beds, name='admin_get_available_beds'),
    path('allocations/check-availability/', check_availability, name='admin_check_availability'),

]