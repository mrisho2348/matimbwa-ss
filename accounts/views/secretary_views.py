"""
Secretary Views
Views for Secretary staff members
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import Staffs
from students.models import Student


@login_required
def secretary_dashboard(request):
    """
    Secretary Dashboard
    Administrative and document management
    """
    if request.user.user_type != "2" or request.user.staff.role != "Secretary":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    staff = request.user.staff
    
    # Secretary statistics
    total_staff = Staffs.objects.count()
    total_students = Student.objects.count()
    active_staff = Staffs.objects.filter(admin__is_active=True).count()
    
    context = {
        'page_title': 'Secretary Dashboard',
        'staff': staff,
        'total_staff': total_staff,
        'total_students': total_students,
        'active_staff': active_staff,
    }
    
    return render(request, 'secretary/dashboard.html', context)


@login_required
def secretary_manage_documents(request):
    """
    Manage school documents
    """
    if request.user.user_type != "2" or request.user.staff.role != "Secretary":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    context = {
        'page_title': 'Manage Documents',
    }
    
    return render(request, 'secretary/manage_documents.html', context)


@login_required
def secretary_manage_correspondence(request):
    """
    Manage school correspondence
    """
    if request.user.user_type != "2" or request.user.staff.role != "Secretary":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    context = {
        'page_title': 'Manage Correspondence',
    }
    
    return render(request, 'secretary/manage_correspondence.html', context)


@login_required
def secretary_schedule_meetings(request):
    """
    Schedule meetings and events
    """
    if request.user.user_type != "2" or request.user.staff.role != "Secretary":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    if request.method == 'POST':
        # Handle meeting scheduling logic
        messages.success(request, 'Meeting scheduled successfully.')
        return redirect('secretary_dashboard')
    
    context = {
        'page_title': 'Schedule Meetings',
    }
    
    return render(request, 'secretary/schedule_meetings.html', context)


@login_required
def secretary_staff_records(request):
    """
    Manage staff records
    """
    if request.user.user_type != "2" or request.user.staff.role != "Secretary":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    all_staff = Staffs.objects.all()
    
    context = {
        'page_title': 'Staff Records',
        'staff_list': all_staff,
    }
    
    return render(request, 'secretary/staff_records.html', context)


@login_required
def secretary_student_records(request):
    """
    Manage student records
    """
    if request.user.user_type != "2" or request.user.staff.role != "Secretary":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    all_students = Student.objects.all()
    
    context = {
        'page_title': 'Student Records',
        'students_list': all_students,
    }
    
    return render(request, 'secretary/student_records.html', context)
