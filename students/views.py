from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Student


@login_required
def student_list(request):
    """List all students"""
    students = Student.objects.all()
    context = {'students': students}
    return render(request, 'students/student_list.html', context)


@login_required
def student_detail(request, admission_number):
    """Student detail view"""
    student = Student.objects.get(admission_number=admission_number)
    context = {'student': student}
    return render(request, 'students/student_detail.html', context)
