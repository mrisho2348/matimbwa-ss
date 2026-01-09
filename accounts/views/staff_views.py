"""
General Staff Views
Views for general staff members
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages


@login_required
def staff_dashboard(request):
    """
    General Staff Dashboard
    Basic staff portal for daily tasks
    """
    if request.user.user_type != "2":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    staff = request.user.staff
    
    context = {
        'page_title': 'Staff Dashboard',
        'staff': staff,
    }
    
    return render(request, 'staff/dashboard.html', context)


@login_required
def staff_mark_attendance(request):
    """
    Mark class attendance
    """
    if request.user.user_type != "2":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    if request.method == 'POST':
        # Handle attendance marking logic
        messages.success(request, 'Attendance marked successfully.')
        return redirect('staff_dashboard')
    
    context = {
        'page_title': 'Mark Attendance',
    }
    
    return render(request, 'staff/mark_attendance.html', context)


@login_required
def staff_enter_results(request):
    """
    Enter student results
    """
    if request.user.user_type != "2":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    if request.method == 'POST':
        # Handle result entry logic
        messages.success(request, 'Results entered successfully.')
        return redirect('staff_dashboard')
    
    context = {
        'page_title': 'Enter Results',
    }
    
    return render(request, 'staff/enter_results.html', context)


@login_required
def staff_view_classes(request):
    """
    View assigned classes
    """
    if request.user.user_type != "2":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    context = {
        'page_title': 'My Classes',
    }
    
    return render(request, 'staff/view_classes.html', context)


@login_required
def staff_view_reports(request):
    """
    View personal staff reports
    """
    if request.user.user_type != "2":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    context = {
        'page_title': 'My Reports',
    }
    
    return render(request, 'staff/view_reports.html', context)
