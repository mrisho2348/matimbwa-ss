# Quick Setup Guide for New View Structure

## Step 1: Update Main Configuration File

Replace the content of `config/urls.py` with the following:

```python
"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('public.urls')),
    path('', include('accounts.urls')),  # Add this line for dashboards
]
```

## Step 2: Verify View Files Are Created

Check that the following files exist in `accounts/views/`:
- ✓ `__init__.py`
- ✓ `hod_views.py`
- ✓ `academic_views.py`
- ✓ `headmaster_views.py`
- ✓ `accountant_views.py`
- ✓ `librarian_views.py`
- ✓ `secretary_views.py`
- ✓ `staff_views.py`
- ✓ `student_views.py`
- ✓ `administrator_views.py`

## Step 3: Update Django Settings (if needed)

Ensure `INSTALLED_APPS` in `config/settings.py` includes:
```python
INSTALLED_APPS = [
    # ...
    'accounts',
    'public',
    # ...
]
```

## Step 4: Test URLs

Run Django development server:
```bash
python manage.py runserver
```

Test URL availability:
```bash
# Visit in browser or use curl
http://localhost:8000/admin/dashboard/
http://localhost:8000/academic/dashboard/
http://localhost:8000/student/dashboard/
# etc.
```

**Note**: You'll need to login first at `/login/` or `/public/login/`

## Step 5: Create Missing Templates

Create template files for each dashboard. The views expect templates at:

### Required Template Paths:

```
templates/
├── admin/
│   ├── dashboard.html ✓
│   ├── manage_staff.html
│   ├── manage_students.html
│   ├── manage_results.html
│   └── settings.html
├── academic/
│   ├── dashboard.html ✓
│   ├── enter_results.html
│   ├── view_results.html
│   ├── performance_report.html
│   └── print_results.html
├── headmaster/
│   ├── dashboard.html ✓
│   ├── manage_staff.html
│   ├── manage_students.html
│   ├── reports.html
│   └── approvals.html
├── accountant/
│   ├── dashboard.html ✓
│   ├── manage_fees.html
│   ├── record_payments.html
│   ├── manage_expenses.html
│   └── financial_reports.html
├── librarian/
│   ├── dashboard.html ✓
│   ├── manage_books.html
│   ├── issue_books.html
│   ├── return_books.html
│   └── reports.html
├── secretary/
│   ├── dashboard.html (use staff/dashboard.html)
│   ├── manage_documents.html
│   ├── manage_correspondence.html
│   ├── schedule_meetings.html
│   ├── staff_records.html
│   └── student_records.html
├── staff/
│   ├── dashboard.html ✓
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

**✓ = Already exists**

## Step 6: Test User Access

Create test users with different roles:

```bash
python manage.py shell
```

```python
from accounts.models import CustomUser, Staffs

# Create HOD user
hod = CustomUser.objects.create_user(
    username='hod_user',
    email='hod@school.com',
    password='testpass123',
    user_type=1
)

# Create Academic staff
academic_user = CustomUser.objects.create_user(
    username='academic_staff',
    email='academic@school.com',
    password='testpass123',
    user_type=2
)
academic_staff = Staffs.objects.create(admin=academic_user, role='Academic')

# Create Accountant staff
accountant_user = CustomUser.objects.create_user(
    username='accountant_staff',
    email='accountant@school.com',
    password='testpass123',
    user_type=2
)
accountant_staff = Staffs.objects.create(admin=accountant_user, role='Accountant')

# Login and test
# Visit /login/ → enter credentials → check dashboard redirects
```

## Step 7: Verify Redirects Work

Test that users are properly redirected to their role-based dashboards:

1. Login as HOD → should redirect to `/admin/dashboard/`
2. Login as Academic → should redirect to `/academic/dashboard/`
3. Login as Accountant → should redirect to `/accountant/dashboard/`
4. Login as Headmaster → should redirect to `/headmaster/dashboard/`
5. Login as Librarian → should redirect to `/librarian/dashboard/`
6. Login as Secretary → should redirect to `/secretary/dashboard/`
7. Login as Staff → should redirect to `/staff/dashboard/`
8. Login as Student → should redirect to `/student/dashboard/` (if user_type=3)

## Step 8: File Cleanup (Optional)

If everything works, you can remove:
- `accounts/views_old.py` (backup of old views)
- `config/urls_new.py` (reference file)

## Troubleshooting

### Issue: ModuleNotFoundError: No module named 'accounts.views.academic_views'

**Solution**: Ensure the `accounts/views/` directory exists with all view files.

### Issue: TemplateDoesNotExist

**Solution**: Create the required template files in the `templates/` directory for each view.

### Issue: Unauthorized access error

**Solution**: Check that user has correct `user_type` and `staff.role` assigned.

### Issue: URL not found (404)

**Solution**: Ensure `config/urls.py` includes `path('', include('accounts.urls'))`

## Command Reference

```bash
# Start development server
python manage.py runserver

# Check URL patterns
python manage.py show_urls

# Run tests
python manage.py test

# Migrate database
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

## Documentation Files

Created documentation files for reference:
- `VIEW_STRUCTURE.md` - Detailed view structure and organization
- `VIEWS_IMPLEMENTATION_SUMMARY.md` - Summary of all created files
- `URL_MAPPING_REFERENCE.md` - Complete URL mapping and routes
- `QUICK_SETUP_GUIDE.md` - This file

## Support

For each role's functions and URLs, refer to:
- View functions: `accounts/views/{role}_views.py`
- URL routes: `accounts/urls.py`
- Templates: `templates/{role}/`
- Documentation: `VIEW_STRUCTURE.md` or `URL_MAPPING_REFERENCE.md`
