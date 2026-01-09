from django.shortcuts import render
from django.views import View


class DashboardView(View):
    """Main dashboard view"""
    
    def get(self, request):
        context = {}
        return render(request, 'core/dashboard.html', context)
