"""
Accountant Views
Views for Accountant staff members
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import Staffs
from students.models import Student


@login_required
def accountant_dashboard(request):
    """
    Accountant Dashboard
    Financial statistics and management options
    """
    if request.user.user_type != "2" or request.user.staff.role != "Accountant":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    staff = request.user.staff
    
    # Financial statistics
    total_staff = Staffs.objects.count()
    total_students = Student.objects.count()
    
    context = {
        'page_title': 'Accountant Dashboard',
        'staff': staff,
        'total_staff': total_staff,
        'total_students': total_students,
    }
    
    return render(request, 'accountant/dashboard.html', context)


@login_required
def accountant_manage_fees(request):
    """
    Manage student fees
    """
    if request.user.user_type != "2" or request.user.staff.role != "Accountant":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    all_students = Student.objects.all()
    
    context = {
        'page_title': 'Manage Fees',
        'students': all_students,
    }
    
    return render(request, 'accountant/manage_fees.html', context)


@login_required
def accountant_record_payments(request):
    """
    Record student fee payments
    """
    if request.user.user_type != "2" or request.user.staff.role != "Accountant":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    if request.method == 'POST':
        # Handle payment recording logic
        messages.success(request, 'Payment recorded successfully.')
        return redirect('accountant_dashboard')
    
    context = {
        'page_title': 'Record Payments',
    }
    
    return render(request, 'accountant/record_payments.html', context)


@login_required
def accountant_manage_expenses(request):
    """
    Manage school expenses
    """
    if request.user.user_type != "2" or request.user.staff.role != "Accountant":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    context = {
        'page_title': 'Manage Expenses',
    }
    
    return render(request, 'accountant/manage_expenses.html', context)


@login_required
def accountant_financial_reports(request):
    """
    Generate financial reports
    """
    if request.user.user_type != "2" or request.user.staff.role != "Accountant":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    context = {
        'page_title': 'Financial Reports',
    }
    
    return render(request, 'accountant/financial_reports.html', context)
