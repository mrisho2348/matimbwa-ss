from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Result, TermAnalysis


@login_required
def results_dashboard(request):
    """Results dashboard view"""
    results = Result.objects.all()
    context = {'results': results}
    return render(request, 'results/dashboard.html', context)


@login_required
def student_results(request, admission_number):
    """Student detailed results view"""
    from students.models import Student
    student = Student.objects.get(admission_number=admission_number)
    results = Result.objects.filter(student=student)
    analysis = TermAnalysis.objects.filter(student=student)
    context = {'student': student, 'results': results, 'analysis': analysis}
    return render(request, 'results/student_results.html', context)
