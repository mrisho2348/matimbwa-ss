from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def login_view(request):
    """User login view"""
    return render(request, 'accounts/login.html')


@login_required
def profile_view(request):
    """User profile view"""
    context = {'user': request.user}
    return render(request, 'accounts/profile.html', context)
