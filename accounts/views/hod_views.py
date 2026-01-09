"""
HOD/Admin Dashboard Views
Views for HOD (Head of Department) and Administrator users
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from accounts.models import CustomUser, AdminHOD, Staffs

from students.models import Student


@login_required
def admin_dashboard(request):
    """
    Admin/HOD Dashboard
    Displays overall school statistics and administrative options
    """
    if request.user.user_type != "1":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    # Get admin profile
    try:
        admin_profile = AdminHOD.objects.get(admin=request.user)
    except AdminHOD.DoesNotExist:
        admin_profile = None
    
    # Dashboard statistics
    total_staff = Staffs.objects.count()
    total_students = Student.objects.count()
    recent_students = Student.objects.all().order_by('-created_at')[:5]
    staff_by_role = Staffs.objects.values('role').distinct().count()
    
    context = {
        'page_title': 'Admin Dashboard',
        'admin_profile': admin_profile,
        'total_staff': total_staff,
        'total_students': total_students,        
        'staff_by_role': staff_by_role,        
        'recent_students': recent_students,
    }
    
    return render(request, 'admin/dashboard.html', context)


@login_required
def hod_manage_staff(request):
    """
    Manage all staff members
    """
    if request.user.user_type != "1":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    all_staff = Staffs.objects.all()
    
    context = {
        'page_title': 'Manage Staff',
        'staff_list': all_staff,
    }
    
    return render(request, 'admin/manage_staff.html', context)


@login_required
def hod_manage_students(request):
    """
    Manage all students
    """
    if request.user.user_type != "1":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    all_students = Student.objects.all()
    
    context = {
        'page_title': 'Manage Students',
        'students_list': all_students,
    }
    
    return render(request, 'admin/manage_students.html', context)


@login_required
def hod_manage_results(request):
    """
    Manage and view all exam results
    """
    if request.user.user_type != "1":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    
    context = {
        'page_title': 'Manage Results',
       
    }
    
    return render(request, 'admin/manage_results.html', context)


@login_required
def hod_system_settings(request):
    """
    System settings and configuration
    """
    if request.user.user_type != "1":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    context = {
        'page_title': 'System Settings',
    }
    
    return render(request, 'admin/settings.html', context)
