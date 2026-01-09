"""
Academic Coordinator Views
Views for Academic Coordinator staff members
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from accounts.models import Staffs
from students.models import Student


@login_required
def academic_dashboard(request):
    """
    Academic Coordinator Dashboard
    Displays student performance and academic statistics
    """
    if request.user.user_type != "2" or request.user.staff.role != "Academic":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    staff = request.user.staff
    
    # Academic statistics
    total_students = Student.objects.count()
    
    context = {
        'page_title': 'Academic Dashboard',
        'staff': staff,
        'total_students': total_students,    }
    
    return render(request, 'academic/dashboard.html', context)


@login_required
def academic_enter_results(request):
    """
    Enter student examination results
    """
    if request.user.user_type != "2" or request.user.staff.role != "Academic":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    if request.method == 'POST':
        # Handle result entry logic
        messages.success(request, 'Results entered successfully.')
        return redirect('academic_dashboard')
    
    all_students = Student.objects.all()
    
    context = {
        'page_title': 'Enter Results',
        'students': all_students,
    }
    
    return render(request, 'academic/enter_results.html', context)


@login_required
def academic_view_results(request):
    """
    View all student results
    """
    if request.user.user_type != "2" or request.user.staff.role != "Academic":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    
    context = {
        'page_title': 'View Results',
        
    }
    
    return render(request, 'academic/view_results.html', context)


@login_required
def academic_performance_report(request):
    """
    Generate performance reports
    """
    if request.user.user_type != "2" or request.user.staff.role != "Academic":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    context = {
        'page_title': 'Performance Reports',
    }
    
    return render(request, 'academic/performance_report.html', context)


@login_required
def academic_print_results(request):
    """
    Print exam results
    """
    if request.user.user_type != "2" or request.user.staff.role != "Academic":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    context = {
        'page_title': 'Print Results',
    }
    
    return render(request, 'academic/print_results.html', context)
