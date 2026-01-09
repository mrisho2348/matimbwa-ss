# View Structure Documentation

## Overview

The application now has a well-organized view structure with separate view files for each user role. This provides better maintainability, scalability, and cleaner code organization.

## Directory Structure

```
accounts/
├── views/
│   ├── __init__.py
│   ├── hod_views.py              # HOD/Admin views
│   ├── academic_views.py          # Academic Coordinator views
│   ├── headmaster_views.py        # Headmaster views
│   ├── accountant_views.py        # Accountant views
│   ├── librarian_views.py         # Librarian views
│   ├── secretary_views.py         # Secretary views
│   ├── staff_views.py             # General Staff views
│   ├── student_views.py           # Student views
│   └── administrator_views.py     # System Administrator views
├── views.py                       # Main views file (imports from submodules)
└── urls.py                        # Dashboard URL routing
```

## View Files Description

### 1. hod_views.py
**HOD/Admin Dashboard Views**
- `admin_dashboard()` - Main HOD dashboard with school statistics
- `hod_manage_staff()` - Manage all staff members
- `hod_manage_students()` - Manage all students
- `hod_manage_results()` - Manage exam results
- `hod_system_settings()` - System configuration

### 2. academic_views.py
**Academic Coordinator Views**
- `academic_dashboard()` - Academic statistics and performance
- `academic_enter_results()` - Enter student examination results
- `academic_view_results()` - View all student results
- `academic_performance_report()` - Generate performance reports
- `academic_print_results()` - Print exam results

### 3. headmaster_views.py
**Headmaster Views**
- `headmaster_dashboard()` - Comprehensive school overview
- `headmaster_manage_staff()` - Manage school staff
- `headmaster_manage_students()` - Manage school students
- `headmaster_view_reports()` - View school reports
- `headmaster_approvals()` - Approve pending requests

### 4. accountant_views.py
**Accountant Views**
- `accountant_dashboard()` - Financial statistics and overview
- `accountant_manage_fees()` - Manage student fees
- `accountant_record_payments()` - Record fee payments
- `accountant_manage_expenses()` - Manage school expenses
- `accountant_financial_reports()` - Generate financial reports

### 5. librarian_views.py
**Librarian Views**
- `librarian_dashboard()` - Library management overview
- `librarian_manage_books()` - Manage book collection
- `librarian_issue_books()` - Issue books to students
- `librarian_return_books()` - Record book returns
- `librarian_reports()` - Generate library reports

### 6. secretary_views.py
**Secretary Views**
- `secretary_dashboard()` - Administrative overview
- `secretary_manage_documents()` - Manage school documents
- `secretary_manage_correspondence()` - Manage correspondence
- `secretary_schedule_meetings()` - Schedule meetings and events
- `secretary_staff_records()` - Manage staff records
- `secretary_student_records()` - Manage student records

### 7. staff_views.py
**General Staff Views**
- `staff_dashboard()` - General staff portal
- `staff_mark_attendance()` - Mark class attendance
- `staff_enter_results()` - Enter student results
- `staff_view_classes()` - View assigned classes
- `staff_view_reports()` - View personal reports

### 8. student_views.py
**Student Views**
- `student_dashboard()` - Student academic portal
- `student_view_results()` - View personal exam results
- `student_view_timetable()` - View class timetable
- `student_view_profile()` - View/edit personal profile
- `student_attendance_record()` - View attendance records

### 9. administrator_views.py
**System Administrator Views**
- `admin_staff_dashboard()` - System overview
- `administrator_manage_users()` - Manage system users
- `administrator_system_settings()` - System configuration
- `administrator_system_logs()` - View system logs
- `administrator_backup()` - Backup and recovery
- `administrator_security()` - Security management

## URL Routing

All dashboard URLs are prefixed with their respective role:

### HOD/Admin URLs
```
/admin/dashboard/
/admin/manage-staff/
/admin/manage-students/
/admin/manage-results/
/admin/system-settings/
```

### Academic Coordinator URLs
```
/academic/dashboard/
/academic/enter-results/
/academic/view-results/
/academic/performance-report/
/academic/print-results/
```

### Headmaster URLs
```
/headmaster/dashboard/
/headmaster/manage-staff/
/headmaster/manage-students/
/headmaster/reports/
/headmaster/approvals/
```

### Accountant URLs
```
/accountant/dashboard/
/accountant/manage-fees/
/accountant/record-payments/
/accountant/manage-expenses/
/accountant/financial-reports/
```

### Librarian URLs
```
/librarian/dashboard/
/librarian/manage-books/
/librarian/issue-books/
/librarian/return-books/
/librarian/reports/
```

### Secretary URLs
```
/secretary/dashboard/
/secretary/manage-documents/
/secretary/manage-correspondence/
/secretary/schedule-meetings/
/secretary/staff-records/
/secretary/student-records/
```

### Staff URLs
```
/staff/dashboard/
/staff/mark-attendance/
/staff/enter-results/
/staff/view-classes/
/staff/view-reports/
```

### Student URLs
```
/student/dashboard/
/student/view-results/
/student/view-timetable/
/student/view-profile/
/student/attendance-record/
```

### Administrator URLs
```
/administrator/dashboard/
/administrator/manage-users/
/administrator/system-settings/
/administrator/system-logs/
/administrator/backup/
/administrator/security/
```

## Security Features

Each view includes:
1. **Login Required** - All views require authentication using `@login_required` decorator
2. **Role-based Access Control** - Views check user type and staff role
3. **Unauthorized Access Handling** - Redirects to login page with error message

## How to Add New Views

1. Create the view function in the appropriate role file
2. Add the URL mapping in `accounts/urls.py`
3. Import the view in the main `accounts/views.py`
4. Create the corresponding template in the templates directory

Example:
```python
# In accounts/views/academic_views.py
@login_required
def new_academic_function(request):
    if request.user.user_type != "2" or request.user.staff.role != "Academic":
        messages.error(request, "Unauthorized access.")
        return redirect('public_login')
    
    context = {
        'page_title': 'New Function',
    }
    return render(request, 'academic/new_function.html', context)
```

## Configuration Updates Required

Update the following files:

1. **config/urls.py** - Include accounts URLs:
```python
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('public.urls')),
    path('', include('accounts.urls')),  # Add this line
]
```

2. **accounts/models.py** - Ensure user_type choices include student type "3" if needed:
```python
user_type_data = (
    (1, "HOD"),
    (2, "Staff"),
    (3, "Student"),  # If using students as users
)
```

## Best Practices

1. Keep view logic in the appropriate role file
2. Use consistent naming conventions (role_action)
3. Always include authorization checks
4. Use Django messages framework for user feedback
5. Create corresponding templates in role-specific directories
6. Document complex business logic with comments
