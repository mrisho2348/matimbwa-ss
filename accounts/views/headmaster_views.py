"""
Headmaster Views
Views for Headmaster staff members
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import Staffs
from students.models import Student


@login_required
def headmaster_dashboard(request):
    """
    Headmaster Dashboard
    Comprehensive school overview and administrative functions
    """
    if request.user.user_type != "2" or request.user.staff.role != "Headmaster":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    staff = request.user.staff
    
    # Headmaster statistics - comprehensive school overview
    total_staff = Staffs.objects.count()
    total_students = Student.objects.count()
    active_students = Student.objects.filter(is_active=True).count() if hasattr(Student, 'is_active') else total_students
    
    # Staff breakdown by role
    staff_by_role = {}
    roles = ["Academic", "Secretary", "Accountant", "Librarian", "Administrator"]
    for role in roles:
        staff_by_role[role] = Staffs.objects.filter(role=role).count()
    
    context = {
        'page_title': 'Headmaster Dashboard',
        'staff': staff,
        'total_staff': total_staff,
        'total_students': total_students,        
        'active_students': active_students,
        'staff_by_role': staff_by_role,
    }
    
    return render(request, 'headmaster/dashboard.html', context)


@login_required
def headmaster_manage_staff(request):
    """
    Manage school staff
    """
    if request.user.user_type != "2" or request.user.staff.role != "Headmaster":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    all_staff = Staffs.objects.all()
    
    context = {
        'page_title': 'Manage Staff',
        'staff_list': all_staff,
    }
    
    return render(request, 'headmaster/manage_staff.html', context)


@login_required
def headmaster_manage_students(request):
    """
    Manage school students
    """
    if request.user.user_type != "2" or request.user.staff.role != "Headmaster":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    all_students = Student.objects.all()
    
    context = {
        'page_title': 'Manage Students',
        'students_list': all_students,
    }
    
    return render(request, 'headmaster/manage_students.html', context)


@login_required
def headmaster_view_reports(request):
    """
    View school reports
    """
    if request.user.user_type != "2" or request.user.staff.role != "Headmaster":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    context = {
        'page_title': 'School Reports',
    }
    
    return render(request, 'headmaster/reports.html', context)


@login_required
def headmaster_approvals(request):
    """
    Approve pending requests and documents
    """
    if request.user.user_type != "2" or request.user.staff.role != "Headmaster":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    context = {
        'page_title': 'Approvals',
    }
    
    return render(request, 'headmaster/approvals.html', context)
