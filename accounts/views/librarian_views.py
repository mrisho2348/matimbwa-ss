"""
Librarian Views
Views for Librarian staff members
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import Staffs
from students.models import Student


@login_required
def librarian_dashboard(request):
    """
    Librarian Dashboard
    Library management and statistics
    """
    if request.user.user_type != "2" or request.user.staff.role != "Librarian":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    staff = request.user.staff
    
    # Library statistics
    total_students = Student.objects.count()
    
    context = {
        'page_title': 'Librarian Dashboard',
        'staff': staff,
        'total_students': total_students,
    }
    
    return render(request, 'librarian/dashboard.html', context)


@login_required
def librarian_manage_books(request):
    """
    Manage library book collection
    """
    if request.user.user_type != "2" or request.user.staff.role != "Librarian":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    context = {
        'page_title': 'Manage Books',
    }
    
    return render(request, 'librarian/manage_books.html', context)


@login_required
def librarian_issue_books(request):
    """
    Issue books to students
    """
    if request.user.user_type != "2" or request.user.staff.role != "Librarian":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    if request.method == 'POST':
        # Handle book issue logic
        messages.success(request, 'Book issued successfully.')
        return redirect('librarian_dashboard')
    
    all_students = Student.objects.all()
    
    context = {
        'page_title': 'Issue Books',
        'students': all_students,
    }
    
    return render(request, 'librarian/issue_books.html', context)


@login_required
def librarian_return_books(request):
    """
    Record book returns from students
    """
    if request.user.user_type != "2" or request.user.staff.role != "Librarian":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    if request.method == 'POST':
        # Handle book return logic
        messages.success(request, 'Book return recorded successfully.')
        return redirect('librarian_dashboard')
    
    context = {
        'page_title': 'Return Books',
    }
    
    return render(request, 'librarian/return_books.html', context)


@login_required
def librarian_reports(request):
    """
    Generate library reports
    """
    if request.user.user_type != "2" or request.user.staff.role != "Librarian":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    context = {
        'page_title': 'Library Reports',
    }
    
    return render(request, 'librarian/reports.html', context)
