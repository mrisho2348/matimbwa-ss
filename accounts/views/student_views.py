"""
Student Views
Views for student users
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from students.models import Student



@login_required
def student_dashboard(request):
    """
    Student Dashboard
    Displays student academic information and results
    """
    if request.user.user_type != "3":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    try:
        student = Student.objects.get(admin=request.user)
    except Student.DoesNotExist:
        student = None
    
    
    context = {
        'page_title': 'Student Dashboard',
        'student': student,
      
    }
    
    return render(request, 'students/dashboard.html', context)


@login_required
def student_view_results(request):
    """
    View personal exam results
    """
    if request.user.user_type != "3":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    try:
        student = Student.objects.get(admin=request.user)
    except Student.DoesNotExist:
        student = None
        student_results = []
    
    context = {
        'page_title': 'My Results',
        'student': student,
        
    }
    
    return render(request, 'students/view_results.html', context)


@login_required
def student_view_timetable(request):
    """
    View class timetable
    """
    if request.user.user_type != "3":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    try:
        student = Student.objects.get(admin=request.user)
    except Student.DoesNotExist:
        student = None
    
    context = {
        'page_title': 'Class Timetable',
        'student': student,
    }
    
    return render(request, 'students/view_timetable.html', context)


@login_required
def student_view_profile(request):
    """
    View and edit personal profile
    """
    if request.user.user_type != "3":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    try:
        student = Student.objects.get(admin=request.user)
    except Student.DoesNotExist:
        student = None
    
    if request.method == 'POST':
        # Handle profile update logic
        messages.success(request, 'Profile updated successfully.')
        return redirect('student_view_profile')
    
    context = {
        'page_title': 'My Profile',
        'student': student,
    }
    
    return render(request, 'students/view_profile.html', context)


@login_required
def student_attendance_record(request):
    """
    View attendance records
    """
    if request.user.user_type != "3":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    try:
        student = Student.objects.get(admin=request.user)
    except Student.DoesNotExist:
        student = None
    
    context = {
        'page_title': 'Attendance Records',
        'student': student,
    }
    
    return render(request, 'students/attendance_record.html', context)
