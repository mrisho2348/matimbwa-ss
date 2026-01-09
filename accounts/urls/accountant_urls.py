from django.urls import path
from accounts.views.accountant_views import (
    accountant_dashboard,
    accountant_manage_fees,
    accountant_record_payments,
    accountant_manage_expenses,
    accountant_financial_reports,
)

urlpatterns = [
    path('dashboard/', accountant_dashboard, name='accountant_dashboard'),
    path('manage-fees/', accountant_manage_fees, name='accountant_manage_fees'),
    path('record-payments/', accountant_record_payments, name='accountant_record_payments'),
    path('manage-expenses/', accountant_manage_expenses, name='accountant_manage_expenses'),
    path('financial-reports/', accountant_financial_reports, name='accountant_financial_reports'),
]
