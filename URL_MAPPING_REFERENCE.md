# Complete URL Mapping Reference

## Dashboard URLs by Role

### HOD/Admin Dashboard Routes
```
GET  /admin/dashboard/                  → admin_dashboard()
GET  /admin/manage-staff/               → hod_manage_staff()
GET  /admin/manage-students/            → hod_manage_students()
GET  /admin/manage-results/             → hod_manage_results()
GET  /admin/system-settings/            → hod_system_settings()
```

### Academic Coordinator Routes
```
GET  /academic/dashboard/               → academic_dashboard()
GET  /academic/enter-results/           → academic_enter_results()
GET  /academic/view-results/            → academic_view_results()
GET  /academic/performance-report/      → academic_performance_report()
GET  /academic/print-results/           → academic_print_results()
```

### Headmaster Routes
```
GET  /headmaster/dashboard/             → headmaster_dashboard()
GET  /headmaster/manage-staff/          → headmaster_manage_staff()
GET  /headmaster/manage-students/       → headmaster_manage_students()
GET  /headmaster/reports/               → headmaster_view_reports()
GET  /headmaster/approvals/             → headmaster_approvals()
```

### Accountant Routes
```
GET  /accountant/dashboard/             → accountant_dashboard()
GET  /accountant/manage-fees/           → accountant_manage_fees()
GET  /accountant/record-payments/       → accountant_record_payments()
GET  /accountant/manage-expenses/       → accountant_manage_expenses()
GET  /accountant/financial-reports/     → accountant_financial_reports()
```

### Librarian Routes
```
GET  /librarian/dashboard/              → librarian_dashboard()
GET  /librarian/manage-books/           → librarian_manage_books()
GET  /librarian/issue-books/            → librarian_issue_books()
GET  /librarian/return-books/           → librarian_return_books()
GET  /librarian/reports/                → librarian_reports()
```

### Secretary Routes
```
GET  /secretary/dashboard/              → secretary_dashboard()
GET  /secretary/manage-documents/       → secretary_manage_documents()
GET  /secretary/manage-correspondence/  → secretary_manage_correspondence()
GET  /secretary/schedule-meetings/      → secretary_schedule_meetings()
GET  /secretary/staff-records/          → secretary_staff_records()
GET  /secretary/student-records/        → secretary_student_records()
```

### Staff Routes
```
GET  /staff/dashboard/                  → staff_dashboard()
GET  /staff/mark-attendance/            → staff_mark_attendance()
GET  /staff/enter-results/              → staff_enter_results()
GET  /staff/view-classes/               → staff_view_classes()
GET  /staff/view-reports/               → staff_view_reports()
```

### Student Routes
```
GET  /student/dashboard/                → student_dashboard()
GET  /student/view-results/             → student_view_results()
GET  /student/view-timetable/           → student_view_timetable()
GET  /student/view-profile/             → student_view_profile()
GET  /student/attendance-record/        → student_attendance_record()
```

### Administrator Routes
```
GET  /administrator/dashboard/          → admin_staff_dashboard()
GET  /administrator/manage-users/       → administrator_manage_users()
GET  /administrator/system-settings/    → administrator_system_settings()
GET  /administrator/system-logs/        → administrator_system_logs()
GET  /administrator/backup/             → administrator_backup()
GET  /administrator/security/           → administrator_security()
```

## Public Routes (Existing)
```
GET  /                                  → public_home()
GET  /about/                            → about_school()
GET  /programs/                         → academic_programs()
GET  /news/                             → news_and_updates()
GET  /gallery/                          → gallery_and_events()
GET  /contact/                          → contact_school()
GET  /login/                            → public_login()
GET  /logout/                           → public_logout()
GET  /register/                         → public_register()
GET  /register/check/                   → public_register_check()
POST /register/ajax/                    → public_register_ajax()
```

## Total Routes Summary
- **Public Routes**: 11
- **Admin Routes**: 5
- **Academic Routes**: 5
- **Headmaster Routes**: 5
- **Accountant Routes**: 5
- **Librarian Routes**: 5
- **Secretary Routes**: 6
- **Staff Routes**: 5
- **Student Routes**: 5
- **Administrator Routes**: 6

**Total: 58 routes**

## URL Naming Convention

Route names follow the pattern: `{role}_{action}`

Examples:
- `admin_dashboard`
- `academic_enter_results`
- `headmaster_manage_staff`
- `accountant_manage_fees`
- `librarian_issue_books`
- `secretary_manage_documents`
- `staff_mark_attendance`
- `student_view_results`

## Template Locations

Each view renders from the corresponding template directory:

```
templates/
├── admin/
│   └── dashboard.html
├── academic/
│   ├── dashboard.html
│   ├── enter_results.html
│   ├── view_results.html
│   ├── performance_report.html
│   └── print_results.html
├── headmaster/
│   ├── dashboard.html
│   ├── manage_staff.html
│   ├── manage_students.html
│   ├── reports.html
│   └── approvals.html
├── accountant/
│   ├── dashboard.html
│   ├── manage_fees.html
│   ├── record_payments.html
│   ├── manage_expenses.html
│   └── financial_reports.html
├── librarian/
│   ├── dashboard.html
│   ├── manage_books.html
│   ├── issue_books.html
│   ├── return_books.html
│   └── reports.html
├── secretary/
│   ├── dashboard.html
│   ├── manage_documents.html
│   ├── manage_correspondence.html
│   ├── schedule_meetings.html
│   ├── staff_records.html
│   └── student_records.html
├── staff/
│   ├── dashboard.html
│   ├── mark_attendance.html
│   ├── enter_results.html
│   ├── view_classes.html
│   └── view_reports.html
└── students/
    ├── dashboard.html
    ├── view_results.html
    ├── view_timetable.html
    ├── view_profile.html
    └── attendance_record.html
```

## Configuration Changes Required

### Update config/urls.py:

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('public.urls')),
    path('', include('accounts.urls')),  # ADD THIS LINE
]
```

### Import in Templates:

Use URL reverse in templates:

```html
<!-- Example in navigation -->
<a href="{% url 'admin_dashboard' %}">Admin Dashboard</a>
<a href="{% url 'academic_dashboard' %}">Academic Dashboard</a>
<a href="{% url 'student_view_results' %}">My Results</a>
```

## Testing URLs

### Test with curl:
```bash
# Test admin dashboard (requires login)
curl http://localhost:8000/admin/dashboard/

# Test academic coordinator
curl http://localhost:8000/academic/dashboard/

# Test student
curl http://localhost:8000/student/dashboard/
```

### Test with Django shell:
```python
from django.urls import reverse

# Get URL
url = reverse('admin_dashboard')
# Output: /admin/dashboard/

url = reverse('academic_enter_results')
# Output: /academic/enter-results/
```
