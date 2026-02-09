# accounts/views/admin_views.py
from datetime import datetime, timedelta,date
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, F, Prefetch
from django.utils import timezone
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from weasyprint import HTML
from accounts.forms.admin_forms import AdminPreferencesForm, AdminProfileUpdateForm
from accounts.forms.student_forms import ParentForm, ParentStudentForm, PreviousSchoolForm, StudentEditForm, StudentForm,StudentFilterForm
from accounts.models import GENDER_CHOICES, ROLE_CHOICES, CustomUser, Department, Notification, Staffs, AdminHOD, SystemLog, TeachingAssignment
from core.models import (
    Combination, CombinationSubject, EducationalLevel, AcademicYear, Term, Subject, 
    ClassLevel, StreamClass
)
from weasyprint.text.fonts import FontConfiguration
from students.models import RELATIONSHIP_CHOICES, STATUS_CHOICES, Parent, PreviousSchool, Student
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_date
from django.db import IntegrityError
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST,require_GET
from django.db import transaction
from django.db.models import Value
from django.db.models.functions import Concat
from django.db.models import CharField
from django.contrib.auth.hashers import make_password
from django.core.files.storage import default_storage
import os
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string

# ============================================================================
# DASHBOARD VIEWS
# ============================================================================

@login_required
def dashboard(request):
    """
    Administrator Dashboard
    Displays system statistics, notifications, and recent activities
    """

    # ==============================
    # BASIC STATISTICS
    # ==============================
    total_users = CustomUser.objects.count()
    total_staff = Staffs.objects.count()
    total_students = Student.objects.count()

    active_staff = Staffs.objects.filter(admin__is_active=True).count()
    inactive_staff = Staffs.objects.filter(admin__is_active=False).count()

    active_students = Student.objects.filter(status='active').count()
    graduated_students = Student.objects.filter(status='completed').count()

    # ==============================
    # NOTIFICATIONS (LAST 24 HOURS)
    # ==============================
    notification_qs = Notification.objects.filter(
        created_at__gte=timezone.now() - timedelta(hours=24)
    )

    notifications = notification_qs.order_by('-created_at')[:5]
    unread_notifications = notification_qs.filter(read=False).count()

    # ==============================
    # RECENT SYSTEM ACTIVITIES (7 DAYS)
    # ==============================
    recent_logs = (
        SystemLog.objects
        .filter(timestamp__gte=timezone.now() - timedelta(days=7))
        .select_related('user')
        .order_by('-timestamp')[:10]
    )

    activities = []
    for log in recent_logs:
        user = log.user
        activities.append({
            "description": log.description,
            "user_name": user.get_full_name() if user else "System",
            "user_initials": (
                f"{user.first_name[:1]}{user.last_name[:1]}".upper()
                if user and user.first_name and user.last_name
                else "SY"
            ),
            "ip_address": log.ip_address,
            "timestamp": log.timestamp,
            "type": log.log_type,
            "icon": get_activity_icon(log.log_type),
        })

    # ==============================
    # CLASS DISTRIBUTION
    # ==============================
    class_distribution = (
        ClassLevel.objects
        .annotate(student_count=Count('students'))
        .values('name', 'student_count')
    )

    # ==============================
    # ACTIVE SESSIONS (PLACEHOLDER)
    # ==============================
    active_sessions = 12  # Replace with session-based logic if needed

    # ==============================
    # CONTEXT
    # ==============================
    context = {
        "page_title": "Administrator Dashboard",

        # Stats
        "total_users": total_users,
        "total_staff": total_staff,
        "total_students": total_students,
        "active_staff": active_staff,
        "inactive_staff": inactive_staff,
        "active_students": active_students,
        "graduated_students": graduated_students,

        # Notifications
        "notifications": notifications,
        "unread_notifications": unread_notifications,

        # Activities
        "activities": activities,

        # Analytics
        "class_distribution": list(class_distribution),
        "active_sessions": active_sessions,

        # Meta
        "current_date": timezone.now(),
    }

    return render(request, "admin/dashboard.html", context)

def get_activity_icon(log_type):
    """Map log type to Bootstrap icon"""
    icon_map = {
        'create': 'plus-circle',
        'update': 'pencil-square',
        'delete': 'trash',
        'login': 'box-arrow-in-right',
        'logout': 'box-arrow-right',
        'security': 'shield-exclamation',
        'system': 'gear',
        'error': 'exclamation-circle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle',
        'success': 'check-circle',
    }
    return icon_map.get(log_type, 'activity')


@login_required
def analytics(request):
    """Advanced analytics and insights"""
    context = {
        'page_title': 'Analytics Dashboard',
    }
    return render(request, 'admin/analytics.html', context)

@login_required
def reports(request):
    """General reports overview"""
    context = {
        'page_title': 'Reports Overview',
    }
    return render(request, 'admin/reports.html', context)

# ============================================================================
# ACADEMIC MANAGEMENT VIEWS
# ============================================================================


# ============================================================================
# PROFILE & ACCOUNT MANAGEMENT VIEWS
# ============================================================================

@login_required
def profile_view(request):
    """View administrator profile with details and statistics"""
    try:
        admin_profile = AdminHOD.objects.get(admin=request.user)
    except AdminHOD.DoesNotExist:
        # Create admin profile if it doesn't exist
        admin_profile = AdminHOD.objects.create(admin=request.user)
    
    # Get recent activities
    recent_activities = SystemLog.objects.filter(
        user=request.user,
        timestamp__gte=timezone.now() - timedelta(days=7)
    ).order_by('-timestamp')[:10]
    
    # Get login statistics
    login_stats = {
        'last_login': request.user.last_login,
        'total_logins': SystemLog.objects.filter(
            user=request.user, 
            log_type='login'
        ).count(),
        'failed_attempts': SystemLog.objects.filter(
            user=request.user,
            log_type='login_failed'
        ).count(),
    }
    
    context = {
        'page_title': 'My Profile',
        'admin_profile': admin_profile,
        'recent_activities': recent_activities,
        'login_stats': login_stats,
        'user_since': request.user.date_joined,
    }
    return render(request, 'admin/account/profile.html', context)

@login_required
def profile_update(request):
    """Update administrator profile information"""
    if request.method == 'POST':
        form = AdminProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('admin:admin_profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AdminProfileUpdateForm(instance=request.user)
    
    context = {
        'page_title': 'Update Profile',
        'form': form,
    }
    return render(request, 'admin/account/profile_update.html', context)

@login_required
def profile_picture_update(request):
    """Update administrator profile picture"""
    if request.method == 'POST' and request.FILES.get('profile_picture'):
        try:
            profile_picture = request.FILES['profile_picture']
            
            # Validate file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif']
            if profile_picture.content_type not in allowed_types:
                messages.error(request, 'Invalid file type. Please upload JPEG, PNG, or GIF images.')
                return redirect('admin:admin_profile')
            
            # Validate file size (max 5MB)
            if profile_picture.size > 5 * 1024 * 1024:
                messages.error(request, 'File size too large. Maximum size is 5MB.')
                return redirect('admin:admin_profile')
            
            # Save profile picture
            # In a real implementation, you would save to the appropriate model field
            # For now, we'll store it in a session variable or save path
            request.session['admin_profile_picture'] = profile_picture.name
            
            messages.success(request, 'Profile picture updated successfully!')
            return redirect('admin:admin_profile')
            
        except Exception as e:
            messages.error(request, f'Error updating profile picture: {str(e)}')
    
    return redirect('admin_profile')



@login_required
def change_password(request):
    """Change administrator password with validation"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important to keep user logged in
            
            # Log the password change
            SystemLog.objects.create(
                user=request.user,
                log_type='security',
                description=f'Password changed successfully',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, '✅ Password changed successfully!')
            return redirect('admin:admin_security')
        else:
            messages.error(request, '⚠️ Please correct the errors below.')
    else:
        form = PasswordChangeForm(request.user)
    
    context = {
        'page_title': 'Change Password',
        'form': form,
    }
    return render(request, 'admin/account/change_password.html', context)






# ============================================================================
# AJAX ENDPOINTS FOR PROFILE MANAGEMENT
# ============================================================================

@login_required
def ajax_check_password_strength(request):
    """AJAX endpoint to check password strength"""
    password = request.GET.get('password', '')
    
    if not password:
        return JsonResponse({'error': 'No password provided'})
    
    # Simple password strength calculation
    strength = 0
    feedback = []
    
    if len(password) >= 8:
        strength += 1
    else:
        feedback.append('Password should be at least 8 characters')
    
    if any(c.isupper() for c in password) and any(c.islower() for c in password):
        strength += 1
    else:
        feedback.append('Include both uppercase and lowercase letters')
    
    if any(c.isdigit() for c in password):
        strength += 1
    else:
        feedback.append('Include at least one number')
    
    special_chars = '!@#$%^&*()_+-=[]{}|;:,.<>?'
    if any(c in special_chars for c in password):
        strength += 1
    else:
        feedback.append('Include at least one special character')
    
    # Strength categories
    if strength <= 1:
        category = 'Very Weak'
        color = '#e74c3c'
    elif strength == 2:
        category = 'Weak'
        color = '#e67e22'
    elif strength == 3:
        category = 'Good'
        color = '#f1c40f'
    else:
        category = 'Strong'
        color = '#2ecc71'
    
    return JsonResponse({
        'strength': strength,
        'category': category,
        'color': color,
        'feedback': feedback,
        'percentage': (strength / 4) * 100
    })

@login_required
def ajax_validate_email(request):
    """AJAX endpoint to validate email uniqueness"""
    email = request.GET.get('email', '')
    
    if not email:
        return JsonResponse({'error': 'No email provided'})
    
    # Check if email exists (excluding current user)
    exists = CustomUser.objects.filter(
        email__iexact=email
    ).exclude(id=request.user.id).exists()
    
    return JsonResponse({
        'available': not exists,
        'message': 'Email already in use' if exists else 'Email available'
    })

@login_required
def ajax_get_security_summary(request):
    """AJAX endpoint to get security summary"""
    # Get security metrics
    metrics = {
        'password_age_days': (
            (timezone.now() - request.user.last_password_change).days 
            if hasattr(request.user, 'last_password_change') 
            else 0
        ),
        'failed_attempts_24h': SystemLog.objects.filter(
            user=request.user,
            log_type='login_failed',
            timestamp__gte=timezone.now() - timedelta(hours=24)
        ).count(),
        'unique_ip_addresses': SystemLog.objects.filter(
            user=request.user,
            log_type='login'
        ).values('ip_address').distinct().count(),
        'account_age_days': (timezone.now() - request.user.date_joined).days,
    }
    
    # Calculate security score (0-100)
    security_score = 100
    
    # Deduct for old password
    if metrics['password_age_days'] > 90:
        security_score -= 20
    elif metrics['password_age_days'] > 180:
        security_score -= 40
    
    # Deduct for failed attempts
    if metrics['failed_attempts_24h'] > 5:
        security_score -= 15
    elif metrics['failed_attempts_24h'] > 10:
        security_score -= 30
    
    # Ensure score is between 0-100
    security_score = max(0, min(100, security_score))
    
    # Determine security level
    if security_score >= 80:
        level = 'Excellent'
        color = '#27ae60'
    elif security_score >= 60:
        level = 'Good'
        color = '#f39c12'
    else:
        level = 'Needs Improvement'
        color = '#e74c3c'
    
    return JsonResponse({
        'metrics': metrics,
        'security_score': security_score,
        'security_level': level,
        'color': color,
        'recommendations': [
            'Change your password every 90 days',
            'Enable two-factor authentication',
            'Review your recent login activity',
            'Log out from unused devices'
        ]
    })

@login_required
def educational_levels_list(request):
    """Display list of educational levels"""
    levels = EducationalLevel.objects.all().order_by('name')
    
    context = {
        'page_title': 'Educational Levels',
        'education_levels': levels,
    }
    return render(request, 'admin/academic/educational_levels_list.html', context)


@login_required
def educational_levels_crud(request):
    """Handle AJAX CRUD operations for educational levels"""
    if request.method == 'POST':
        action = request.POST.get('action', '').lower()
        
        try:
            if action == 'create':
                name = request.POST.get('name', '').strip()
                code = request.POST.get('code', '').strip()
                description = request.POST.get('description', '').strip()
                
                if not name or not code:
                    return JsonResponse({
                        'success': False,
                        'message': 'Name and Code are required.'
                    })
                
                # Check for duplicates
                if EducationalLevel.objects.filter(code__iexact=code).exists():
                    return JsonResponse({
                        'success': False,
                        'message': f'Educational level with code "{code}" already exists.'
                    })
                
                level = EducationalLevel.objects.create(
                    name=name,
                    code=code,
                    description=description
                )
                
                return JsonResponse({
                    'success': True,
                    'message': f'Educational level "{name}" created successfully.',
                    'level': {
                        'id': level.id,
                        'name': level.name,
                        'code': level.code,
                        'description': level.description,
                    }
                })
                
            elif action == 'update':
                level_id = request.POST.get('id')
                if not level_id:
                    return JsonResponse({
                        'success': False,
                        'message': 'Level ID is required.'
                    })
                
                level = get_object_or_404(EducationalLevel, id=level_id)
                
                name = request.POST.get('name', '').strip()
                code = request.POST.get('code', '').strip()
                description = request.POST.get('description', '').strip()
                
                if not name or not code:
                    return JsonResponse({
                        'success': False,
                        'message': 'Name and Code are required.'
                    })
                
                # Check for duplicate code (exclude current)
                if EducationalLevel.objects.filter(
                    code__iexact=code
                ).exclude(id=level.id).exists():
                    return JsonResponse({
                        'success': False,
                        'message': f'Educational level with code "{code}" already exists.'
                    })
                
                level.name = name
                level.code = code
                level.description = description
                level.save()
                
                return JsonResponse({
                    'success': True,
                    'message': f'Educational level "{name}" updated successfully.',
                    'level': {
                        'id': level.id,
                        'name': level.name,
                        'code': level.code,
                        'description': level.description,
                    }
                })
                
            elif action == 'delete':
                level_id = request.POST.get('id')
                if not level_id:
                    return JsonResponse({
                        'success': False,
                        'message': 'Level ID is required.'
                    })
                
                level = get_object_or_404(EducationalLevel, id=level_id)
                level_name = level.name
                level.delete()
                
                return JsonResponse({
                    'success': True,
                    'message': f'Educational level "{level_name}" deleted successfully.',
                    'id': level_id
                })
            
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid action.'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'POST request required.'
    })


# Legacy view - redirect to list for backward compatibility
@login_required
def educational_levels(request):
    """Redirect to educational_levels_list for backward compatibility"""
    return redirect('admin_educational_levels_list')

@login_required
def academic_years_list(request):
    """Display list of academic years"""
    years = AcademicYear.objects.all().order_by('-start_date')
    
    context = {
        'page_title': 'Academic Years',
        'academic_years': years,
    }
    return render(request, 'admin/academic/academic_years_list.html', context)


@login_required
def academic_years_crud(request):
    """Handle AJAX CRUD operations for academic years"""
    if request.method == 'POST':
        action = request.POST.get('action', '').lower()
        
        try:
            if action == 'create':
                name = request.POST.get('name', '').strip()
                start_date_str = request.POST.get('start_date', '').strip()
                end_date_str = request.POST.get('end_date', '').strip()

                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                
                if not name or not start_date or not end_date:
                    return JsonResponse({
                        'success': False,
                        'message': 'Name, start date, and end date are required.'
                    })
                
                # Check for duplicates
                if AcademicYear.objects.filter(name__iexact=name).exists():
                    return JsonResponse({
                        'success': False,
                        'message': f'Academic year "{name}" already exists.'
                    })
                
                year = AcademicYear.objects.create(
                    name=name,
                    start_date=start_date,
                    end_date=end_date
                )
                
                return JsonResponse({
                    'success': True,
                    'message': f'Academic year "{name}" created successfully.',
                    'year': {
                        'id': year.id,
                        'name': year.name,
                        'start_date': year.start_date.strftime('%Y-%m-%d'),
                        'end_date': year.end_date.strftime('%Y-%m-%d'),
                        'is_active': year.is_active,
                    }
                })
                
            elif action == 'update':
                year_id = request.POST.get('id')
                if not year_id:
                    return JsonResponse({
                        'success': False,
                        'message': 'Year ID is required.'
                    })
                
                year = get_object_or_404(AcademicYear, id=year_id)
                
                name = request.POST.get('name', '').strip()
                start_date_str = request.POST.get('start_date', '').strip()
                end_date_str = request.POST.get('end_date', '').strip()

                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                
                if not name or not start_date or not end_date:
                    return JsonResponse({
                        'success': False,
                        'message': 'Name, start date, and end date are required.'
                    })
                
                # Check for duplicate name (exclude current)
                if AcademicYear.objects.filter(
                    name__iexact=name
                ).exclude(id=year.id).exists():
                    return JsonResponse({
                        'success': False,
                        'message': f'Academic year "{name}" already exists.'
                    })
                
                year.name = name
                year.start_date = start_date
                year.end_date = end_date
                year.save()
                
                return JsonResponse({
                    'success': True,
                    'message': f'Academic year "{name}" updated successfully.',
                    'year': {
                        'id': year.id,
                        'name': year.name,
                        'start_date': year.start_date.strftime('%Y-%m-%d'),
                        'end_date': year.end_date.strftime('%Y-%m-%d'),
                        'is_active': year.is_active,
                    }
                })
                
            elif action == 'delete':
                year_id = request.POST.get('id')
                if not year_id:
                    return JsonResponse({
                        'success': False,
                        'message': 'Year ID is required.'
                    })
                
                year = get_object_or_404(AcademicYear, id=year_id)
                year_name = year.name
                year.delete()
                
                return JsonResponse({
                    'success': True,
                    'message': f'Academic year "{year_name}" deleted successfully.',
                    'id': year_id
                })
            
            elif action == 'activate':
                year_id = request.POST.get('id')
                if not year_id:
                    return JsonResponse({
                        'success': False,
                        'message': 'Year ID is required.'
                    })
                
                year = get_object_or_404(AcademicYear, id=year_id)
                
                # Deactivate all other years
                AcademicYear.objects.exclude(id=year.id).update(is_active=False)
                
                # Activate this year
                year.is_active = True
                year.save()
                
                return JsonResponse({
                    'success': True,
                    'message': f'Academic year "{year.name}" activated successfully.',
                    'year': {
                        'id': year.id,
                        'name': year.name,
                        'is_active': year.is_active,
                    }
                })
            
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid action.'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'POST request required.'
    })


# Legacy view - redirect to list for backward compatibility
@login_required
def academic_years(request):
    """Redirect to academic_years_list for backward compatibility"""
    return redirect('admin_academic_years_list')

@login_required
def terms_list(request):
    """Display list of terms with academic years"""

    academic_years = AcademicYear.objects.all().order_by('-start_date')

    terms = (
        Term.objects
        .select_related('academic_year')
        .order_by('-academic_year__start_date', 'term_number')
    )

    active_academic_year = AcademicYear.objects.filter(is_active=True).first()

    context = {
        'page_title': 'Terms',
        'terms': terms,
        'academic_years': academic_years,          # ✅ all academic years
        'active_academic_year': active_academic_year,  # ✅ optional but useful
    }

    return render(request, 'admin/academic/terms_list.html', context)



@login_required
def terms_crud(request):
    """Handle AJAX CRUD operations for terms"""
    if request.method == 'POST':
        action = request.POST.get('action', '').lower()
        
        try:
            if action == 'create':
                return create_term(request)
            elif action == 'update':
                return update_term(request)
            elif action == 'delete':
                return delete_term(request)
            elif action == 'activate':
                return activate_term(request)
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid action specified.'
                })
                
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'POST request required.'
    })


def create_term(request):
    """Create a new term"""
    # Get and validate required fields
    academic_year_id = request.POST.get('academic_year')
    if not academic_year_id:
        return JsonResponse({
            'success': False,
            'message': 'Academic year is required.'
        })
    
    term_number = request.POST.get('term_number')
    if not term_number:
        return JsonResponse({
            'success': False,
            'message': 'Term number is required.'
        })
    
    start_date_str = request.POST.get('start_date')
    end_date_str = request.POST.get('end_date')
    
    if not start_date_str or not end_date_str:
        return JsonResponse({
            'success': False,
            'message': 'Start date and end date are required.'
        })
    
    # Parse dates
    start_date = parse_date(start_date_str)
    end_date = parse_date(end_date_str)
    
    if not start_date or not end_date:
        return JsonResponse({
            'success': False,
            'message': 'Invalid date format. Please use YYYY-MM-DD format.'
        })
    
    # Validate dates
    validation_errors = validate_term_dates(start_date, end_date)
    if validation_errors:
        return JsonResponse({
            'success': False,
            'message': ' '.join(validation_errors)
        })
    
    # Get academic year
    try:
        academic_year = AcademicYear.objects.get(id=academic_year_id)
    except AcademicYear.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Selected academic year does not exist.'
        })
    
    # Validate term dates are within academic year
    if start_date < academic_year.start_date:
        return JsonResponse({
            'success': False,
            'message': f'Term start date cannot be before academic year start date ({academic_year.start_date}).'
        })
    
    if end_date > academic_year.end_date:
        return JsonResponse({
            'success': False,
            'message': f'Term end date cannot be after academic year end date ({academic_year.end_date}).'
        })
    
    # Check for duplicate term in same academic year
    if Term.objects.filter(
        academic_year=academic_year,
        term_number=term_number
    ).exists():
        return JsonResponse({
            'success': False,
            'message': f'Term {term_number} already exists for academic year {academic_year.name}.'
        })
    
    # Check for date overlaps with existing terms in same academic year
    overlapping_terms = Term.objects.filter(
        academic_year=academic_year,
        start_date__lt=end_date,
        end_date__gt=start_date
    )
    
    if overlapping_terms.exists():
        overlapping_term = overlapping_terms.first()
        return JsonResponse({
            'success': False,
            'message': f'Date range overlaps with {overlapping_term.get_term_number_display()} ({overlapping_term.start_date} to {overlapping_term.end_date}).'
        })
    
    try:
        # Create the term
        term = Term.objects.create(
            academic_year=academic_year,
            term_number=term_number,
            start_date=start_date,
            end_date=end_date,
            is_active=False  # New terms are inactive by default
        )
        
        return JsonResponse({
            'success': True,
            'message': f'{term.get_term_number_display()} created successfully for {academic_year.name}.',
            'term': {
                'id': term.id,
                'academic_year_id': term.academic_year.id,
                'academic_year_name': term.academic_year.name,
                'term_number': term.term_number,
                'term_display': term.get_term_number_display(),
                'start_date': term.start_date.strftime('%Y-%m-%d'),
                'end_date': term.end_date.strftime('%Y-%m-%d'),
                'is_active': term.is_active
            }
        })
        
    except IntegrityError:
        return JsonResponse({
            'success': False,
            'message': 'A term with these details already exists.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error creating term: {str(e)}'
        })


def update_term(request):
    """Update an existing term"""
    term_id = request.POST.get('id')
    if not term_id:
        return JsonResponse({
            'success': False,
            'message': 'Term ID is required.'
        })
    
    try:
        term = Term.objects.get(id=term_id)
    except Term.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Term not found.'
        })
    
    # Check if term is active (prevent editing active term)
    if term.is_active:
        return JsonResponse({
            'success': False,
            'message': 'Cannot edit an active term. Deactivate it first.'
        })
    
    # Get and validate required fields
    academic_year_id = request.POST.get('academic_year')
    term_number = request.POST.get('term_number')
    start_date_str = request.POST.get('start_date')
    end_date_str = request.POST.get('end_date')
    
    if not all([academic_year_id, term_number, start_date_str, end_date_str]):
        return JsonResponse({
            'success': False,
            'message': 'All fields are required.'
        })
    
    # Parse dates
    start_date = parse_date(start_date_str)
    end_date = parse_date(end_date_str)
    
    if not start_date or not end_date:
        return JsonResponse({
            'success': False,
            'message': 'Invalid date format.'
        })
    
    # Validate dates
    validation_errors = validate_term_dates(start_date, end_date)
    if validation_errors:
        return JsonResponse({
            'success': False,
            'message': ' '.join(validation_errors)
        })
    
    # Get academic year
    try:
        academic_year = AcademicYear.objects.get(id=academic_year_id)
    except AcademicYear.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Selected academic year does not exist.'
        })
    
    # Validate term dates are within academic year
    if start_date < academic_year.start_date:
        return JsonResponse({
            'success': False,
            'message': f'Term start date cannot be before academic year start date ({academic_year.start_date}).'
        })
    
    if end_date > academic_year.end_date:
        return JsonResponse({
            'success': False,
            'message': f'Term end date cannot be after academic year end date ({academic_year.end_date}).'
        })
    
    # Check for duplicate term in same academic year (excluding current term)
    if Term.objects.filter(
        academic_year=academic_year,
        term_number=term_number
    ).exclude(id=term.id).exists():
        return JsonResponse({
            'success': False,
            'message': f'Term {term_number} already exists for academic year {academic_year.name}.'
        })
    
    # Check for date overlaps with other terms in same academic year
    overlapping_terms = Term.objects.filter(
        academic_year=academic_year,
        start_date__lt=end_date,
        end_date__gt=start_date
    ).exclude(id=term.id)
    
    if overlapping_terms.exists():
        overlapping_term = overlapping_terms.first()
        return JsonResponse({
            'success': False,
            'message': f'Date range overlaps with {overlapping_term.get_term_number_display()} ({overlapping_term.start_date} to {overlapping_term.end_date}).'
        })
    
    try:
        # Update the term
        term.academic_year = academic_year
        term.term_number = term_number
        term.start_date = start_date
        term.end_date = end_date
        term.full_clean()  # Run model validation
        term.save()
        
        return JsonResponse({
            'success': True,
            'message': f'{term.get_term_number_display()} updated successfully.',
            'term': {
                'id': term.id,
                'academic_year_id': term.academic_year.id,
                'academic_year_name': term.academic_year.name,
                'term_number': term.term_number,
                'term_display': term.get_term_number_display(),
                'start_date': term.start_date.strftime('%Y-%m-%d'),
                'end_date': term.end_date.strftime('%Y-%m-%d'),
                'is_active': term.is_active
            }
        })
        
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })
    except IntegrityError:
        return JsonResponse({
            'success': False,
            'message': 'A term with these details already exists.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating term: {str(e)}'
        })


def delete_term(request):
    """Delete a term"""
    term_id = request.POST.get('id')
    if not term_id:
        return JsonResponse({
            'success': False,
            'message': 'Term ID is required.'
        })
    
    try:
        term = Term.objects.get(id=term_id)
    except Term.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Term not found.'
        })
    
    # Check if term is active
    if term.is_active:
        return JsonResponse({
            'success': False,
            'message': 'Cannot delete an active term. Deactivate it first.'
        })
    
    # Check if term has any associated data (optional - add your own checks)
     # if term.exam_set.exists():
      #  return JsonResponse({
       # 'success': False,
        #    'message': 'Cannot delete term with associated exams.'
       #  })
    
    term_info = f'{term.get_term_number_display()} ({term.academic_year.name})'
    
    try:
        term.delete()
        return JsonResponse({
            'success': True,
            'message': f'{term_info} deleted successfully.',
            'id': term_id
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting term: {str(e)}'
        })


def activate_term(request):
    """Activate a term (deactivates all other terms)"""
    term_id = request.POST.get('id')
    if not term_id:
        return JsonResponse({
            'success': False,
            'message': 'Term ID is required.'
        })
    
    try:
        term = Term.objects.get(id=term_id)
    except Term.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Term not found.'
        })
    
    # Check if term is already active
    if term.is_active:
        return JsonResponse({
            'success': False,
            'message': 'Term is already active.'
        })
    
    # Check if term dates are valid (not in the past)
    today = date.today()
    if term.end_date < today:
        return JsonResponse({
            'success': False,
            'message': 'Cannot activate a term that has already ended.'
        })
    
    try:
        # Activate the term (this will automatically deactivate others via save method)
        term.is_active = True
        term.save()
        
        return JsonResponse({
            'success': True,
            'message': f'{term.get_term_number_display()} activated successfully. All other terms are now inactive.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error activating term: {str(e)}'
        })


def validate_term_dates(start_date, end_date):
    """Validate term dates"""
    errors = []
    
    # Check if start date is before end date
    if start_date >= end_date:
        errors.append('Start date must be before end date.')
    
    # Check if dates are in the same year
    if start_date.year != end_date.year:
        errors.append('Start date and end date must be in the same year.')
    
    # Check if start date is not in the past (optional)
    today = date.today()
    if start_date < today:
        # Allow past dates for historical terms
        pass
    
    return errors

# Legacy view - redirect to list for backward compatibility
@login_required
def terms(request):
    """Redirect to terms_list for backward compatibility"""
    return redirect('admin_terms_list')


@login_required
def subjects_list(request):
    """Display subjects management page"""
    subjects = Subject.objects.select_related('educational_level').all().order_by('educational_level', 'name')
    educational_levels = EducationalLevel.objects.filter(is_active=True)
    
    # Count active subjects
    active_subjects_count = subjects.filter(is_active=True).count()
    
    context = {
        'subjects': subjects,
        'educational_levels': educational_levels,
        'active_subjects_count': active_subjects_count,
    }
    
    return render(request, 'admin/academic/subjects_list.html', context)


@login_required
def subjects_crud(request):
    """Handle AJAX CRUD operations for subjects"""
    if request.method == 'POST':
        action = request.POST.get('action', '').lower()
        
        try:
            if action == 'create':
                return create_subject(request)
            elif action == 'update':
                return update_subject(request)
            elif action == 'toggle_status':
                return toggle_subject_status(request)
            elif action == 'toggle_compulsory':
                return toggle_subject_compulsory(request)
            elif action == 'delete':
                return delete_subject(request)
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid action specified.'
                })
                
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'POST request required.'
    })


def create_subject(request):
    """Create a new subject"""
    # Get and validate required fields
    educational_level_id = request.POST.get('educational_level')
    if not educational_level_id:
        return JsonResponse({
            'success': False,
            'message': 'Educational level is required.'
        })
    
    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({
            'success': False,
            'message': 'Subject name is required.'
        })
    
    code = request.POST.get('code', '').strip()
    if not code:
        return JsonResponse({
            'success': False,
            'message': 'Subject code is required.'
        })
    
    # Validate name and code length
    if len(name) < 2:
        return JsonResponse({
            'success': False,
            'message': 'Subject name must be at least 2 characters long.'
        })
    
    if len(code) > 20:
        return JsonResponse({
            'success': False,
            'message': 'Subject code cannot exceed 20 characters.'
        })
    
    if len(name) > 100:
        return JsonResponse({
            'success': False,
            'message': 'Subject name cannot exceed 100 characters.'
        })
    
    # Validate code format
    if not code.replace('-', '').replace('_', '').isalnum():
        return JsonResponse({
            'success': False,
            'message': 'Subject code can only contain letters, numbers, hyphens, and underscores.'
        })
    
    # Get educational level
    try:
        educational_level = EducationalLevel.objects.get(id=educational_level_id)
    except EducationalLevel.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Selected educational level does not exist.'
        })
    
    # Check for duplicate subject code within the same educational level
    if Subject.objects.filter(
        educational_level=educational_level,
        code__iexact=code
    ).exists():
        return JsonResponse({
            'success': False,
            'message': f'Subject with code "{code}" already exists for {educational_level.name}.'
        })
    
    # Get optional fields
    short_name = request.POST.get('short_name', '').strip()
    description = request.POST.get('description', '').strip()
    is_compulsory = request.POST.get('is_compulsory') == 'on' or request.POST.get('is_compulsory') == 'true'
    is_active = request.POST.get('is_active') == 'on' or request.POST.get('is_active') == 'true'
    
    # Validate short name length if provided
    if short_name and len(short_name) > 20:
        return JsonResponse({
            'success': False,
            'message': 'Short name cannot exceed 20 characters.'
        })
    
    try:
        # Create the subject
        subject = Subject.objects.create(
            educational_level=educational_level,
            name=name,
            code=code.upper(),  # Store code in uppercase for consistency
            short_name=short_name,
            description=description,
            is_compulsory=is_compulsory,
            is_active=is_active
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Subject "{name}" created successfully.',
            'subject': {
                'id': subject.id,
                'educational_level_id': subject.educational_level.id,
                'educational_level_name': subject.educational_level.name,
                'name': subject.name,
                'code': subject.code,
                'short_name': subject.short_name,
                'is_compulsory': subject.is_compulsory,
                'is_active': subject.is_active,
                'description': subject.description
            }
        })
        
    except IntegrityError as e:
        if 'unique' in str(e).lower():
            return JsonResponse({
                'success': False,
                'message': f'A subject with code "{code}" already exists for {educational_level.name}.'
            })
        return JsonResponse({
            'success': False,
            'message': f'Database error: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error creating subject: {str(e)}'
        })


def update_subject(request):
    """Update an existing subject"""
    subject_id = request.POST.get('id')
    if not subject_id:
        return JsonResponse({
            'success': False,
            'message': 'Subject ID is required.'
        })
    
    try:
        subject = Subject.objects.get(id=subject_id)
    except Subject.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Subject not found.'
        })
    
    # Get and validate required fields
    educational_level_id = request.POST.get('educational_level')
    name = request.POST.get('name', '').strip()
    code = request.POST.get('code', '').strip()
    
    if not educational_level_id or not name or not code:
        return JsonResponse({
            'success': False,
            'message': 'Educational level, name, and code are required.'
        })
    
    # Validate name and code length
    if len(name) < 2:
        return JsonResponse({
            'success': False,
            'message': 'Subject name must be at least 2 characters long.'
        })
    
    if len(code) > 20:
        return JsonResponse({
            'success': False,
            'message': 'Subject code cannot exceed 20 characters.'
        })
    
    if len(name) > 100:
        return JsonResponse({
            'success': False,
            'message': 'Subject name cannot exceed 100 characters.'
        })
    
    # Validate code format
    if not code.replace('-', '').replace('_', '').isalnum():
        return JsonResponse({
            'success': False,
            'message': 'Subject code can only contain letters, numbers, hyphens, and underscores.'
        })
    
    # Get educational level
    try:
        educational_level = EducationalLevel.objects.get(id=educational_level_id)
    except EducationalLevel.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Selected educational level does not exist.'
        })
    
    # Check for duplicate subject code within the same educational level (excluding current)
    if Subject.objects.filter(
        educational_level=educational_level,
        code__iexact=code
    ).exclude(id=subject.id).exists():
        return JsonResponse({
            'success': False,
            'message': f'Subject with code "{code}" already exists for {educational_level.name}.'
        })
    
    # Get optional fields
    short_name = request.POST.get('short_name', '').strip()
    description = request.POST.get('description', '').strip()
    is_compulsory = request.POST.get('is_compulsory') == 'on' or request.POST.get('is_compulsory') == 'true'
    is_active = request.POST.get('is_active') == 'on' or request.POST.get('is_active') == 'true'
    
    # Validate short name length if provided
    if short_name and len(short_name) > 20:
        return JsonResponse({
            'success': False,
            'message': 'Short name cannot exceed 20 characters.'
        })
    
    try:
        # Update the subject
        subject.educational_level = educational_level
        subject.name = name
        subject.code = code.upper()  # Store code in uppercase for consistency
        subject.short_name = short_name
        subject.description = description
        subject.is_compulsory = is_compulsory
        subject.is_active = is_active
        subject.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Subject "{name}" updated successfully.',
            'subject': {
                'id': subject.id,
                'educational_level_id': subject.educational_level.id,
                'educational_level_name': subject.educational_level.name,
                'name': subject.name,
                'code': subject.code,
                'short_name': subject.short_name,
                'is_compulsory': subject.is_compulsory,
                'is_active': subject.is_active,
                'description': subject.description
            }
        })
        
    except IntegrityError as e:
        if 'unique' in str(e).lower():
            return JsonResponse({
                'success': False,
                'message': f'A subject with code "{code}" already exists for {educational_level.name}.'
            })
        return JsonResponse({
            'success': False,
            'message': f'Database error: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating subject: {str(e)}'
        })


def toggle_subject_status(request):
    """Toggle subject active/inactive status"""
    subject_id = request.POST.get('id')
    if not subject_id:
        return JsonResponse({
            'success': False,
            'message': 'Subject ID is required.'
        })
    
    try:
        subject = Subject.objects.get(id=subject_id)
    except Subject.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Subject not found.'
        })
    
    try:
        # Toggle the status
        subject.is_active = not subject.is_active
        subject.save()
        
        status_text = "activated" if subject.is_active else "deactivated"
        
        return JsonResponse({
            'success': True,
            'message': f'Subject "{subject.name}" {status_text} successfully.',
            'is_active': subject.is_active
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error toggling subject status: {str(e)}'
        })


def toggle_subject_compulsory(request):
    """Toggle subject compulsory/optional status"""
    subject_id = request.POST.get('id')
    if not subject_id:
        return JsonResponse({
            'success': False,
            'message': 'Subject ID is required.'
        })
    
    try:
        subject = Subject.objects.get(id=subject_id)
    except Subject.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Subject not found.'
        })
    
    try:
        # Toggle the compulsory status
        subject.is_compulsory = not subject.is_compulsory
        subject.save()
        
        type_text = "marked as compulsory" if subject.is_compulsory else "marked as optional"
        
        return JsonResponse({
            'success': True,
            'message': f'Subject "{subject.name}" {type_text} successfully.',
            'is_compulsory': subject.is_compulsory
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error toggling subject type: {str(e)}'
        })


def delete_subject(request):
    """Delete a subject"""
    subject_id = request.POST.get('id')
    if not subject_id:
        return JsonResponse({
            'success': False,
            'message': 'Subject ID is required.'
        })
    
    try:
        subject = Subject.objects.get(id=subject_id)
    except Subject.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Subject not found.'
        })
    
    # Check if subject has any associated data (optional - add your own checks)
    # Example: if subject.class_set.exists():
    #     return JsonResponse({
    #         'success': False,
    #         'message': 'Cannot delete subject with associated classes.'
    #     })
    
    subject_name = subject.name
    
    try:
        subject.delete()
        return JsonResponse({
            'success': True,
            'message': f'Subject "{subject_name}" deleted successfully.',
            'id': subject_id
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting subject: {str(e)}'
        })


# Helper function to get subjects list view (optional)


# Legacy view - redirect to list for backward compatibility
@login_required
def subjects(request):
    """Redirect to subjects_list for backward compatibility"""
    return redirect('admin_subjects_list')


@login_required
def class_levels_list(request):
    """Display class levels management page"""
    class_levels = ClassLevel.objects.select_related('educational_level').all().order_by('educational_level', 'name')
    educational_levels = EducationalLevel.objects.filter(is_active=True)
    
    # Count active class levels
    active_class_levels_count = class_levels.filter(is_active=True).count()
    
    context = {
        'class_levels': class_levels,
        'educational_levels': educational_levels,
        'active_class_levels_count': active_class_levels_count,
    }
    
    return render(request, 'admin/academic/class_levels_list.html', context)




@login_required
def class_levels_crud(request):
    """Handle AJAX CRUD operations for class levels"""
    if request.method == 'POST':
        action = request.POST.get('action', '').lower()
        
        try:
            if action == 'create':
                return create_class_level(request)
            elif action == 'update':
                return update_class_level(request)
            elif action == 'toggle_status':
                return toggle_class_level_status(request)
            elif action == 'delete':
                return delete_class_level(request)
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid action specified.'
                })
                
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'POST request required.'
    })


def create_class_level(request):
    """Create a new class level"""
    # Get and validate required fields
    educational_level_id = request.POST.get('educational_level')
    if not educational_level_id:
        return JsonResponse({
            'success': False,
            'message': 'Educational level is required.'
        })
    
    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({
            'success': False,
            'message': 'Class level name is required.'
        })
    
    code = request.POST.get('code', '').strip()
    if not code:
        return JsonResponse({
            'success': False,
            'message': 'Class level code is required.'
        })
    
    order_str = request.POST.get('order', '').strip()
    if not order_str:
        return JsonResponse({
            'success': False,
            'message': 'Order is required.'
        })
    
    try:
        order = int(order_str)
        if order < 1 or order > 100:
            return JsonResponse({
                'success': False,
                'message': 'Order must be between 1 and 100.'
            })
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Order must be a valid number.'
        })
    
    # Validate name and code length
    if len(name) > 50:
        return JsonResponse({
            'success': False,
            'message': 'Class level name cannot exceed 50 characters.'
        })
    
    if len(code) > 20:
        return JsonResponse({
            'success': False,
            'message': 'Class level code cannot exceed 20 characters.'
        })
    
    # Validate code format (alphanumeric)
    if not code.isalnum():
        return JsonResponse({
            'success': False,
            'message': 'Class level code can only contain letters and numbers.'
        })
    
    # Get educational level
    try:
        educational_level = EducationalLevel.objects.get(id=educational_level_id)
    except EducationalLevel.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Selected educational level does not exist.'
        })
    
    # Check for duplicate class level code within the same educational level
    if ClassLevel.objects.filter(
        educational_level=educational_level,
        code__iexact=code
    ).exists():
        return JsonResponse({
            'success': False,
            'message': f'Class level with code "{code}" already exists for {educational_level.name}.'
        })
    
    # Check for duplicate order within the same educational level
    if ClassLevel.objects.filter(
        educational_level=educational_level,
        order=order
    ).exists():
        return JsonResponse({
            'success': False,
            'message': f'Another class level already has order {order} for {educational_level.name}.'
        })
    
    # Get optional fields
    is_active = request.POST.get('is_active') == 'on' or request.POST.get('is_active') == 'true'
    
    try:
        # Create the class level
        class_level = ClassLevel.objects.create(
            educational_level=educational_level,
            name=name,
            code=code.upper(),  # Store code in uppercase for consistency
            order=order,
            is_active=is_active
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Class level "{name}" created successfully.',
            'class_level': {
                'id': class_level.id,
                'educational_level_id': class_level.educational_level.id,
                'educational_level_name': class_level.educational_level.name,
                'name': class_level.name,
                'code': class_level.code,
                'order': class_level.order,
                'is_active': class_level.is_active
            }
        })
        
    except IntegrityError as e:
        if 'unique' in str(e).lower():
            return JsonResponse({
                'success': False,
                'message': f'A class level with code "{code}" already exists for {educational_level.name}.'
            })
        return JsonResponse({
            'success': False,
            'message': f'Database error: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error creating class level: {str(e)}'
        })


def update_class_level(request):
    """Update an existing class level"""
    class_level_id = request.POST.get('id')
    if not class_level_id:
        return JsonResponse({
            'success': False,
            'message': 'Class level ID is required.'
        })
    
    try:
        class_level = ClassLevel.objects.get(id=class_level_id)
    except ClassLevel.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Class level not found.'
        })
    
    # Get and validate required fields
    educational_level_id = request.POST.get('educational_level')
    name = request.POST.get('name', '').strip()
    code = request.POST.get('code', '').strip()
    order_str = request.POST.get('order', '').strip()
    
    if not educational_level_id or not name or not code or not order_str:
        return JsonResponse({
            'success': False,
            'message': 'Educational level, name, code, and order are required.'
        })
    
    try:
        order = int(order_str)
        if order < 1 or order > 100:
            return JsonResponse({
                'success': False,
                'message': 'Order must be between 1 and 100.'
            })
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Order must be a valid number.'
        })
    
    # Validate name and code length
    if len(name) > 50:
        return JsonResponse({
            'success': False,
            'message': 'Class level name cannot exceed 50 characters.'
        })
    
    if len(code) > 20:
        return JsonResponse({
            'success': False,
            'message': 'Class level code cannot exceed 20 characters.'
        })
    
    # Validate code format (alphanumeric)
    if not code.isalnum():
        return JsonResponse({
            'success': False,
            'message': 'Class level code can only contain letters and numbers.'
        })
    
    # Get educational level
    try:
        educational_level = EducationalLevel.objects.get(id=educational_level_id)
    except EducationalLevel.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Selected educational level does not exist.'
        })
    
    # Check for duplicate class level code within the same educational level (excluding current)
    if ClassLevel.objects.filter(
        educational_level=educational_level,
        code__iexact=code
    ).exclude(id=class_level.id).exists():
        return JsonResponse({
            'success': False,
            'message': f'Class level with code "{code}" already exists for {educational_level.name}.'
        })
    
    # Check for duplicate order within the same educational level (excluding current)
    if ClassLevel.objects.filter(
        educational_level=educational_level,
        order=order
    ).exclude(id=class_level.id).exists():
        return JsonResponse({
            'success': False,
            'message': f'Another class level already has order {order} for {educational_level.name}.'
        })
    
    # Get optional fields
    is_active = request.POST.get('is_active') == 'on' or request.POST.get('is_active') == 'true'
    
    try:
        # Update the class level
        class_level.educational_level = educational_level
        class_level.name = name
        class_level.code = code.upper()  # Store code in uppercase for consistency
        class_level.order = order
        class_level.is_active = is_active
        class_level.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Class level "{name}" updated successfully.',
            'class_level': {
                'id': class_level.id,
                'educational_level_id': class_level.educational_level.id,
                'educational_level_name': class_level.educational_level.name,
                'name': class_level.name,
                'code': class_level.code,
                'order': class_level.order,
                'is_active': class_level.is_active
            }
        })
        
    except IntegrityError as e:
        if 'unique' in str(e).lower():
            return JsonResponse({
                'success': False,
                'message': f'A class level with code "{code}" already exists for {educational_level.name}.'
            })
        return JsonResponse({
            'success': False,
            'message': f'Database error: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating class level: {str(e)}'
        })


def toggle_class_level_status(request):
    """Toggle class level active/inactive status"""
    class_level_id = request.POST.get('id')
    if not class_level_id:
        return JsonResponse({
            'success': False,
            'message': 'Class level ID is required.'
        })
    
    try:
        class_level = ClassLevel.objects.get(id=class_level_id)
    except ClassLevel.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Class level not found.'
        })
    
    try:
        # Toggle the status
        class_level.is_active = not class_level.is_active
        class_level.save()
        
        status_text = "activated" if class_level.is_active else "deactivated"
        
        return JsonResponse({
            'success': True,
            'message': f'Class level "{class_level.name}" {status_text} successfully.',
            'is_active': class_level.is_active
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error toggling class level status: {str(e)}'
        })


def delete_class_level(request):
    """Delete a class level"""
    class_level_id = request.POST.get('id')
    if not class_level_id:
        return JsonResponse({
            'success': False,
            'message': 'Class level ID is required.'
        })
    
    try:
        class_level = ClassLevel.objects.get(id=class_level_id)
    except ClassLevel.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Class level not found.'
        })
    
    # Check if class level has any associated data (optional - add your own checks)
    # Example: if class_level.stream_set.exists():
    #     return JsonResponse({
    #         'success': False,
    #         'message': 'Cannot delete class level with associated streams.'
    #     })
    
    class_level_name = class_level.name
    
    try:
        class_level.delete()
        return JsonResponse({
            'success': True,
            'message': f'Class level "{class_level_name}" deleted successfully.',
            'id': class_level_id
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting class level: {str(e)}'
        })


# Helper function to get class levels list view (optional)



# Legacy view - redirect to list for backward compatibility
@login_required
def class_levels(request):
    """Redirect to class_levels_list for backward compatibility"""
    return redirect('admin_class_levels_list')

# Helper function to get stream classes list view
@login_required
def stream_classes_list(request):
    """Display stream classes management page"""
    stream_classes = StreamClass.objects.select_related(
        'class_level',
        'class_level__educational_level'
    ).all()
    
    class_levels = ClassLevel.objects.filter(is_active=True).select_related('educational_level')
    
    # Count active streams
    active_streams_count = stream_classes.filter(is_active=True).count()
    
    # Calculate total students across all streams
    total_students = 0
    for stream in stream_classes:
        total_students += stream.student_count
    
    context = {
        'stream_classes': stream_classes,
        'class_levels': class_levels,
        'active_streams_count': active_streams_count,
        'total_students': total_students,
    }
    
    return render(request, 'admin/academic/stream_classes_list.html', context)




@login_required
def stream_classes_crud(request):
    """Handle AJAX CRUD operations for stream classes"""
    if request.method == 'POST':
        action = request.POST.get('action', '').lower()
        
        try:
            if action == 'create':
                return create_stream_class(request)
            elif action == 'update':
                return update_stream_class(request)
            elif action == 'toggle_status':
                return toggle_stream_class_status(request)
            elif action == 'delete':
                return delete_stream_class(request)
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid action specified.'
                })
                
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'POST request required.'
    })


def create_stream_class(request):
    """Create a new stream class"""
    # Get and validate required fields
    class_level_id = request.POST.get('class_level')
    if not class_level_id:
        return JsonResponse({
            'success': False,
            'message': 'Class level is required.'
        })
    
    stream_letter = request.POST.get('stream_letter', '').strip().upper()
    if not stream_letter:
        return JsonResponse({
            'success': False,
            'message': 'Stream letter is required.'
        })
    
    capacity_str = request.POST.get('capacity', '50').strip()
    
    # Validate stream letter
    if len(stream_letter) != 1 or not stream_letter.isalpha():
        return JsonResponse({
            'success': False,
            'message': 'Stream letter must be a single letter (A-Z).'
        })
    
    # Validate capacity
    try:
        capacity = int(capacity_str)
        if capacity < 10:
            return JsonResponse({
                'success': False,
                'message': 'Capacity must be at least 10 students.'
            })
        if capacity > 200:
            return JsonResponse({
                'success': False,
                'message': 'Capacity cannot exceed 200 students.'
            })
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Capacity must be a valid number.'
        })
    
    # Get class level
    try:
        class_level = ClassLevel.objects.get(id=class_level_id, is_active=True)
    except ClassLevel.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Selected class level does not exist or is inactive.'
        })
    
    # Check for duplicate stream letter within the same class level
    if StreamClass.objects.filter(
        class_level=class_level,
        stream_letter=stream_letter
    ).exists():
        return JsonResponse({
            'success': False,
            'message': f'Stream "{stream_letter}" already exists for {class_level.name}.'
        })
    
    # Get optional fields
    is_active = request.POST.get('is_active') == 'on' or request.POST.get('is_active') == 'true'
    
    try:
        # Create the stream class
        stream = StreamClass.objects.create(
            class_level=class_level,
            stream_letter=stream_letter,
            capacity=capacity,
            is_active=is_active
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Stream class "{stream}" created successfully.',
            'stream': {
                'id': stream.id,
                'class_level_id': stream.class_level.id,
                'class_level_name': stream.class_level.name,
                'educational_level_name': stream.class_level.educational_level.name,
                'stream_letter': stream.stream_letter,
                'capacity': stream.capacity,
                'student_count': stream.student_count,
                'is_active': stream.is_active,
                'full_name': str(stream)
            }
        })
        
    except IntegrityError as e:
        if 'unique' in str(e).lower():
            return JsonResponse({
                'success': False,
                'message': f'A stream with letter "{stream_letter}" already exists for {class_level.name}.'
            })
        return JsonResponse({
            'success': False,
            'message': f'Database error: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error creating stream class: {str(e)}'
        })


def update_stream_class(request):
    """Update an existing stream class"""
    stream_id = request.POST.get('id')
    if not stream_id:
        return JsonResponse({
            'success': False,
            'message': 'Stream class ID is required.'
        })
    
    try:
        stream = StreamClass.objects.get(id=stream_id)
    except StreamClass.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Stream class not found.'
        })
    
    # Get and validate required fields
    class_level_id = request.POST.get('class_level')
    stream_letter = request.POST.get('stream_letter', '').strip().upper()
    capacity_str = request.POST.get('capacity', str(stream.capacity)).strip()
    
    if not class_level_id or not stream_letter:
        return JsonResponse({
            'success': False,
            'message': 'Class level and stream letter are required.'
        })
    
    # Validate stream letter
    if len(stream_letter) != 1 or not stream_letter.isalpha():
        return JsonResponse({
            'success': False,
            'message': 'Stream letter must be a single letter (A-Z).'
        })
    
    # Validate capacity
    try:
        capacity = int(capacity_str)
        if capacity < 10:
            return JsonResponse({
                'success': False,
                'message': 'Capacity must be at least 10 students.'
            })
        if capacity > 200:
            return JsonResponse({
                'success': False,
                'message': 'Capacity cannot exceed 200 students.'
            })
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Capacity must be a valid number.'
        })
    
    # Get class level
    try:
        class_level = ClassLevel.objects.get(id=class_level_id, is_active=True)
    except ClassLevel.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Selected class level does not exist or is inactive.'
        })
    
    # Check for duplicate stream letter within the same class level (excluding current)
    if StreamClass.objects.filter(
        class_level=class_level,
        stream_letter=stream_letter
    ).exclude(id=stream.id).exists():
        return JsonResponse({
            'success': False,
            'message': f'Stream "{stream_letter}" already exists for {class_level.name}.'
        })
    
    # Check if capacity is less than current student count
    current_student_count = stream.student_count
    if capacity < current_student_count:
        return JsonResponse({
            'success': False,
            'message': f'Cannot reduce capacity below current student count ({current_student_count} students).'
        })
    
    # Get optional fields
    is_active = request.POST.get('is_active') == 'on' or request.POST.get('is_active') == 'true'
    
    try:
        # Update the stream class
        stream.class_level = class_level
        stream.stream_letter = stream_letter
        stream.capacity = capacity
        stream.is_active = is_active
        stream.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Stream class "{stream}" updated successfully.',
            'stream': {
                'id': stream.id,
                'class_level_id': stream.class_level.id,
                'class_level_name': stream.class_level.name,
                'educational_level_name': stream.class_level.educational_level.name,
                'stream_letter': stream.stream_letter,
                'capacity': stream.capacity,
                'student_count': stream.student_count,
                'is_active': stream.is_active,
                'full_name': str(stream)
            }
        })
        
    except IntegrityError as e:
        if 'unique' in str(e).lower():
            return JsonResponse({
                'success': False,
                'message': f'A stream with letter "{stream_letter}" already exists for {class_level.name}.'
            })
        return JsonResponse({
            'success': False,
            'message': f'Database error: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating stream class: {str(e)}'
        })


def toggle_stream_class_status(request):
    """Toggle stream class active/inactive status"""
    stream_id = request.POST.get('id')
    if not stream_id:
        return JsonResponse({
            'success': False,
            'message': 'Stream class ID is required.'
        })
    
    try:
        stream = StreamClass.objects.get(id=stream_id)
    except StreamClass.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Stream class not found.'
        })
    
    # Check if stream has active students when trying to deactivate
    if stream.is_active and stream.student_count > 0:
        return JsonResponse({
            'success': False,
            'message': f'Cannot deactivate stream with {stream.student_count} active students. Reassign students first.'
        })
    
    try:
        # Toggle the status
        stream.is_active = not stream.is_active
        stream.save()
        
        status_text = "activated" if stream.is_active else "deactivated"
        
        return JsonResponse({
            'success': True,
            'message': f'Stream class "{stream}" {status_text} successfully.',
            'is_active': stream.is_active,
            'student_count': stream.student_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error toggling stream class status: {str(e)}'
        })


def delete_stream_class(request):
    """Delete a stream class"""
    stream_id = request.POST.get('id')
    if not stream_id:
        return JsonResponse({
            'success': False,
            'message': 'Stream class ID is required.'
        })
    
    try:
        stream = StreamClass.objects.get(id=stream_id)
    except StreamClass.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Stream class not found.'
        })
    
    # Check if stream has any students
    if stream.student_count > 0:
        return JsonResponse({
            'success': False,
            'message': f'Cannot delete stream with {stream.student_count} students. Reassign students first.'
        })
    
    stream_name = str(stream)
    
    try:
        stream.delete()
        return JsonResponse({
            'success': True,
            'message': f'Stream class "{stream_name}" deleted successfully.',
            'id': stream_id
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting stream class: {str(e)}'
        })


@login_required
def stream_students(request, stream_id):
    """
    View to manage students in a specific stream
    """
    # Get the stream
    stream = get_object_or_404(StreamClass, id=stream_id)
    
    # Get all students in this stream
    students = Student.objects.filter(
        stream_class=stream,
    
        is_active=True
    ).select_related('class_level', 'academic_year').order_by('first_name', 'last_name')
    
    # Get available students who can be added to this stream
    # Students who are active but not in this stream, and are in the same class level
    available_students = Student.objects.filter(
    is_active=True,
    class_level=stream.class_level,
    stream_class__isnull=True
).select_related(
    'class_level', 'academic_year'
).order_by('first_name', 'last_name')

    
    # Get count statistics
    total_students_in_stream = students.count()
    available_students_count = available_students.count()
    capacity_percentage = (total_students_in_stream / stream.capacity * 100) if stream.capacity > 0 else 0
 
    context = {
        'stream': stream,
        'students': students,
        'available_students': available_students,
        'total_students_in_stream': total_students_in_stream,
        'available_students_count': available_students_count,
        'capacity_percentage': capacity_percentage,
        'page_title': f'Students in {stream.class_level.name}{stream.stream_letter}',
    }
    
    return render(request, 'admin/students/stream_students.html', context)


@login_required
def remove_student_from_stream(request, stream_id):
    """
    AJAX view to remove a student from a stream
    """
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            # Try to parse as JSON first
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                student_id = data.get('student_id')
            else:
                # Fall back to form data
                student_id = request.POST.get('student_id')
            
            if not student_id:
                return JsonResponse({
                    'success': False,
                    'message': 'Student ID is required.'
                })
            
            # Get student and stream
            student = get_object_or_404(Student, id=student_id, is_active=True)
            stream = get_object_or_404(StreamClass, id=stream_id)
            
            # Verify student is in this stream
            if student.stream_class != stream:
                return JsonResponse({
                    'success': False,
                    'message': 'Student is not in this stream.'
                })
            
            # Remove student from stream
            student.stream_class = None
            student.save()
            
            # Update counts
            total_students_in_stream = Student.objects.filter(stream_class=stream, is_active=True).count()
            capacity_percentage = (total_students_in_stream / stream.capacity * 100) if stream.capacity > 0 else 0
            
            return JsonResponse({
                'success': True,
                'message': f'{student.full_name} has been removed from the stream.',
                'total_students': total_students_in_stream,
                'capacity_percentage': capacity_percentage,
                'student_id': student_id
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid request data.'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error removing student: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    })



@login_required
def add_student_to_stream(request, stream_id):
    """
    AJAX view to add students to a stream
    """
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            # Get student IDs from form data
            student_ids = request.POST.getlist('student_ids[]')
            
            if not student_ids:
                return JsonResponse({
                    'success': False,
                    'message': 'No students selected.'
                })
            
            stream = get_object_or_404(StreamClass, id=stream_id)
            added_count = 0
            failed_students = []
            
            for student_id in student_ids:
                try:
                    student = Student.objects.get(id=student_id, is_active=True)
                    
                    # Check if student is already in a stream
                    if student.stream_class:
                        failed_students.append(f"{student.full_name()} (Already in a stream)")
                        continue
                    
                    # Check capacity
                    current_count = Student.objects.filter(stream_class=stream, is_active=True).count()
                    if current_count >= stream.capacity:
                        failed_students.append(f"{student.full_name()} (Stream at capacity)")
                        continue
                    
                    # Add student to stream
                    student.stream_class = stream
                    student.save()
                    added_count += 1
                    
                except Student.DoesNotExist:
                    failed_students.append(f"Student ID {student_id} (Not found)")
                    continue
            
            message = f"Successfully added {added_count} student(s) to the stream."
            if failed_students:
                message += f" Failed to add {len(failed_students)} student(s)."
            
            return JsonResponse({
                'success': True,
                'message': message,
                'added_count': added_count,
                'failed_count': len(failed_students)
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error adding students: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    })


@login_required
def bulk_remove_students_from_stream(request, stream_id):
    """
    AJAX view to bulk remove multiple students from a stream
    """
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            # Get student IDs from form data
            student_ids = request.POST.getlist('student_ids[]')
            
            if not student_ids:
                return JsonResponse({
                    'success': False,
                    'message': 'No students selected.'
                })
            
            stream = get_object_or_404(StreamClass, id=stream_id)
            removed_count = 0
            failed_students = []
            
            # Prepare response data
            removed_student_names = []
            
            for student_id in student_ids:
                try:
                    student = Student.objects.get(id=student_id, is_active=True)
                    
                    # Verify student is in this stream
                    if student.stream_class != stream:
                        failed_students.append(f"{student.full_name} (Not in this stream)")
                        continue
                    
                    # Remove student from stream
                    student.stream_class = None
                    student.save()
                    
                    removed_count += 1
                    removed_student_names.append(student.full_name)
                    
                except Student.DoesNotExist:
                    failed_students.append(f"Student ID {student_id} (Not found)")
                    continue
                except Exception as e:
                    failed_students.append(f"{student_id} (Error: {str(e)})")
                    continue
            
            # Update counts after all removals
            total_students_in_stream = Student.objects.filter(stream_class=stream, is_active=True).count()
            capacity_percentage = (total_students_in_stream / stream.capacity * 100) if stream.capacity > 0 else 0
            
            # Prepare success message
            if removed_count > 0:
                if removed_count <= 3:
                    # Show individual names for small removals
                    student_names_str = ', '.join(removed_student_names)
                    message = f"Successfully removed {student_names_str} from the stream."
                else:
                    # Generic message for larger removals
                    message = f"Successfully removed {removed_count} students from the stream."
                
                if failed_students:
                    message += f" Failed to remove {len(failed_students)} student(s)."
            else:
                message = "No students were removed from the stream."
            
            return JsonResponse({
                'success': True,
                'message': message,
                'removed_count': removed_count,
                'failed_count': len(failed_students),
                'total_students': total_students_in_stream,
                'capacity_percentage': capacity_percentage
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error removing students: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    })

# views.py - Simple version
@login_required
@require_POST
def bulk_toggle_student_status(request):
    """Simple bulk status toggle"""
    try:
        # Get parameters
        student_ids = json.loads(request.POST.get('student_ids', '[]'))
        is_active = request.POST.get('is_active', 'false').lower() == 'true'
        
        if not student_ids:
            return JsonResponse({
                'success': False,
                'message': 'No students selected'
            })
        
        # Update students
        updated = Student.objects.filter(id__in=student_ids).update(
            is_active=is_active,
            status='active' if is_active else 'inactive'
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Updated {updated} student(s)',
            'updated': updated
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        })


# Legacy view - redirect to list for backward compatibility
@login_required
def stream_classes(request):
    """Redirect to stream_classes_list for backward compatibility"""
    return redirect('admin_stream_classes_list')

# ============================================================================
# STUDENT MANAGEMENT VIEWS
# ============================================================================
@login_required
def get_streams_by_class(request):
    """Get streams by class for dropdowns (AJAX)"""
    class_id = request.GET.get('class_id')
    
    if class_id:
        try:
            streams = StreamClass.objects.filter(
                class_level_id=class_id, 
                is_active=True
            ).select_related('class_level').order_by('class_level__name', 'stream_letter')
            
            stream_list = []
            for stream in streams:
                # Combine class level name with stream letter as shown in __str__ method
                stream_name = f"{stream.class_level.name}{stream.stream_letter}"
                stream_list.append({
                    'id': stream.id, 
                    'text': stream_name,
                    'stream_letter': stream.stream_letter,
                    'class_level_name': stream.class_level.name
                })
            
            return JsonResponse({
                'success': True,
                'streams': stream_list
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'error': 'No class ID provided'
    })
    
@login_required
def students_list(request):
    """Display list of students with advanced filtering"""
    # Get filter parameters
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    class_filter = request.GET.get('class_level', '')
    
    # Start with all students
    students = Student.objects.all().select_related(
        'class_level', 'stream_class', 'previous_school'
    ).prefetch_related('optional_subjects', 'parents')
    
    # Apply filters
    if search_query:
        students = students.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(middle_name__icontains=search_query) |
            Q(registration_number__icontains=search_query) |
            Q(examination_number__icontains=search_query) |
            Q(address__icontains=search_query)
        )
    
    if status_filter:
        students = students.filter(status=status_filter)
    
    if class_filter:
        students = students.filter(class_level_id=class_filter)
    
    # Calculate statistics
    total_students = Student.objects.count()
    active_students = Student.objects.filter(is_active=True).count()
    inactive_students = Student.objects.filter(is_active=False).count()
    male_students = Student.objects.filter(gender='male').count()
    female_students = Student.objects.filter(gender='female').count()
    
    # Get all education levels
    education_levels = EducationalLevel.objects.filter(is_active=True)
    
    # Get all class levels
    class_levels = ClassLevel.objects.filter(is_active=True).select_related('educational_level')
    
    # Get unique admission years for filter
    admission_years = AcademicYear.objects.all()
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(students, 25)  # Show 25 students per page
    
    try:
        students_page = paginator.page(page)
    except PageNotAnInteger:
        students_page = paginator.page(1)
    except EmptyPage:
        students_page = paginator.page(paginator.num_pages)
    
    context = {
        'students': students,
        'total_students': total_students,
        'active_students': active_students,
        'inactive_students': inactive_students,
        'male_students': male_students,
        'female_students': female_students,
        'education_levels': education_levels,
        'class_levels': class_levels,
        'admission_years': admission_years,
        'status_choices': STATUS_CHOICES,
        'gender_choices': GENDER_CHOICES,
        'search_query': search_query,
        'status_filter': status_filter,
        'class_filter': class_filter,
    }
    
    return render(request, 'admin/students/student_list.html', context)

@login_required
def get_class_levels_by_education_level(request):
    """AJAX endpoint to get class levels by education level"""
    education_level_id = request.GET.get('education_level_id')
    
    if not education_level_id:
        return JsonResponse({'success': False, 'message': 'Education level ID required'})
    
    try:
        class_levels = ClassLevel.objects.filter(
            educational_level_id=education_level_id,
            is_active=True
        ).order_by('order')
        
        class_list = []
        for cls in class_levels:
            class_list.append({
                'id': cls.id,
                'text': f"{cls.name} ({cls.code})",
                'name': cls.name,
                'code': cls.code
            })
        
        return JsonResponse({
            'success': True,
            'class_levels': class_list
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def toggle_student_status(request):
    """AJAX endpoint to toggle student active status"""
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        
        try:
            student = Student.objects.get(id=student_id)
            student.is_active = not student.is_active
            student.save()
            
            action = 'activated' if student.is_active else 'deactivated'
            
            return JsonResponse({
                'success': True,
                'message': f'Student {student.full_name} {action} successfully.',
                'is_active': student.is_active
            })
            
        except Student.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Student not found.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})

@login_required
def delete_student(request):
    """AJAX endpoint to delete a student"""
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        
        try:
            student = Student.objects.get(id=student_id)
            student_name = student.full_name
            student.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Student {student_name} deleted successfully.'
            })
            
        except Student.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Student not found.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})

@login_required
def students_add(request):
    """
    Handle student creation with AJAX validation and form submission
    """
    # GET request - show empty form
    if request.method == 'GET':
        return handle_get_request(request)
    
    # POST request - process form submission
    elif request.method == 'POST':
        return handle_post_request(request)

def handle_get_request(request):
    """Handle GET request - prepare form and context"""
    form = StudentForm()
    
    # Prepare context for template
    context = {
        'form': form,
        'class_levels': ClassLevel.objects.filter(is_active=True).order_by('order'),
        'academic_years': AcademicYear.objects.all(),
        'stream_classes': StreamClass.objects.filter(is_active=True).order_by('class_level', 'stream_letter'),
        'previous_schools': PreviousSchool.objects.all().order_by('name'),
        'subjects': Subject.objects.filter(is_active=True).order_by('name'),
        'status_choices': STATUS_CHOICES,
        'gender_choices': GENDER_CHOICES,
        'page_title': 'Add New Student',
        'is_ajax_validation': False,
    }
    
    return render(request, 'admin/students/student_add.html', context)

def handle_post_request(request):
    """Handle POST request - validate and save student"""
    # Check if this is AJAX validation only
    is_ajax_validation = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest' and 
        request.POST.get('validate_only') == 'true'
    )
    
    # Prepare form with data
    form = StudentForm(request.POST, request.FILES)
    
    # Handle AJAX validation
    if is_ajax_validation:
        return handle_ajax_validation(form)
    
    # Handle regular form submission
    return handle_form_submission(request, form)

def handle_ajax_validation(form):
    """Handle AJAX form validation"""
    if form.is_valid():
        return JsonResponse({
            'success': True,
            'message': 'Form is valid',
            'errors': {}
        })
    else:
        # Format errors for frontend
        errors = {}
        for field, error_list in form.errors.items():
            if field == '__all__':
                errors['non_field_errors'] = error_list
            else:
                errors[field] = error_list[0] if error_list else ''
        
        return JsonResponse({
            'success': False,
            'message': 'Please correct the errors below',
            'errors': errors
        }, status=400)

@transaction.atomic
def handle_form_submission(request, form):
    """Handle regular form submission and save student"""
    if form.is_valid():
        try:
            # Get optional subjects from POST data
            optional_subjects_ids = request.POST.getlist('optional_subjects', [])
            
            # Save student instance
            student = form.save(commit=False)
            
            # Set admission year if not provided
            if not student.admission_year:
                student.admission_year = datetime.now().year
            
            # Generate serial number if needed
            if not student.serial_number:
                last_student = Student.objects.filter(
                    admission_year=student.admission_year
                ).order_by('-serial_number').first()
                student.serial_number = 1 if not last_student else last_student.serial_number + 1
            
            # Save the student (this will also generate registration number)
            student.save()
            
            # Handle optional subjects
            if optional_subjects_ids:
                subjects = Subject.objects.filter(id__in=optional_subjects_ids)
                student.optional_subjects.set(subjects)
            
            # Get save type to determine next action
            save_type = request.POST.get('save_type', 'save_list')
            
            # Handle AJAX response
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Student {student.full_name} added successfully!',
                    'student_id': student.id,
                    'student_name': student.full_name,
                    'registration_number': student.registration_number,
                    'save_type': save_type,
                    'redirect_url': get_redirect_url(save_type, student.id)
                })
            
            # Handle regular HTTP response
            return handle_success_redirect(save_type, student.id)
            
        except Exception as e:
            # Log the error here if you have logging setup
            print(f"Error saving student: {str(e)}")
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': f'Error saving student: {str(e)}',
                    'errors': {'__all__': 'An unexpected error occurred'}
                })
            else:
                # Re-render form with error
                return render_form_with_error(request, form, str(e))
    
    else:
        # Form is invalid
        return handle_invalid_form(request, form)

def get_redirect_url(save_type, student_id):
    """Get redirect URL based on save type"""
    if save_type == 'save_add':
        return reverse('admin_students_add')
    elif save_type == 'save_parent':
        return reverse('admin_add_parent_to_student', kwargs={'student_id': student_id})
    else:  # save_list or default
        return reverse('admin_students_list')

def handle_success_redirect(save_type, student_id):
    """Handle redirect after successful form submission"""
    if save_type == 'save_add':
        return redirect('admin_students_add')
    elif save_type == 'save_parent':
        return redirect('admin_add_parent_to_student', student_id=student_id)
    else:  # save_list or default
        return redirect('admin_students_list')

def handle_invalid_form(request, form):
    """Handle invalid form submission"""
    # Format errors for response
    errors = {}
    for field, error_list in form.errors.items():
        if field == '__all__':
            errors['non_field_errors'] = error_list
        else:
            errors[field] = error_list[0] if error_list else ''
    
    # AJAX response
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': False,
            'message': 'Please correct the errors below',
            'errors': errors
        }, status=400)
    
    # Regular HTTP response - re-render form
    context = {
        'form': form,
        'class_levels': ClassLevel.objects.filter(is_active=True).order_by('order'),
        'stream_classes': StreamClass.objects.filter(is_active=True).order_by('class_level', 'stream_letter'),
        'previous_schools': PreviousSchool.objects.all().order_by('name'),
        'subjects': Subject.objects.filter(is_active=True).order_by('name'),
        'status_choices': STATUS_CHOICES,
        'gender_choices': GENDER_CHOICES,
        'page_title': 'Add New Student',
        'form_errors': errors,
    }
    
    return render(request, 'admin/students/student_add.html', context)

def render_form_with_error(request, form, error_message):
    """Render form with error message"""
    context = {
        'form': form,
        'class_levels': ClassLevel.objects.filter(is_active=True).order_by('order'),
        'stream_classes': StreamClass.objects.filter(is_active=True).order_by('class_level', 'stream_letter'),
        'previous_schools': PreviousSchool.objects.all().order_by('name'),
        'subjects': Subject.objects.filter(is_active=True).order_by('name'),
        'status_choices': STATUS_CHOICES,
        'gender_choices': GENDER_CHOICES,
        'page_title': 'Add New Student',
        'error_message': error_message,
    }
    
    return render(request, 'admin/students/student_add.html', context)



@login_required
def add_parent_to_student(request, student_id):
    """
    View for adding a new parent/guardian to a student
    URL: /admin/students/<student_id>/parent/add/
    """
    student = get_object_or_404(Student, pk=student_id)
    
    # Check if user has access to this student
    if not request.user.has_perm('students.view_student', student):
        messages.error(request, 'You do not have permission to view this student.')
        return redirect('admin_students_list')
    
    if request.method == 'POST':
        form = ParentForm(request.POST)
        
        if form.is_valid():
            try:
                # Save the parent
                parent = form.save(commit=False)
                parent.save()
                
                # Link parent to student
                parent.students.add(student)
                
                # If this parent is fee responsible, unset others
                if parent.is_fee_responsible:
                    student.parents.filter(is_fee_responsible=True).exclude(pk=parent.pk).update(is_fee_responsible=False)
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': 'Parent added successfully!',
                        'parent_id': parent.id,
                        'parent_name': parent.full_name,
                        'relationship': parent.relationship
                    })
                
                # Handle regular form submission
                action = request.POST.get('action_type', 'save_only')
                
                messages.success(request, f'Parent "{parent.full_name}" added successfully!')
                
                if action == 'save_and_view':
                    return redirect('admin_student_detail', student_id=student.id)
                elif action == 'save_and_add_another':
                    return redirect('admin_add_parent_to_student', student_id=student.id)
                elif action == 'save_and_edit':
                    return redirect('admin_edit_parent', student_id=student.id, parent_id=parent.id)
                else:  # save_only
                    return redirect('admin_add_parent_to_student', student_id=student.id)
                    
            except Exception as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': f'Error adding parent: {str(e)}'
                    }, status=400)
                else:
                    messages.error(request, f'Error adding parent: {str(e)}')
        else:
            # Form has errors
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Please correct the errors below',
                    'errors': form.errors
                }, status=400)
            else:
                # For non-AJAX, we'll show errors in the template
                pass
    else:
        # GET request - initialize form
        form = ParentForm()
    
    # Prepare context
    context = {
        'student': student,
        'form': form,
        'parent': None,  # No parent for add view
        'RELATIONSHIP_CHOICES': RELATIONSHIP_CHOICES,
        'page_title': f'Add Parent - {student.full_name}',
    }
    
    return render(request, 'admin/students/parent_add.html', context)


@login_required
def edit_parent(request, student_id, parent_id):
    """
    View for editing an existing parent/guardian
    URL: /admin/students/<student_id>/parent/<parent_id>/edit/
    """
    student = get_object_or_404(Student, pk=student_id)
    parent = get_object_or_404(Parent, pk=parent_id, students=student)
    
    # Check if user has access
    if not request.user.has_perm('students.view_student', student):
        messages.error(request, 'You do not have permission to view this student.')
        return redirect('admin_students_list')
    
    if request.method == 'POST':
        form = ParentForm(request.POST, instance=parent)
        
        if form.is_valid():
            try:
                # Save the parent
                parent = form.save()
                
                # If this parent is fee responsible, unset others
                if parent.is_fee_responsible:
                    student.parents.filter(is_fee_responsible=True).exclude(pk=parent.pk).update(is_fee_responsible=False)
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': 'Parent updated successfully!',
                        'parent_id': parent.id,
                        'parent_name': parent.full_name,
                        'relationship': parent.relationship
                    })
                
                # Handle regular form submission
                action = request.POST.get('action_type', 'save_only')
                
                messages.success(request, f'Parent "{parent.full_name}" updated successfully!')
                
                if action == 'save_and_view':
                    return redirect('admin_student_detail', student_id=student.id)
                elif action == 'save_and_add_another':
                    return redirect('admin_add_parent_to_student', student_id=student.id)
                else:  # save_only or save_and_edit
                    return redirect('admin_edit_parent', student_id=student.id, parent_id=parent.id)
                    
            except Exception as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': f'Error updating parent: {str(e)}'
                    }, status=400)
                else:
                    messages.error(request, f'Error updating parent: {str(e)}')
        else:
            # Form has errors
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Please correct the errors below',
                    'errors': form.errors
                }, status=400)
    else:
        # GET request - initialize form with parent data
        form = ParentForm(instance=parent)
    
    # Prepare context
    context = {
        'student': student,
        'parent': parent,
        'form': form,
        'RELATIONSHIP_CHOICES': RELATIONSHIP_CHOICES,
        'page_title': f'Edit Parent - {parent.full_name}',
    }
    
    return render(request, 'admin/students/parent_add.html', context)


@login_required
def delete_parent(request, student_id, parent_id):
    """
    View for deleting a parent/guardian
    URL: /admin/students/<student_id>/parent/<parent_id>/delete/
    """
    if request.method == 'POST':
        student = get_object_or_404(Student, pk=student_id)
        parent = get_object_or_404(Parent, pk=parent_id, students=student)
        
        try:
            parent_name = parent.full_name
            
            # Remove the relationship
            parent.students.remove(student)
            
            # If this was the only student for this parent, delete the parent
            if parent.students.count() == 0:
                parent.delete()
                message = f'Parent "{parent_name}" deleted successfully!'
            else:
                message = f'Parent "{parent_name}" unlinked from student successfully!'
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': message
                })
            
            messages.success(request, message)
            return redirect('admin_student_detail', student_id=student.id)
            
        except Exception as e:
            error_message = f'Error deleting parent: {str(e)}'
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': error_message
                }, status=400)
            
            messages.error(request, error_message)
            return redirect('admin_student_detail', student_id=student.id)
    
    # GET request - redirect to student detail
    return redirect('admin_student_detail', student_id=student_id)


# AJAX-specific views for better separation

@login_required
def save_parent(request, student_id):
    """
    AJAX endpoint for saving a new parent
    URL: /admin/students/<student_id>/parent/save/
    """
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        student = get_object_or_404(Student, pk=student_id)
        form = ParentForm(request.POST)
        
        if form.is_valid():
            try:
                # Save the parent
                parent = form.save(commit=False)
                parent.save()
                
                # Link parent to student
                parent.students.add(student)
                
                # If this parent is fee responsible, unset others
                if parent.is_fee_responsible:
                    student.parents.filter(is_fee_responsible=True).exclude(pk=parent.pk).update(is_fee_responsible=False)
                
                return JsonResponse({
                    'success': True,
                    'message': 'Parent added successfully!',
                    'parent_id': parent.id,
                    'parent_name': parent.full_name,
                    'relationship': parent.relationship,
                    'html': render_parent_card(parent, student)  # Optional: return HTML for dynamic update
                })
                
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'Error adding parent: {str(e)}'
                })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Please correct the errors below',
                'errors': form.errors
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request'
    })


@login_required
def update_parent(request, student_id, parent_id):
    """
    AJAX endpoint for updating an existing parent
    URL: /admin/students/<student_id>/parent/<parent_id>/update/
    """
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        student = get_object_or_404(Student, pk=student_id)
        parent = get_object_or_404(Parent, pk=parent_id, students=student)
        form = ParentForm(request.POST, instance=parent)
        
        if form.is_valid():
            try:
                # Save the parent
                parent = form.save()
                
                # If this parent is fee responsible, unset others
                if parent.is_fee_responsible:
                    student.parents.filter(is_fee_responsible=True).exclude(pk=parent.pk).update(is_fee_responsible=False)
                
                return JsonResponse({
                    'success': True,
                    'message': 'Parent updated successfully!',
                    'parent_id': parent.id,
                    'parent_name': parent.full_name,
                    'relationship': parent.relationship,
                    'html': render_parent_card(parent, student)  # Optional: return HTML for dynamic update
                })
                
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'Error updating parent: {str(e)}'
                }, status=400)
        else:
            return JsonResponse({
                'success': False,
                'message': 'Please correct the errors below',
                'errors': form.errors
            }, status=400)
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request'
    }, status=400)


def render_parent_card(parent, student):
    """
    Helper function to render parent card HTML
    """
    from django.template.loader import render_to_string
    
    return render_to_string('admin/students/parent_card.html', {
        'parent': parent,
        'student': student
    })
       
# students/views.py
@login_required
def update_parent_fee_responsibility(request, student_id, parent_id):
    """
    AJAX endpoint for updating fee responsibility
    URL: /admin/students/<student_id>/parent/<parent_id>/update-fee-responsibility/
    """
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        student = get_object_or_404(Student, pk=student_id)
        parent = get_object_or_404(Parent, pk=parent_id, students=student)
        
        try:
            is_fee_responsible = request.POST.get('is_fee_responsible') == 'true'
            
            # Update the parent
            parent.is_fee_responsible = is_fee_responsible
            parent.save()
            
            # If this parent is being made fee responsible, unset others
            if is_fee_responsible:
                student.parents.filter(is_fee_responsible=True).exclude(pk=parent.pk).update(is_fee_responsible=False)
            
            return JsonResponse({
                'success': True,
                'message': 'Fee responsibility updated successfully!',
                'parent_id': parent.id,
                'is_fee_responsible': parent.is_fee_responsible,
                'html': render_parent_card(parent, student)
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error updating fee responsibility: {str(e)}'
            }, status=400)
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request'
    }, status=400)
    
    
@login_required
def students_by_class(request):
    """
    Enhanced view for browsing students by class with advanced filtering
    """
    # Initialize form with GET data
    form = StudentFilterForm(request.GET or None)
    
    # Get all active class levels with aggregated data using optimized queries
    class_levels = ClassLevel.objects.filter(
        is_active=True
    ).select_related('educational_level').annotate(
        student_count=Count(
            'students',
            filter=Q(students__is_active=True),
            distinct=True
        ),
        stream_count=Count(
            'streams',
            filter=Q(streams__is_active=True),
            distinct=True
        ),
        male_count=Count(
            'students',
            filter=Q(students__is_active=True, students__gender='male'),
            distinct=True
        ),
        female_count=Count(
            'students',
            filter=Q(students__is_active=True, students__gender='female'),
            distinct=True
        )
    ).order_by('educational_level__name', 'order')  # Changed from 'educational_level__order' to 'educational_level__name'
    
    # Initialize queryset with optimized prefetching
    students = Student.objects.filter(is_active=True).select_related(
        'class_level',
        'stream_class',
        'class_level__educational_level'
    ).prefetch_related(
        'parents'
    ).order_by('class_level__order', 'first_name')
    
    # Apply filters from form
    if form.is_valid():
        # Class filter
        class_level = form.cleaned_data.get('class_level')
        if class_level:
            students = students.filter(class_level=class_level)
        
        # Stream filter
        stream = form.cleaned_data.get('stream')
        if stream:
            students = students.filter(stream_class=stream)
        
        # Status filter
        status = form.cleaned_data.get('status')
        if status:
            students = students.filter(status=status)
        
        # Gender filter
        gender = form.cleaned_data.get('gender')
        if gender:
            students = students.filter(gender=gender)
        
        # Search filter
        search_query = form.cleaned_data.get('search')
        if search_query:
            # Create a search vector for better performance
            students = students.annotate(
                full_name_search=Concat(
                    'first_name', Value(' '), 'middle_name', Value(' '), 'last_name',
                    output_field=CharField()
                )
            ).filter(
                Q(full_name_search__icontains=search_query) |
                Q(registration_number__icontains=search_query) |
                Q(examination_number__icontains=search_query) |
                Q(parents__full_name__icontains=search_query) |
                Q(parents__first_phone_number__icontains=search_query)
            ).distinct()
        
        # Date range filter
        date_from = form.cleaned_data.get('date_from')
        if date_from:
            students = students.filter(created_at__date__gte=date_from)
        
        date_to = form.cleaned_data.get('date_to')
        if date_to:
            students = students.filter(created_at__date__lte=date_to)
    
    # Get streams for selected class
    streams = []
    selected_class = form.cleaned_data.get('class_level') if form.is_valid() else None
    if selected_class:
        streams = StreamClass.objects.filter(
            class_level=selected_class,
            is_active=True
        ).order_by('stream_letter')
    
    # Get statistics - optimized with single query where possible
    stats_query = Student.objects.filter(is_active=True)
    
    # Apply same filters to statistics
    if form.is_valid():
        if selected_class:
            stats_query = stats_query.filter(class_level=selected_class)
        
        status = form.cleaned_data.get('status')
        if status:
            stats_query = stats_query.filter(status=status)
        
        gender = form.cleaned_data.get('gender')
        if gender:
            stats_query = stats_query.filter(gender=gender)
    
    # Get statistics counts
    total_students = stats_query.count()
    active_students = stats_query.filter(status='active').count()
    male_students = stats_query.filter(gender='male').count()
    female_students = stats_query.filter(gender='female').count()
    
    # Count classes with students (optimized)
    if form.is_valid() and selected_class:
        classes_with_students = 1
    else:
        classes_with_students = ClassLevel.objects.filter(
            is_active=True,
            students__is_active=True
        ).distinct().count()
    
    # Pagination
    page_size = int(request.GET.get('page_size', 25))
    paginator = Paginator(students, page_size)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get selected class and stream objects
    selected_class_obj = selected_class
    selected_stream_obj = form.cleaned_data.get('stream') if form.is_valid() else None
    
    # Prepare context
    context = {
        'form': form,
        'class_levels': class_levels,
        'students': page_obj,
        'selected_class': selected_class.id if selected_class else '',
        'selected_class_obj': selected_class_obj,
        'selected_stream': selected_stream_obj.id if selected_stream_obj else '',
        'selected_status': form.cleaned_data.get('status', '') if form.is_valid() else '',
        'selected_gender': form.cleaned_data.get('gender', '') if form.is_valid() else '',
        'search_query': form.cleaned_data.get('search', '') if form.is_valid() else '',
        'date_from': form.cleaned_data.get('date_from', '') if form.is_valid() else '',
        'date_to': form.cleaned_data.get('date_to', '') if form.is_valid() else '',
        'page_size': str(page_size),
        'streams': streams,
        
        # Statistics
        'total_students': total_students,
        'active_students': active_students,
        'male_students': male_students,
        'female_students': female_students,
        'classes_with_students': classes_with_students,
        
        # Choices for filters
        'status_choices': STATUS_CHOICES,
        'gender_choices': GENDER_CHOICES,
        
        # Page title
        'page_title': 'Students by Class',
    }
    
    return render(request, 'admin/students/students_by_class.html', context)


# Additional helper functions for bulk operations
@login_required
def get_students_export(request):
    """
    Get filtered students for export
    """
    if request.method == 'GET':
        # Reuse the filtering logic from students_by_class
        form = StudentFilterForm(request.GET or None)
        
        if form.is_valid():
            students = Student.objects.filter(is_active=True).select_related(
                'class_level', 'stream_class'
            ).prefetch_related('parents')
            
            # Apply filters
            class_level = form.cleaned_data.get('class_level')
            if class_level:
                students = students.filter(class_level=class_level)
            
            stream = form.cleaned_data.get('stream')
            if stream:
                students = students.filter(stream_class=stream)
            
            status = form.cleaned_data.get('status')
            if status:
                students = students.filter(status=status)
            
            gender = form.cleaned_data.get('gender')
            if gender:
                students = students.filter(gender=gender)
            
            search_query = form.cleaned_data.get('search')
            if search_query:
                students = students.annotate(
                    full_name_search=Concat(
                        'first_name', Value(' '), 'middle_name', Value(' '), 'last_name',
                        output_field=CharField()
                    )
                ).filter(
                    Q(full_name_search__icontains=search_query) |
                    Q(registration_number__icontains=search_query)
                )
            
            return JsonResponse({
                'success': True,
                'count': students.count(),
                'filters': form.cleaned_data
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


@login_required
def get_class_statistics(request):
    """
    Get real-time statistics for a class
    """
    class_id = request.GET.get('class_id')
    
    if class_id:
        try:
            stats = Student.objects.filter(
                class_level_id=class_id,
                is_active=True
            ).aggregate(
                total=Count('id'),
                active=Count('id', filter=Q(status='active')),
                male=Count('id', filter=Q(gender='male')),
                female=Count('id', filter=Q(gender='female')),
                suspended=Count('id', filter=Q(status='suspended')),
                withdrawn=Count('id', filter=Q(status='withdrawn')),
            )
            
            return JsonResponse({
                'success': True,
                'stats': stats
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False, 'message': 'Class ID required'})

@login_required
def export_students(request):
    """
    Export students to Excel/CSV
    """
    if request.method == 'POST':
        student_ids = request.POST.getlist('student_ids[]')
        export_format = request.POST.get('format', 'excel')
        
        # Get students based on selection
        if student_ids:
            students = Student.objects.filter(id__in=student_ids)
        else:
            # Export all based on current filters (you can pass filter params)
            students = Student.objects.filter(is_active=True)
        
        # Prepare data for export
        data = []
        for student in students.select_related('class_level', 'stream_class'):
            parent = student.parents.first()
            data.append({
                'Registration Number': student.registration_number or '',
                'Full Name': student.full_name,
                'First Name': student.first_name,
                'Middle Name': student.middle_name or '',
                'Last Name': student.last_name,
                'Date of Birth': student.date_of_birth or '',
                'Age': student.age or '',
                'Gender': student.get_gender_display(),
                'Class': student.class_level.name if student.class_level else '',
                'Stream': student.stream_class.name if student.stream_class else '',
                'Status': student.get_status_display(),
                'Admission Year': student.admission_year or '',
                'Address': student.address or '',
                'Parent Name': parent.full_name if parent else '',
                'Parent Relationship': parent.relationship if parent else '',
                'Parent Phone': parent.first_phone_number if parent else '',
                'Parent Email': parent.email if parent else '',
                'Examination Number': student.examination_number or '',
                'Created Date': student.created_at.strftime('%Y-%m-%d'),
            })
        
        # Generate Excel file
        import pandas as pd
        from io import BytesIO
        
        df = pd.DataFrame(data)
        
        if export_format == 'excel':
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Students', index=False)
            output.seek(0)
            
            response = HttpResponse(
                output.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename=students_export.xlsx'
            return response
        
        elif export_format == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename=students_export.csv'
            df.to_csv(response, index=False)
            return response
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required
def bulk_update_student_status(request):
    """
    Bulk update student status
    """
    if request.method == 'POST':
        student_ids = request.POST.getlist('student_ids[]')
        new_status = request.POST.get('status')
        
        if not student_ids or not new_status:
            return JsonResponse({
                'success': False,
                'message': 'Missing parameters'
            })
        
        try:
            # Update student status
            updated_count = Student.objects.filter(
                id__in=student_ids,
                is_active=True
            ).update(status=new_status, updated_at=timezone.now())
            
            return JsonResponse({
                'success': True,
                'message': f'Updated status for {updated_count} student(s)',
                'updated_count': updated_count
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error updating status: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required
def bulk_move_students(request):
    """
    Bulk move students to another class
    """
    if request.method == 'POST':
        student_ids = request.POST.getlist('student_ids[]')
        class_id = request.POST.get('class_id')
        keep_stream = request.POST.get('keep_stream') == 'true'
        
        if not student_ids or not class_id:
            return JsonResponse({
                'success': False,
                'message': 'Missing parameters'
            })
        
        try:
            # Get new class
            new_class = get_object_or_404(ClassLevel, id=class_id, is_active=True)
            
            # Update students
            updated_count = 0
            students = Student.objects.filter(id__in=student_ids, is_active=True)
            
            for student in students:
                student.class_level = new_class
                
                # Clear stream if not keeping it
                if not keep_stream:
                    student.stream_class = None
                
                student.save()
                updated_count += 1
            
            return JsonResponse({
                'success': True,
                'message': f'Moved {updated_count} student(s) to {new_class.name}',
                'updated_count': updated_count
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error moving students: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required
@require_GET
def get_class_levels(request):
    """
    API endpoint to get all active class levels for AJAX requests.
    Used for bulk operations like moving students between classes.    """  
    
    try:
        # Get all active class levels
        class_levels = ClassLevel.objects.filter(
            is_active=True
        ).select_related(
            'educational_level'
        ).order_by('educational_level__order', 'order')
        
        # Prepare response data
        data = [
            {
                'id': cls.id,
                'name': cls.name,
                'code': cls.code,
                'order': cls.order,
                'educational_level': {
                    'id': cls.educational_level.id,
                    'name': cls.educational_level.name,
                    'code': cls.educational_level.code
                } if cls.educational_level else None,
                'full_name': f"{cls.name} ({cls.educational_level.name})" if cls.educational_level else cls.name
            }
            for cls in class_levels
        ]
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data)
        })
        
    except Exception as e:
        # Log error (you can use Django logging here)
        print(f"Error fetching class levels: {str(e)}")
        
        return JsonResponse({
            'success': False,
            'message': 'Failed to load class levels',
            'error': str(e)
        })


@login_required
def student_report(request, student_id):
    """
    Generate student report
    """
    student = get_object_or_404(Student, id=student_id)
    
    # Get academic history
    academic_history = []
    # You would query your academic history model here
    
    # Get attendance summary
    attendance_summary = {}
    # You would query attendance data here
    
    # Get fee information
    fee_info = {}
    # You would query fee data here
    
    context = {
        'student': student,
        'academic_history': academic_history,
        'attendance_summary': attendance_summary,
        'fee_info': fee_info,
    }
    
    return render(request, 'admin/students/includes/student_report.html', context)

@login_required
def remove_student_subject(request, student_id):
    if request.method == 'POST':
        student = get_object_or_404(Student, id=student_id)
        subject_id = request.POST.get('subject_id')
        subject = get_object_or_404(Subject, id=subject_id)
        
        if subject in student.optional_subjects.all():
            student.optional_subjects.remove(subject)
            return JsonResponse({'success': True, 'message': 'Subject removed successfully'})
        
        return JsonResponse({'success': False, 'message': 'Subject not found in student\'s subjects'})



@login_required
def add_optional_subjects(request, student_id):
    if request.method == 'POST':
        student = get_object_or_404(Student, id=student_id)
        subject_ids = json.loads(request.POST.get('subject_ids', '[]'))
        
        added_count = 0
        for subject_id in subject_ids:
            try:
                subject = Subject.objects.get(id=subject_id, is_compulsory=False)
                student.optional_subjects.add(subject)
                added_count += 1
            except Subject.DoesNotExist:
                continue
        
        return JsonResponse({
            'success': True, 
            'message': f'Added {added_count} subject(s) to student'
        })

@login_required
@require_POST
def remove_parent_from_student(request, student_id):
    """
    Remove a parent from a student's parent list
    """
    try:
        student = get_object_or_404(Student, id=student_id)
        parent_id = request.POST.get('parent_id')
        
        if not parent_id:
            return JsonResponse({
                'success': False,
                'message': 'Parent ID is required'
            }, status=400)
        
        parent = get_object_or_404(Parent, id=parent_id)
        
        # Check if parent is associated with this student
        if parent in student.parents.all():
            # Remove the student from parent's students list
            parent.students.remove(student)
            
            # If this was the only student for this parent, delete the parent
            if parent.students.count() == 0:
                parent.delete()
                message = f'Parent {parent.full_name} has been removed and deleted since they had no other students.'
            else:
                message = f'Parent {parent.full_name} has been removed from this student.'
            
            return JsonResponse({
                'success': True,
                'message': message
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'This parent is not associated with this student.'
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })


@login_required
def add_student_to_parent(request, parent_id):
    """
    Add a student to a parent's assigned students
    """
    parent = get_object_or_404(Parent, id=parent_id)
    
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        
        if not student_id:
            messages.error(request, "Please select a student.")
            return redirect('admin_view_parent', parent_id=parent_id)
        
        try:
            student = get_object_or_404(Student, id=student_id, is_active=True)
            
            with transaction.atomic():
                # Check if student is already assigned to this parent
                if student in parent.students.all():
                    messages.warning(request, f"Student '{student.full_name}' is already assigned to '{parent.full_name}'.")
                else:
                    # Get the student's existing parents
                    existing_parents = student.parents.all()
                    
                    # Check if force assignment is requested
                    force_assignment = request.POST.get('force_assignment') == 'on'
                    
                    if existing_parents.exists() and not force_assignment:
                        # Student already has other parents
                        existing_parent_names = [p.full_name for p in existing_parents]
                        messages.error(request, 
                            f"Student '{student.full_name}' is already assigned to other parent(s): "
                            f"{', '.join(existing_parent_names)}. "
                            f"Use 'Force assignment' to assign anyway."
                        )
                        return redirect('admin_view_parent', parent_id=parent_id)
                    
                    # If force assignment, we'll just add the parent (Django ManyToMany handles duplicates)
                    # Add the student to parent
                    parent.students.add(student)
                    
                    # Handle fee responsibility if parent is fee responsible
                    if parent.is_fee_responsible:
                        # Make this parent fee responsible for this student
                        # Since it's a ManyToMany, we need to update through model if it exists
                        # or handle it differently based on your model structure
                        pass
                    
                    messages.success(request, f"Student '{student.full_name}' has been successfully assigned to '{parent.full_name}'.")
            
        except Student.DoesNotExist:
            messages.error(request, "Selected student not found or is inactive.")
        except Exception as e:
            messages.error(request, f"Error assigning student: {str(e)}")
        
        return redirect('admin_view_parent', parent_id=parent_id)
    
    # If GET request, redirect to parent detail page
    return redirect('admin_view_parent', parent_id=parent_id)


@login_required
def remove_student_from_parent(request, parent_id, student_id):
    """
    Remove a student from a parent's assigned students
    """
    if request.method == 'POST':
        parent = get_object_or_404(Parent, id=parent_id)
        student = get_object_or_404(Student, id=student_id)
        
        try:
            # Check if the student is actually assigned to this parent
            if student in parent.students.all():
                # Remove the relationship
                parent.students.remove(student)
                
                # Update parent's fee responsibility if needed
                if parent.is_fee_responsible and student.parents.filter(is_fee_responsible=True).exists():
                    # Another fee responsible parent exists for this student
                    pass
                elif parent.is_fee_responsible and not student.parents.filter(is_fee_responsible=True).exists():
                    # This was the only fee responsible parent
                    # You might want to handle this case - perhaps set another parent as fee responsible
                    pass
                
                messages.success(request, f"Student '{student.full_name}' has been removed from '{parent.full_name}'.")
            else:
                messages.warning(request, f"Student '{student.full_name}' is not assigned to '{parent.full_name}'.")
                
        except Exception as e:
            messages.error(request, f"Error removing student: {str(e)}")
        
        return redirect('admin_view_parent', parent_id=parent_id)
    
    # If not POST request, redirect to parent detail page
    return redirect('admin_view_parent', parent_id=parent_id)


@login_required
def student_status(request):
    """Manage student statuses"""
    students = Student.objects.select_related('class_level', 'stream_class').all()
    
    # Filters
    status_filter = request.GET.get('status', '')
    if status_filter:
        students = students.filter(status=status_filter)
    
    # Status statistics
    status_stats = Student.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    # Calculate age statistics
    today = date.today()
    age_stats = {
        'under_10': students.filter(date_of_birth__isnull=False).filter(
            date_of_birth__gte=date(today.year - 10, today.month, today.day)
        ).count(),
        '10_15': students.filter(date_of_birth__isnull=False).filter(
            date_of_birth__lt=date(today.year - 10, today.month, today.day),
            date_of_birth__gte=date(today.year - 15, today.month, today.day)
        ).count(),
        'over_15': students.filter(date_of_birth__isnull=False).filter(
            date_of_birth__lt=date(today.year - 15, today.month, today.day)
        ).count(),
    }
    
    context = {
        'students': students,
        'status_stats': status_stats,
        'age_stats': age_stats,
        'status_choices': STATUS_CHOICES,
        'status_filter': status_filter,
    }
    return render(request, 'admin/students/student_status.html', context)

@login_required
def student_edit(request, student_id):
    """
    View for editing student details with proper stream pre-population
    """
    student = get_object_or_404(Student, pk=student_id)
    
    # Get related data for the form
    class_levels = ClassLevel.objects.filter(is_active=True).select_related('educational_level')
    academic_years = AcademicYear.objects.all()
    previous_schools = PreviousSchool.objects.all()
    
    # Get streams - include student's current stream even if not active
    if student.class_level:
        # Get active streams for student's class level
        stream_classes = StreamClass.objects.filter(
            class_level=student.class_level,
            is_active=True
        ).select_related('class_level')
        
        # If student has a stream that's not in active streams, include it
        if student.stream_class and not stream_classes.filter(id=student.stream_class.id).exists():
            stream_classes = stream_classes | StreamClass.objects.filter(id=student.stream_class.id)
    else:
        stream_classes = StreamClass.objects.filter(is_active=True).select_related('class_level')
    
    # Get all streams for JavaScript initialization
    all_streams = StreamClass.objects.filter(is_active=True).select_related('class_level')
    
    # Get student's current subjects (from optional_subjects)
    student_subjects = student.optional_subjects.all() if hasattr(student, 'optional_subjects') else []
    student_subjects_ids = [subject.id for subject in student_subjects]
    
    if request.method == 'POST':
        form = StudentEditForm(request.POST, request.FILES, instance=student)
        
        if form.is_valid():
            try:
                # Get action type from form
                action_type = request.POST.get('action_type', 'save_only')
                
                # Save the student
                student = form.save()
                
                # Prepare response
                response_data = {
                    'success': True,
                    'message': 'Student updated successfully!',
                    'student_name': student.full_name,
                }
                
                # Add profile pic URL if exists
                if student.profile_pic:
                    response_data['profile_pic_url'] = student.profile_pic.url
                
                # Handle AJAX request
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse(response_data)
                
                # Handle regular form submission
                messages.success(request, 'Student updated successfully!')
                
                # Redirect based on action type
                if action_type == 'save_and_view':
                    return redirect('admin_student_detail', student_id=student.id)
                elif action_type == 'save_and_add_parent':
                    return redirect('admin_add_parent_to_student', student_id=student.id)
                elif action_type == 'save_and_add_another':
                    return redirect('admin_add_student')
                elif action_type == 'save_and_return_to_list':
                    return redirect('admin_students_list')
                else:  # save_only
                    return redirect('admin_student_edit', student_id=student.id)
                    
            except Exception as e:
                # Handle errors
                error_msg = str(e)
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': f'Error updating student: {error_msg}'
                    }, status=400)
                else:
                    messages.error(request, f'Error updating student: {error_msg}')
        else:
            # Form has errors
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Convert Django form errors to simpler format for frontend
                errors_dict = {}
                for field, errors in form.errors.items():
                    errors_dict[field] = [str(error) for error in errors]
                
                return JsonResponse({
                    'success': False,
                    'message': 'Please correct the errors below',
                    'errors': errors_dict
                }, status=400)
            else:
                # For non-AJAX, we'll show errors in the template
                messages.error(request, 'Please correct the errors below')
    else:
        # GET request - initialize form with student data
        form = StudentEditForm(instance=student)
        
        # Store the current stream ID in form data for JavaScript
        if student.stream_class:
            form.fields['stream_class'].widget.attrs['data-current-stream-id'] = str(student.stream_class.id)
        
        # Set initial subjects
        form.fields['subjects'].initial = student_subjects
    
    # Get subjects for the current class level to display in the form
    if student.class_level:
        subjects = Subject.objects.filter(
            educational_level=student.class_level.educational_level,
            is_active=True
        ).select_related('educational_level').order_by('name')
    else:
        subjects = Subject.objects.filter(is_active=True).select_related('educational_level').order_by('name')
    
    # Prepare context
    context = {
        'student': student,
        'form': form,
        'academic_years': academic_years,
        'class_levels': class_levels,
        'stream_classes': stream_classes,  # Initial streams for current class
        'all_streams': all_streams,  # All streams for JavaScript
        'subjects': subjects,
        'previous_schools': previous_schools,
        'student_subjects': student_subjects,
        'student_subjects_ids': student_subjects_ids,
        'gender_choices': GENDER_CHOICES,
        'status_choices': STATUS_CHOICES,
        'today': date.today(),
        'page_title': f'Edit Student - {student.full_name}',
    }
    
    return render(request, 'admin/students/edit_student.html', context)


@login_required
def student_delete(request, id):
    """Delete student"""
    student = get_object_or_404(Student, id=id)
    
    if request.method == 'POST':
        student_name = student.full_name
        student.delete()
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Student {student_name} deleted successfully!'
            })
        return redirect('admin_students_list')
    
    context = {
        'student': student
    }
    return render(request, 'admin/students/student_delete.html', context)


def student_detail(request, id):
    """View student details"""
    student = get_object_or_404(Student, id=id)
    
    # Get related data
    parents = student.parents.all()
    optional_subjects = student.optional_subjects.all()
    
    # Get all available optional subjects for student's class level
    available_subjects = []
    if student.class_level:
        # Get subjects from student's educational level that are not compulsory
        educational_level = student.class_level.educational_level
        available_subjects = Subject.objects.filter(
            educational_level=educational_level,
            is_compulsory=False,
            is_active=True
        ).exclude(
            id__in=optional_subjects.values_list('id', flat=True)
        )
    
    # Calculate age
    age = None
    if student.date_of_birth:
        today = date.today()
        age = today.year - student.date_of_birth.year - (
            (today.month, today.day) < (student.date_of_birth.month, student.date_of_birth.day)
        )
    
    # Get compulsory subjects count
    compulsory_count = 0
    if student.class_level and student.class_level.educational_level:
        compulsory_count = Subject.objects.filter(
            educational_level=student.class_level.educational_level,
            is_compulsory=True,
            is_active=True
        ).count()
    
    # Get current academic year
    current_academic_year = AcademicYear.objects.filter(is_active=True).first()
    
    context = {
        'student': student,
        'parents': parents,
        'optional_subjects': optional_subjects,
        'available_subjects': available_subjects,
        'compulsory_count': compulsory_count,
        'optional_count': optional_subjects.count(),
        'age': age,
        'current_academic_year': current_academic_year,
        'student_subjects': list(optional_subjects),  # All subjects for this student
    }
    return render(request, 'admin/students/student_detail.html', context)


@login_required
@require_POST
def students_ajax(request):
    """Handle AJAX requests for student operations"""
    action = request.POST.get('action')
    
    if action == 'delete':
        student_id = request.POST.get('id')
        student = get_object_or_404(Student, id=student_id)
        student_name = student.full_name
        student.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Student {student_name} deleted successfully!'
        })
    
    elif action == 'toggle_status':
        student_id = request.POST.get('id')
        student = get_object_or_404(Student, id=student_id)
        student.is_active = not student.is_active
        student.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Status updated for {student.full_name}',
            'is_active': student.is_active
        })
    
    elif action == 'get_student':
        student_id = request.POST.get('id')
        student = get_object_or_404(Student, id=student_id)
        
        # Calculate age
        age = None
        if student.date_of_birth:
            today = date.today()
            age = today.year - student.date_of_birth.year - (
                (today.month, today.day) < (student.date_of_birth.month, student.date_of_birth.day)
            )
        
        return JsonResponse({
            'success': True,
            'student': {
                'id': student.id,
                'full_name': student.full_name,
                'registration_number': student.registration_number,
                'class_level': student.class_level.name if student.class_level else '',
                'class_level_id': student.class_level.id if student.class_level else None,
                'stream_class': student.stream_class.name if student.stream_class else '',
                'stream_class_id': student.stream_class.id if student.stream_class else None,
                'status': student.status,
                'status_display': student.get_status_display(),
                'is_active': student.is_active,
                'age': age,
                'primary_contact': student.primary_contact,
                'gender': student.get_gender_display(),
                'date_of_birth': student.date_of_birth.strftime('%Y-%m-%d') if student.date_of_birth else '',
                'address': student.address or '',
                'parents': [{'id': p.id, 'name': p.full_name} for p in student.parents.all()],
            }
        })
    
    elif action == 'bulk_update':
        # Handle bulk status update
        student_ids = request.POST.getlist('student_ids[]')
        new_status = request.POST.get('status')
        
        if not student_ids or not new_status:
            return JsonResponse({
                'success': False,
                'message': 'No students selected or status not provided'
            })
        
        students = Student.objects.filter(id__in=student_ids)
        updated_count = students.update(status=new_status, is_active=(new_status == 'active'))
        
        return JsonResponse({
            'success': True,
            'message': f'Updated status for {updated_count} students',
            'updated_count': updated_count
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid action'})

# ============================================
# PARENT VIEWS
# ============================================

@login_required
def parents_list(request):
    """List all parents"""
    parents = Parent.objects.prefetch_related('students').all()
    
    # Filters
    search_query = request.GET.get('search', '')
    relationship_filter = request.GET.get('relationship', '')
    fee_responsible_filter = request.GET.get('fee_responsible', '')
    
    if search_query:
        parents = parents.filter(
            Q(full_name__icontains=search_query) |
            Q(first_phone_number__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(students__first_name__icontains=search_query) |
            Q(students__last_name__icontains=search_query)
        ).distinct()
    
    if relationship_filter:
        parents = parents.filter(relationship=relationship_filter)
    
    if fee_responsible_filter:
        if fee_responsible_filter == 'yes':
            parents = parents.filter(is_fee_responsible=True)
        elif fee_responsible_filter == 'no':
            parents = parents.filter(is_fee_responsible=False)
    
    # Count statistics
    total_parents = parents.count()
    fee_responsible_count = Parent.objects.filter(is_fee_responsible=True).count()
    
    # Pagination
    paginator = Paginator(parents.order_by('-created_at'), 25)
    page = request.GET.get('page', 1)
    parents_page = paginator.get_page(page)
    
    context = {
        'parents': parents_page,
        'relationship_choices': RELATIONSHIP_CHOICES,
        'search_query': search_query,
        'relationship_filter': relationship_filter,
        'fee_responsible_filter': fee_responsible_filter,
        'total_parents': total_parents,
        'fee_responsible_count': fee_responsible_count,
    }
    return render(request, 'admin/students/parent_list.html', context)


@login_required
def add_parent(request):
    """
    Add a new parent/guardian with ability to assign multiple students
    """
    # Get all active students for the select field
    available_students = Student.objects.filter(
        is_active=True
    ).select_related('class_level').order_by('first_name', 'last_name')
    
    if request.method == 'POST':
        form = ParentStudentForm(request.POST)
        action = request.POST.get('action', 'save')
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Check for duplicate phone number
                    phone = form.cleaned_data['first_phone_number']
                    email = form.cleaned_data.get('email', '').strip()
                    
                    # Check if parent with same primary phone already exists
                    existing_parent = Parent.objects.filter(
                        Q(first_phone_number=phone) | 
                        Q(second_phone_number=phone)
                    ).first()
                    
                    if existing_parent:
                        # Update existing parent
                        existing_parent.full_name = form.cleaned_data['full_name']
                        existing_parent.relationship = form.cleaned_data['relationship']
                        existing_parent.address = form.cleaned_data['address']
                        existing_parent.email = email
                        existing_parent.second_phone_number = form.cleaned_data.get('second_phone_number', '')
                        existing_parent.save()
                        parent = existing_parent
                        message = f"Parent '{parent.full_name}' updated successfully!"
                    else:
                        # Create new parent
                        parent = form.save()
                        message = f"Parent '{parent.full_name}' created successfully!"
                    
                    # Get selected student IDs from POST data
                    student_ids = request.POST.getlist('students')
                    
                    if student_ids:
                        # Get student objects
                        students = Student.objects.filter(id__in=student_ids, is_active=True)
                        
                        # Check for force assignment
                        force_assignment = request.POST.get('force_assign', 'false') == 'true'
                        
                        for student in students:
                            # Check if student already has this parent
                            existing_relationship = Parent.objects.filter(
                                student=student,
                                parent=parent
                            ).first()
                            
                            if existing_relationship:
                                # Update existing relationship
                                existing_relationship.relationship = parent.relationship
                                existing_relationship.is_fee_responsible = form.cleaned_data.get('is_fee_responsible', False)
                                existing_relationship.save()
                            else:
                                # Check if student has other parents
                                existing_parents = Parent.objects.filter(
                                    student=student
                                ).exclude(parent=parent)
                                
                                if existing_parents.exists() and not force_assignment:
                                    # Get existing parent names
                                    existing_parent_names = existing_parents.values_list('parent__full_name', flat=True)
                                    form.add_error(None, 
                                        f"Student '{student.full_name}' is already assigned to other parent(s): "
                                        f"{', '.join(existing_parent_names)}. "
                                        f"Use 'Force assignment' to reassign."
                                    )
                                    return render(request, 'admin/students/add_parent.html', {
                                        'form': form,
                                        'relationship_choices': RELATIONSHIP_CHOICES,
                                        'available_students': available_students,
                                    })
                                
                                # If force assignment or no existing parents, create new relationship
                                if force_assignment:
                                    # Remove all existing relationships for this student
                                    existing_parents.delete()
                                
                                # Create new relationship
                                Parent.objects.create(
                                    student=student,
                                    parent=parent,
                                    relationship=parent.relationship,
                                    is_fee_responsible=form.cleaned_data.get('is_fee_responsible', False)
                                )
                    
                    # Handle fee responsibility
                    if form.cleaned_data.get('is_fee_responsible', False):
                        # If this parent is fee responsible, update all their relationships
                        Parent.objects.filter(parent=parent).update(
                            is_fee_responsible=True
                        )
                    
                    messages.success(request, message)
                    
                    # Handle different actions
                    if action == 'save_and_view':
                        return redirect('admin_view_parent', parent_id=parent.id)
                    elif action == 'save_and_add_another':
                        return redirect('admin_add_parent')
                    else:
                        return redirect('admin_parents_list')
            
            except ValidationError as e:
                form.add_error(None, str(e))
            except Exception as e:
                form.add_error(None, f"An error occurred: {str(e)}")
    
    else:
        form = ParentStudentForm()
    
    context = {
        'form': form,
        'relationship_choices': RELATIONSHIP_CHOICES,
        'available_students': available_students,
    }
    
    return render(request, 'admin/students/add_parent.html', context)


@login_required
def parent_detail(request, parent_id):
    """
    View detailed information about a parent/guardian
    """
    parent = get_object_or_404(Parent, id=parent_id)
    
    # Get all students not assigned to this parent
    assigned_student_ids = parent.students.values_list('id', flat=True)
    all_students = Student.objects.filter(
        is_active=True
    ).exclude(id__in=assigned_student_ids).order_by('first_name')
    
    # Calculate active students count
    active_students_count = parent.students.filter(is_active=True).count()
    
    # Get related parents (parents sharing the same students)
    related_parents = set()
    for student in parent.students.all():
        for other_parent in student.parents.all():
            if other_parent != parent:
                related_parents.add(other_parent)
    
    # Count related parents
    related_parents_count = len(related_parents)
    
    context = {
        'parent': parent,
        'all_students': all_students,
        'active_students_count': active_students_count,
        'related_parents': list(related_parents),
        'related_parents_count': related_parents_count,
    }
    
    return render(request, 'admin/students/parent_detail.html', context)


@login_required
def parent_edit(request, parent_id):
    parent = get_object_or_404(Parent, id=parent_id)

    available_students = Student.objects.filter(
        is_active=True
    ).select_related('class_level').order_by('first_name', 'last_name')

    current_students = parent.students.all()

    if request.method == 'POST':
        form = ParentStudentForm(request.POST, instance=parent)
        action = request.POST.get('action', 'save')

        if form.is_valid():
            try:
                with transaction.atomic():

                    phone = form.cleaned_data['first_phone_number']
                    email = form.cleaned_data.get('email', '').strip()

                    # 🔹 Check duplicate phone number
                    existing_parent = Parent.objects.filter(
                        Q(first_phone_number=phone) | Q(second_phone_number=phone)
                    ).exclude(id=parent.id).first()

                    if existing_parent:
                        # Merge parents
                        existing_parent.full_name = form.cleaned_data['full_name']
                        existing_parent.relationship = form.cleaned_data['relationship']
                        existing_parent.address = form.cleaned_data['address']
                        existing_parent.email = email
                        existing_parent.second_phone_number = form.cleaned_data.get('second_phone_number', '')
                        existing_parent.is_fee_responsible = form.cleaned_data.get('is_fee_responsible', False)
                        existing_parent.save()

                        # Move students
                        existing_parent.students.add(*current_students)
                        parent.delete()
                        parent = existing_parent

                        message = f"Parent merged with existing record '{parent.full_name}'."
                    else:
                        parent = form.save()
                        message = f"Parent '{parent.full_name}' updated successfully."

                    # 🔹 Handle students
                    student_ids = request.POST.getlist('students')
                    selected_students = Student.objects.filter(id__in=student_ids, is_active=True)

                    force_assignment = request.POST.get('force_assign') == 'true'

                    for student in selected_students:
                        other_parents = student.parents.exclude(id=parent.id)

                        if other_parents.exists() and not force_assignment:
                            names = ", ".join(other_parents.values_list('full_name', flat=True))
                            raise ValidationError(
                                f"Student '{student.full_name}' already assigned to: {names}. "
                                f"Use force assignment to override."
                            )

                        if force_assignment:
                            student.parents.clear()

                        parent.students.add(student)

                    # 🔹 Remove unchecked students
                    for student in current_students:
                        if str(student.id) not in student_ids:
                            parent.students.remove(student)

                    messages.success(request, message)

                    if action == 'save_and_view':
                        return redirect('admin_view_parent', parent_id=parent.id)
                    elif action == 'save_and_add_another':
                        return redirect('admin_add_parent')
                    else:
                        return redirect('admin_parents_list')

            except ValidationError as e:
                form.add_error(None, e.message)
            except Exception as e:
                form.add_error(None, f"Unexpected error: {str(e)}")

    else:
        form = ParentStudentForm(instance=parent)

    return render(request, 'admin/students/edit_parent.html', {
        'form': form,
        'parent': parent,
        'current_students': current_students,
        'relationship_choices': RELATIONSHIP_CHOICES,
        'available_students': available_students,
    })





def parent_delete(request):
    """
    AJAX view for deleting a parent
    """
    if request.method == 'POST':
        parent_id = request.POST.get('parent_id')
        try:
            parent = Parent.objects.get(id=parent_id)
            parent_name = parent.full_name
            parent.delete()
            return JsonResponse({
                'success': True,
                'message': f'Parent "{parent_name}" has been deleted successfully.'
            })
        except Parent.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Parent not found.'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    }) 
    
    

# ============================================
# PREVIOUS SCHOOL VIEWS
# ============================================

@login_required
def previous_schools_list(request):
    """Display previous schools management page"""
    schools = PreviousSchool.objects.all().order_by('name')
    
    # Get school level choices from model
    school_level_choices = PreviousSchool.SCHOOL_LEVEL_CHOICES
    
    context = {
        'schools': schools,
        'school_level_choices': school_level_choices,
    }
    
    return render(request, 'admin/students/previous_schools_list.html', context)


@login_required
def previous_schools_crud(request):
    """Handle AJAX CRUD operations for previous schools"""
    if request.method == 'POST':
        action = request.POST.get('action', '').lower()
        
        try:
            if action == 'create':
                return create_previous_school(request)
            elif action == 'update':
                return update_previous_school(request)
            elif action == 'delete':
                return delete_previous_school(request)
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid action specified.'
                })
                
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'POST request required.'
    })


def create_previous_school(request):
    """Create a new previous school"""
    # Get and validate required fields
    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({
            'success': False,
            'message': 'School name is required.'
        })
    
    school_level = request.POST.get('school_level', '').strip()
    if not school_level:
        return JsonResponse({
            'success': False,
            'message': 'School level is required.'
        })
    
    # Validate school level choice
    valid_levels = [choice[0] for choice in PreviousSchool.SCHOOL_LEVEL_CHOICES]
    if school_level not in valid_levels:
        return JsonResponse({
            'success': False,
            'message': 'Invalid school level selected.'
        })
    
    # Validate name length
    if len(name) < 2:
        return JsonResponse({
            'success': False,
            'message': 'School name must be at least 2 characters long.'
        })
    
    if len(name) > 200:
        return JsonResponse({
            'success': False,
            'message': 'School name cannot exceed 200 characters.'
        })
    
    # Get optional field
    location = request.POST.get('location', '').strip()
    
    # Validate location length if provided
    if location and len(location) > 200:
        return JsonResponse({
            'success': False,
            'message': 'Location cannot exceed 200 characters.'
        })
    
    try:
        # Check for duplicate school name (case-insensitive)
        if PreviousSchool.objects.filter(name__iexact=name).exists():
            return JsonResponse({
                'success': False,
                'message': f'A school with name "{name}" already exists.'
            })
        
        # Create the school
        school = PreviousSchool.objects.create(
            name=name,
            school_level=school_level,
            location=location if location else None
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Previous school "{name}" created successfully.',
            'school': {
                'id': school.id,
                'name': school.name,
                'school_level': school.school_level,
                'school_level_display': school.get_school_level_display(),
                'location': school.location,
                'created_at': school.created_at.strftime('%Y-%m-%d')
            }
        })
        
    except IntegrityError as e:
        if 'unique' in str(e).lower():
            return JsonResponse({
                'success': False,
                'message': f'A school with name "{name}" already exists.'
            })
        return JsonResponse({
            'success': False,
            'message': f'Database error: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error creating school: {str(e)}'
        })


def update_previous_school(request):
    """Update an existing previous school"""
    school_id = request.POST.get('id')
    if not school_id:
        return JsonResponse({
            'success': False,
            'message': 'School ID is required.'
        })
    
    try:
        school = PreviousSchool.objects.get(id=school_id)
    except PreviousSchool.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'School not found.'
        })
    
    # Get and validate required fields
    name = request.POST.get('name', '').strip()
    school_level = request.POST.get('school_level', '').strip()
    
    if not name or not school_level:
        return JsonResponse({
            'success': False,
            'message': 'School name and level are required.'
        })
    
    # Validate school level choice
    valid_levels = [choice[0] for choice in PreviousSchool.SCHOOL_LEVEL_CHOICES]
    if school_level not in valid_levels:
        return JsonResponse({
            'success': False,
            'message': 'Invalid school level selected.'
        })
    
    # Validate name length
    if len(name) < 2:
        return JsonResponse({
            'success': False,
            'message': 'School name must be at least 2 characters long.'
        })
    
    if len(name) > 200:
        return JsonResponse({
            'success': False,
            'message': 'School name cannot exceed 200 characters.'
        })
    
    # Get optional field
    location = request.POST.get('location', '').strip()
    
    # Validate location length if provided
    if location and len(location) > 200:
        return JsonResponse({
            'success': False,
            'message': 'Location cannot exceed 200 characters.'
        })
    
    try:
        # Check for duplicate school name (case-insensitive, excluding current)
        if PreviousSchool.objects.filter(name__iexact=name).exclude(id=school.id).exists():
            return JsonResponse({
                'success': False,
                'message': f'A school with name "{name}" already exists.'
            })
        
        # Update the school
        school.name = name
        school.school_level = school_level
        school.location = location if location else None
        school.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Previous school "{name}" updated successfully.',
            'school': {
                'id': school.id,
                'name': school.name,
                'school_level': school.school_level,
                'school_level_display': school.get_school_level_display(),
                'location': school.location,
                'created_at': school.created_at.strftime('%Y-%m-%d')
            }
        })
        
    except IntegrityError as e:
        if 'unique' in str(e).lower():
            return JsonResponse({
                'success': False,
                'message': f'A school with name "{name}" already exists.'
            })
        return JsonResponse({
            'success': False,
            'message': f'Database error: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating school: {str(e)}'
        })


def delete_previous_school(request):
    """Delete a previous school"""
    school_id = request.POST.get('id')
    if not school_id:
        return JsonResponse({
            'success': False,
            'message': 'School ID is required.'
        })
    
    try:
        school = PreviousSchool.objects.get(id=school_id)
        school_name = school.name
        
        # Check if school is referenced by any student

        if school.students.exists() or school.transferred_students.exists():
            student_count = school.students.count() + school.transferred_students.count()
            return JsonResponse({
                'success': False,
                'message': f'Cannot delete school "{school_name}". It is referenced by {student_count} student(s).'
            })
        
        # Delete the school
        school.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Previous school "{school_name}" deleted successfully.'
        })
        
    except PreviousSchool.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'School not found.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting school: {str(e)}'
        })

# ============================================
# HELPER VIEWS
# ============================================

@login_required
def get_subjects_by_class(request):
    """
    AJAX endpoint to return active subjects
    based on the educational level of a given class level
    """
    class_id = request.GET.get('class_id')

    if not class_id:
        return JsonResponse({
            'success': False,
            'subjects': [],
            'message': 'Class ID is required'
        })

    # Get class level safely
    class_level = get_object_or_404(
        ClassLevel,
        id=class_id,
        is_active=True
    )

    # Get educational level from class level
    educational_level = class_level.educational_level

    # Fetch ACTIVE subjects for that educational level
    subjects = Subject.objects.filter(
        educational_level=educational_level,
        is_active=True
    ).order_by('name')

    # Prepare data for <select><option>
    data = [
        {
            'id': subject.id,
            'name': f"{subject.name} ({subject.code})"
        }
        for subject in subjects
    ]

    return JsonResponse({
        'success': True,
        'subjects': data
    })

    
@login_required
def student_export(request):
    """Export students to CSV or Excel"""
    import csv
    from django.http import HttpResponse
    
    # Create the HttpResponse object with CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="students.csv"'
    
    writer = csv.writer(response)
    
    # Write headers
    writer.writerow([
        'Registration Number', 'Full Name', 'Class', 'Stream', 
        'Gender', 'Date of Birth', 'Age', 'Status', 'Address',
        'Primary Contact', 'Parent Name', 'Parent Phone', 'Parent Email'
    ])
    
    # Get students with related data
    students = Student.objects.select_related(
        'class_level', 'stream_class'
    ).prefetch_related('parents').filter(is_active=True)
    
    for student in students:
        # Get primary parent (fee responsible or first)
        parent = student.parents.filter(is_fee_responsible=True).first()
        if not parent:
            parent = student.parents.first()
        
        writer.writerow([
            student.registration_number or '',
            student.full_name,
            student.class_level.name if student.class_level else '',
            student.stream_class.name if student.stream_class else '',
            student.get_gender_display(),
            student.date_of_birth.strftime('%Y-%m-%d') if student.date_of_birth else '',
            student.age or '',
            student.get_status_display(),
            student.address or '',
            student.primary_contact or '',
            parent.full_name if parent else '',
            parent.first_phone_number if parent else '',
            parent.email if parent else '',
        ])
    
    return response
# ============================================================================
# STAFF MANAGEMENT VIEWS
# ============================================================================

@login_required
def staffs_list(request):
    """Display staff management page"""
    staffs = Staffs.objects.select_related('admin').all().order_by('admin__last_name', 'admin__first_name')
    
    # Count active staff
    active_staff_count = staffs.filter(admin__is_active=True).count()
    
    context = {
        'staffs': staffs,
        'active_staff_count': active_staff_count,
    }
    
    return render(request, 'admin/staff/staffs_list.html', context)


@login_required
def staffs_crud(request):
    """Handle AJAX CRUD operations for staff"""
    if request.method == 'POST':
        action = request.POST.get('action', '').lower()
        
        try:
            if action == 'create':
                return create_staff(request)
            elif action == 'update':
                return update_staff(request)
            elif action == 'toggle_status':
                return toggle_staff_status(request)
            elif action == 'delete':
                return delete_staff(request)
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid action specified.'
                })
                
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'POST request required.'
    })


def create_staff(request):
    """Create a new staff member"""
    # Get and validate required fields
    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    username = request.POST.get('username', '').strip()
    email = request.POST.get('email', '').strip()
    password = request.POST.get('password', '').strip()
    confirm_password = request.POST.get('confirm_password', '').strip()
    user_type = request.POST.get('user_type', '').strip()
    
    # Validate required fields
    required_fields = {
        'first_name': first_name,
        'last_name': last_name,
        'username': username,
        'email': email,
        'password': password,
        'user_type': user_type
    }
    
    for field_name, value in required_fields.items():
        if not value:
            return JsonResponse({
                'success': False,
                'message': f'{field_name.replace("_", " ").title()} is required.'
            })
    
    # Validate name length
    if len(first_name) < 2 or len(last_name) < 2:
        return JsonResponse({
            'success': False,
            'message': 'First name and last name must be at least 2 characters long.'
        })
    
    if len(first_name) > 50 or len(last_name) > 50:
        return JsonResponse({
            'success': False,
            'message': 'First name and last name cannot exceed 50 characters.'
        })
    
    # Validate username
    if len(username) < 3 or len(username) > 150:
        return JsonResponse({
            'success': False,
            'message': 'Username must be 3-150 characters long.'
        })
    
    # Validate email
    if '@' not in email or '.' not in email:
        return JsonResponse({
            'success': False,
            'message': 'Please enter a valid email address.'
        })
    
    # Validate password
    if password != confirm_password:
        return JsonResponse({
            'success': False,
            'message': 'Passwords do not match.'
        })
    
    if len(password) < 8:
        return JsonResponse({
            'success': False,
            'message': 'Password must be at least 8 characters long.'
        })
    
    # Validate user_type
    if user_type not in ['1', '2']:
        return JsonResponse({
            'success': False,
            'message': 'Invalid user type selected.'
        })
    
    # Check for existing username
    if CustomUser.objects.filter(username=username).exists():
        return JsonResponse({
            'success': False,
            'message': 'Username already exists.'
        })
    
    # Check for existing email
    if CustomUser.objects.filter(email=email).exists():
        return JsonResponse({
            'success': False,
            'message': 'Email already exists.'
        })
    
    # Get optional fields
    middle_name = request.POST.get('middle_name', '').strip()
    gender = request.POST.get('gender', '').strip()
    date_of_birth = request.POST.get('date_of_birth', '').strip()
    phone_number = request.POST.get('phone_number', '').strip()
    marital_status = request.POST.get('marital_status', '').strip()
    position_title = request.POST.get('position_title', '').strip()
    work_place = request.POST.get('work_place', '').strip()
    joining_date = request.POST.get('joining_date', '').strip()
    is_active = request.POST.get('is_active') == 'on' or request.POST.get('is_active') == 'true'
    
    # Validate phone number if provided
    if phone_number and len(phone_number) > 14:
        return JsonResponse({
            'success': False,
            'message': 'Phone number cannot exceed 14 digits.'
        })
    
    # Parse dates
    date_of_birth_obj = None
    if date_of_birth:
        try:
            date_of_birth_obj = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid date of birth format. Use YYYY-MM-DD.'
            })
    
    joining_date_obj = None
    if joining_date:
        try:
            joining_date_obj = datetime.strptime(joining_date, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid joining date format. Use YYYY-MM-DD.'
            })
    
    try:
        with transaction.atomic():
            # Create CustomUser
            user = CustomUser.objects.create(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=make_password(password),
                user_type=user_type,
                is_active=is_active
            )
            
            # Create Staffs
            staff = Staffs.objects.create(
                admin=user,
                middle_name=middle_name,
                gender=gender,
                date_of_birth=date_of_birth_obj or datetime(2000, 1, 1).date(),
                phone_number=phone_number,
                marital_status=marital_status,
                position_title=position_title,
                work_place=work_place,
                joining_date=joining_date_obj
            )
            
            # Handle file uploads
            if 'profile_picture' in request.FILES:
                profile_picture = request.FILES['profile_picture']
                if profile_picture.size > 2 * 1024 * 1024:  # 2MB
                    raise ValidationError('Profile picture size should not exceed 2MB.')
                
                # Validate file extension
                valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
                ext = os.path.splitext(profile_picture.name)[1].lower()
                if ext not in valid_extensions:
                    raise ValidationError('Invalid file type for profile picture. Allowed: JPG, PNG, GIF.')
                
                # Save the file
                file_name = f'staff_{staff.id}_profile{ext}'
                file_path = default_storage.save(f'profile_pictures/{file_name}', profile_picture)
                staff.profile_picture = file_path
            
            if 'signature' in request.FILES:
                signature = request.FILES['signature']
                if signature.size > 1 * 1024 * 1024:  # 1MB
                    raise ValidationError('Signature size should not exceed 1MB.')
                
                # Validate file extension
                valid_extensions = ['.jpg', '.jpeg', '.png']
                ext = os.path.splitext(signature.name)[1].lower()
                if ext not in valid_extensions:
                    raise ValidationError('Invalid file type for signature. Allowed: JPG, PNG.')
                
                # Save the file
                file_name = f'staff_{staff.id}_signature{ext}'
                file_path = default_storage.save(f'signatures/{file_name}', signature)
                staff.signature = file_path
            
            staff.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Staff member "{staff.get_full_name()}" created successfully.',
                'staff': {
                    'id': staff.id,
                    'full_name': staff.get_full_name(),
                    'username': staff.admin.username,
                    'email': staff.admin.email,
                    'is_active': staff.admin.is_active
                }
            })
            
    except IntegrityError as e:
        return JsonResponse({
            'success': False,
            'message': f'Database error: {str(e)}'
        })
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error creating staff: {str(e)}'
        })


def update_staff(request):
    """Update an existing staff member"""
    staff_id = request.POST.get('id')
    if not staff_id:
        return JsonResponse({
            'success': False,
            'message': 'Staff ID is required.'
        })
    
    try:
        staff = Staffs.objects.get(id=staff_id)
    except Staffs.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Staff member not found.'
        })
    
    # Get and validate required fields
    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    username = request.POST.get('username', '').strip()
    email = request.POST.get('email', '').strip()
    user_type = request.POST.get('user_type', '').strip()
    
    # Validate required fields
    if not all([first_name, last_name, username, email, user_type]):
        return JsonResponse({
            'success': False,
            'message': 'First name, last name, username, email, and user type are required.'
        })
    
    # Validate name length
    if len(first_name) < 2 or len(last_name) < 2:
        return JsonResponse({
            'success': False,
            'message': 'First name and last name must be at least 2 characters long.'
        })
    
    # Validate username
    if len(username) < 3 or len(username) > 150:
        return JsonResponse({
            'success': False,
            'message': 'Username must be 3-150 characters long.'
        })
    
    # Validate email
    if '@' not in email or '.' not in email:
        return JsonResponse({
            'success': False,
            'message': 'Please enter a valid email address.'
        })
    
    # Validate user_type
    if user_type not in ['1', '2']:
        return JsonResponse({
            'success': False,
            'message': 'Invalid user type selected.'
        })
    
    # Check for existing username (excluding current)
    if CustomUser.objects.filter(username=username).exclude(id=staff.admin.id).exists():
        return JsonResponse({
            'success': False,
            'message': 'Username already exists.'
        })
    
    # Check for existing email (excluding current)
    if CustomUser.objects.filter(email=email).exclude(id=staff.admin.id).exists():
        return JsonResponse({
            'success': False,
            'message': 'Email already exists.'
        })
    
    # Handle password change
    password = request.POST.get('password', '').strip()
    confirm_password = request.POST.get('confirm_password', '').strip()
    
    if password:
        if password != confirm_password:
            return JsonResponse({
                'success': False,
                'message': 'Passwords do not match.'
            })
        
        if len(password) < 8:
            return JsonResponse({
                'success': False,
                'message': 'Password must be at least 8 characters long.'
            })
    
    # Get optional fields
    middle_name = request.POST.get('middle_name', '').strip()
    gender = request.POST.get('gender', '').strip()
    date_of_birth = request.POST.get('date_of_birth', '').strip()
    phone_number = request.POST.get('phone_number', '').strip()
    marital_status = request.POST.get('marital_status', '').strip()
    position_title = request.POST.get('position_title', '').strip()
    work_place = request.POST.get('work_place', '').strip()
    joining_date = request.POST.get('joining_date', '').strip()
    is_active = request.POST.get('is_active') == 'on' or request.POST.get('is_active') == 'true'
    
    # Validate phone number if provided
    if phone_number and len(phone_number) > 14:
        return JsonResponse({
            'success': False,
            'message': 'Phone number cannot exceed 14 digits.'
        })
    
    # Parse dates
    date_of_birth_obj = None
    if date_of_birth:
        try:
            date_of_birth_obj = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid date of birth format. Use YYYY-MM-DD.'
            })
    
    joining_date_obj = None
    if joining_date:
        try:
            joining_date_obj = datetime.strptime(joining_date, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid joining date format. Use YYYY-MM-DD.'
            })
    
    try:
        with transaction.atomic():
            # Update CustomUser
            user = staff.admin
            user.username = username
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.user_type = user_type
            user.is_active = is_active
            
            if password:
                user.password = make_password(password)
            
            user.save()
            
            # Update Staffs
            staff.middle_name = middle_name
            staff.gender = gender
            if date_of_birth_obj:
                staff.date_of_birth = date_of_birth_obj
            staff.phone_number = phone_number
            staff.marital_status = marital_status
            staff.position_title = position_title
            staff.work_place = work_place
            if joining_date_obj:
                staff.joining_date = joining_date_obj
            
            # Handle file uploads
            if 'profile_picture' in request.FILES:
                profile_picture = request.FILES['profile_picture']
                if profile_picture.size > 2 * 1024 * 1024:  # 2MB
                    raise ValidationError('Profile picture size should not exceed 2MB.')
                
                # Validate file extension
                valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
                ext = os.path.splitext(profile_picture.name)[1].lower()
                if ext not in valid_extensions:
                    raise ValidationError('Invalid file type for profile picture. Allowed: JPG, PNG, GIF.')
                
                # Delete old file if exists
                if staff.profile_picture:
                    default_storage.delete(staff.profile_picture.name)
                
                # Save new file
                file_name = f'staff_{staff.id}_profile{ext}'
                file_path = default_storage.save(f'profile_pictures/{file_name}', profile_picture)
                staff.profile_picture = file_path
            
            if 'signature' in request.FILES:
                signature = request.FILES['signature']
                if signature.size > 1 * 1024 * 1024:  # 1MB
                    raise ValidationError('Signature size should not exceed 1MB.')
                
                # Validate file extension
                valid_extensions = ['.jpg', '.jpeg', '.png']
                ext = os.path.splitext(signature.name)[1].lower()
                if ext not in valid_extensions:
                    raise ValidationError('Invalid file type for signature. Allowed: JPG, PNG.')
                
                # Delete old file if exists
                if staff.signature:
                    default_storage.delete(staff.signature.name)
                
                # Save new file
                file_name = f'staff_{staff.id}_signature{ext}'
                file_path = default_storage.save(f'signatures/{file_name}', signature)
                staff.signature = file_path
            
            staff.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Staff member "{staff.get_full_name()}" updated successfully.',
                'staff': {
                    'id': staff.id,
                    'full_name': staff.get_full_name(),
                    'username': staff.admin.username,
                    'email': staff.admin.email,
                    'is_active': staff.admin.is_active
                }
            })
            
    except IntegrityError as e:
        return JsonResponse({
            'success': False,
            'message': f'Database error: {str(e)}'
        })
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating staff: {str(e)}'
        })


def toggle_staff_status(request):
    """Toggle staff active status"""
    staff_id = request.POST.get('id')
    if not staff_id:
        return JsonResponse({
            'success': False,
            'message': 'Staff ID is required.'
        })
    
    try:
        staff = Staffs.objects.get(id=staff_id)
        staff.admin.is_active = not staff.admin.is_active
        staff.admin.save()
        
        status_text = 'activated' if staff.admin.is_active else 'deactivated'
        
        return JsonResponse({
            'success': True,
            'message': f'Staff member "{staff.get_full_name()}" {status_text} successfully.',
            'is_active': staff.admin.is_active
        })
        
    except Staffs.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Staff member not found.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating staff status: {str(e)}'
        })


def delete_staff(request):
    """Delete a staff member"""
    staff_id = request.POST.get('id')
    if not staff_id:
        return JsonResponse({
            'success': False,
            'message': 'Staff ID is required.'
        })
    
    try:
        staff = Staffs.objects.get(id=staff_id)
        full_name = staff.get_full_name()
        
        # Delete associated files
        if staff.profile_picture:
            default_storage.delete(staff.profile_picture.name)
        if staff.signature:
            default_storage.delete(staff.signature.name)
        
        # Delete the CustomUser (will cascade to Staffs due to OneToOne relationship)
        staff.admin.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Staff member "{full_name}" deleted successfully.'
        })
        
    except Staffs.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Staff member not found.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting staff: {str(e)}'
        })


@login_required
def view_staff(request, staff_id):
    """View staff details"""
    staff = get_object_or_404(Staffs, id=staff_id)
    
    context = {
        'staff': staff,
    }
    
    return render(request, 'admin/staff/view_staff.html', context)

@login_required
def staff_roles_list(request):
    """Display staff roles management page"""
    # Get all staff members with related data
    staff_members = Staffs.objects.select_related(
        'admin',
        'department'  # Add department relation
    ).all()
    
    # Get statistics
    total_staff = staff_members.count()
    active_staff = staff_members.filter(admin__is_active=True).count()
    
    # Get position_title counts
    roles = Staffs.objects.values('position_title').annotate(count=Count('position_title')).order_by('-count')
    total_roles = roles.count()
    
    # Get departments for dropdown
    departments = Department.objects.filter(is_active=True).order_by('name')
    
    # Role choices from model
    role_choices = ROLE_CHOICES
    
    # Get all staff for dropdowns
    all_staff = Staffs.objects.select_related('admin', 'department').order_by('admin__first_name', 'admin__last_name')
    
    # Filter by position_title if specified
    selected_role = request.GET.get('position_title')
    if selected_role:
        staff_members = staff_members.filter(position_title=selected_role)
    
    # Search functionality for DataTable (if needed for initial load)
    search_query = request.GET.get('search', '')
    if search_query:
        staff_members = staff_members.filter(
            Q(admin__first_name__icontains=search_query) |
            Q(admin__last_name__icontains=search_query) |
            Q(admin__email__icontains=search_query) |
            Q(admin__username__icontains=search_query) |
            Q(phone_number__icontains=search_query) |
            Q(position_title__icontains=search_query) |
            Q(department__name__icontains=search_query)
        )
    
    context = {
        'staff_members': staff_members,
        'all_staff': all_staff,
        'roles': roles,
        'role_choices': role_choices,
        'selected_role': selected_role,
        'search_query': search_query,
        'total_staff': total_staff,
        'active_staff': active_staff,
        'total_roles': total_roles,
        'departments': departments,  # Pass departments for dropdowns
        'page_title': 'Staff Positions Management',
    }
    
    return render(request, 'admin/staff/staff_roles_list.html', context)

@login_required
def staff_roles_crud(request):
    """Handle AJAX CRUD operations for staff roles"""
    if request.method == 'POST':
        action = request.POST.get('action', '').lower()
        
        try:
            if action == 'assign_role':
                return assign_staff_role(request)
            elif action == 'bulk_assign':
                return bulk_assign_roles(request)
            elif action == 'edit_role':
                return edit_staff_role(request)
            elif action == 'remove_role':
                return remove_staff_role(request)
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid action specified.'
                })
                
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'POST request required.'
    })

def assign_staff_role(request):
    """Assign position_title to a staff member"""
    staff_id = request.POST.get('staff')
    position_title = request.POST.get('position_title', '').strip()
    department_id = request.POST.get('department', '').strip()
    employment_type = request.POST.get('employment_type', '').strip()
    joining_date = request.POST.get('joining_date', '').strip()
    
    if not staff_id:
        return JsonResponse({
            'success': False,
            'message': 'Staff selection is required.'
        })
    
    if not position_title:
        return JsonResponse({
            'success': False,
            'message': 'Position selection is required.'
        })
    
    try:
        staff = Staffs.objects.get(id=staff_id)
    except Staffs.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Staff member not found.'
        })
    
    # Validate position_title
    valid_roles = [r[0] for r in ROLE_CHOICES]
    if position_title not in valid_roles:
        return JsonResponse({
            'success': False,
            'message': 'Invalid position specified.'
        })
    
    try:
        # Update staff position_title
        staff.position_title = position_title
        
        # Update department if provided
        if department_id:
            try:
                department = Department.objects.get(id=department_id)
                staff.department = department
            except Department.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Department not found.'
                })
        else:
            staff.department = None
        
        # Update employment type if provided
        if employment_type:
            staff.employment_type = employment_type
        
        # Update joining date if provided
        if joining_date:
            try:
                staff.joining_date = joining_date
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid joining date format.'
                })
        
        staff.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Position "{position_title}" assigned to {staff.get_full_name()} successfully.',
            'staff_id': staff.id,
            'position_title': staff.position_title,
            'department_name': staff.department.name if staff.department else None,
            'department_id': staff.department.id if staff.department else None,
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error assigning position: {str(e)}'
        })

def bulk_assign_roles(request):
    """Assign same position_title to multiple staff members"""
    staff_ids = request.POST.getlist('staff_list[]')
    position_title = request.POST.get('position_title', '').strip()
    department_id = request.POST.get('department', '').strip()
    
    if not staff_ids:
        return JsonResponse({
            'success': False,
            'message': 'No staff members selected.'
        })
    
    if not position_title:
        return JsonResponse({
            'success': False,
            'message': 'Position selection is required.'
        })
    
    # Validate position_title
    valid_roles = [r[0] for r in ROLE_CHOICES]
    if position_title not in valid_roles:
        return JsonResponse({
            'success': False,
            'message': 'Invalid position specified.'
        })
    
    # Get department if provided
    department = None
    if department_id:
        try:
            department = Department.objects.get(id=department_id)
        except Department.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Department not found.'
            })
    
    try:
        updated_count = 0
        failed_updates = []
        
        for staff_id in staff_ids:
            try:
                staff = Staffs.objects.get(id=staff_id)
                staff.position_title = position_title
                if department:
                    staff.department = department
                staff.save()
                updated_count += 1
            except Staffs.DoesNotExist:
                failed_updates.append(f"Staff ID {staff_id} not found")
            except Exception as e:
                failed_updates.append(f"Staff ID {staff_id}: {str(e)}")
        
        message = f'Position "{position_title}" assigned to {updated_count} staff member(s) successfully.'
        if failed_updates:
            message += f' Failed: {", ".join(failed_updates)}'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'updated_count': updated_count,
            'failed_count': len(failed_updates)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error bulk assigning positions: {str(e)}'
        })

def edit_staff_role(request):
    """Edit staff position_title"""
    staff_id = request.POST.get('staff_id')
    position_title = request.POST.get('position_title', '').strip()
    department_id = request.POST.get('department', '').strip()
    employment_type = request.POST.get('employment_type', '').strip()
    joining_date = request.POST.get('joining_date', '').strip()
    
    if not staff_id:
        return JsonResponse({
            'success': False,
            'message': 'Staff ID is required.'
        })
    
    try:
        staff = Staffs.objects.get(id=staff_id)
    except Staffs.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Staff member not found.'
        })
    
    # If position_title is provided, validate it
    if position_title:
        valid_roles = [r[0] for r in ROLE_CHOICES]
        if position_title not in valid_roles:
            return JsonResponse({
                'success': False,
                'message': 'Invalid position specified.'
            })
    
    try:
        # Update position_title if provided
        if position_title:
            staff.position_title = position_title
        
        # Update department if provided (empty string clears the department)
        if department_id is not None:
            if department_id == '':
                staff.department = None
            else:
                try:
                    department = Department.objects.get(id=department_id)
                    staff.department = department
                except Department.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': 'Department not found.'
                    })
        
        # Update employment type if provided
        if employment_type:
            staff.employment_type = employment_type
        
        # Update joining date if provided
        if joining_date:
            if joining_date.strip():
                try:
                    staff.joining_date = joining_date
                except ValueError:
                    return JsonResponse({
                        'success': False,
                        'message': 'Invalid joining date format.'
                    })
            else:
                staff.joining_date = None
        
        staff.save()
        
        action = 'updated' if position_title else 'cleared'
        return JsonResponse({
            'success': True,
            'message': f'Position {action} for {staff.get_full_name()} successfully.',
            'staff_id': staff.id,
            'position_title': staff.position_title,
            'department_name': staff.department.name if staff.department else None,
            'department_id': staff.department.id if staff.department else None,
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating position: {str(e)}'
        })

def remove_staff_role(request):
    """Remove position_title from staff member"""
    staff_id = request.POST.get('staff_id')
    
    if not staff_id:
        return JsonResponse({
            'success': False,
            'message': 'Staff ID is required.'
        })
    
    try:
        staff = Staffs.objects.get(id=staff_id)
    except Staffs.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Staff member not found.'
        })
    
    try:
        # Clear the position_title and department
        previous_position = staff.position_title
        previous_department = staff.department.name if staff.department else None
        
        staff.position_title = ''
        staff.department = None
        staff.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Position removed from {staff.get_full_name()} successfully.',
            'staff_id': staff.id,
            'position_title': staff.position_title,
            'department_name': None,
            'department_id': None,
            'previous_position': previous_position,
            'previous_department': previous_department
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error removing position: {str(e)}'
        })
    

@login_required
def teaching_assignments_list(request):
    """Display teaching assignments management page"""
    # Get current academic year
    current_academic_year = AcademicYear.objects.filter(is_active=True).first()
    academic_year_id = request.GET.get('academic_year')
    
    if academic_year_id:
        try:
            current_academic_year = AcademicYear.objects.get(id=academic_year_id)
        except AcademicYear.DoesNotExist:
            current_academic_year = AcademicYear.objects.filter(is_active=True).first()
    
    # Get assignments for current academic year
    assignments = TeachingAssignment.objects.filter(
        academic_year=current_academic_year
    ).select_related(
        'staff', 'staff__admin', 'staff__department',
        'subject', 'subject__educational_level',
        'class_level', 'class_level__educational_level',
        'stream_class', 'academic_year'
    ).order_by('class_level__order', 'staff__admin__first_name')
    
    # Get all academic years for dropdown
    academic_years = AcademicYear.objects.all().order_by('-start_date')
    
    # Get data for forms
    all_staff = Staffs.objects.select_related('admin', 'department').order_by('admin__first_name')
    class_levels = ClassLevel.objects.filter(is_active=True).select_related('educational_level').order_by('order')
    subjects = Subject.objects.filter(is_active=True).select_related('educational_level').order_by('name')
    
    context = {
        'assignments': assignments,
        'current_academic_year': current_academic_year,
        'academic_years': academic_years,
        'all_staff': all_staff,
        'class_levels': class_levels,
        'subjects': subjects,
    }
    
    return render(request, 'admin/staff/teaching_assignments.html', context)


@login_required
@require_http_methods(["GET"])
def get_assignment_details(request):
    """Get assignment details for editing"""
    assignment_id = request.GET.get('assignment_id')
    
    try:
        assignment = TeachingAssignment.objects.select_related(
            'staff', 'subject', 'class_level', 'stream_class', 'academic_year'
        ).get(id=assignment_id)
        
        # Get all staff for the dropdown
        all_staff = Staffs.objects.select_related('admin', 'department').order_by('admin__first_name')
        
        # Get all active class levels
        class_levels = ClassLevel.objects.filter(is_active=True).order_by('order')
        
        # Get subjects for the current class level's educational level
        if assignment.class_level:
            subjects = Subject.objects.filter(
                educational_level=assignment.class_level.educational_level,
                is_active=True
            ).order_by('name')
        else:
            subjects = Subject.objects.filter(is_active=True).order_by('name')
        
        # Get streams for the current class level
        if assignment.class_level:
            streams = StreamClass.objects.filter(
                class_level=assignment.class_level, 
                is_active=True
            ).order_by('stream_letter')
        else:
            streams = StreamClass.objects.none()
        
        html = render_to_string('admin/staff/edit_assignment_form.html', {
            'assignment': assignment,
            'all_staff': all_staff,
            'class_levels': class_levels,
            'subjects': subjects,
            'streams': streams,
        })
        
        return JsonResponse({'success': True, 'html': html})
        
    except TeachingAssignment.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Assignment not found.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})



@login_required
def department_management(request):
    """
    Main view for department management
    """
    # Get all departments with HOD info
    departments = Department.objects.select_related('head_of_department__admin').all()
    
    # Get statistics
    total_departments = departments.count()
    active_departments = departments.filter(is_active=True).count()
    inactive_departments = total_departments - active_departments
    departments_with_hod = departments.filter(head_of_department__isnull=False).count()
    
    # Get HOD candidates (active staff members who are not already HODs)
    hod_candidates = Staffs.objects.filter(
        admin__is_active=True
    ).select_related('admin').order_by('admin__first_name')
    
    context = {
        'departments': departments,
        'total_departments': total_departments,
        'active_departments': active_departments,
        'inactive_departments': inactive_departments,
        'departments_with_hod': departments_with_hod,
        'hod_candidates': hod_candidates,
        'page_title': 'Department Management',
    }
    
    return render(request, 'admin/staff/department_management.html', context)

@login_required
def departments_crud(request):
    """
    AJAX view for handling all CRUD operations for departments
    """
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        action = request.POST.get('action')
        
        if action == 'create':
            return create_department(request)
        elif action == 'update':
            return update_department(request)
        elif action == 'toggle_status':
            return toggle_department_status(request)
        elif action == 'delete':
            return delete_department(request)
        elif action == 'bulk_delete':
            return bulk_delete_departments(request)
        elif action == 'bulk_toggle_status':
            return bulk_toggle_departments_status(request)
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method or action.'
    })

def create_department(request):
    """
    Create a new department
    """
    try:
        # Get form data
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip().upper()
        description = request.POST.get('description', '').strip()
        hod_id = request.POST.get('head_of_department', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        
        # Validate required fields
        if not name:
            return JsonResponse({
                'success': False,
                'message': 'Department name is required.'
            })
        
        if not code:
            return JsonResponse({
                'success': False,
                'message': 'Department code is required.'
            })
        
        # Check for duplicate name
        if Department.objects.filter(name__iexact=name).exists():
            return JsonResponse({
                'success': False,
                'message': f'A department with name "{name}" already exists.'
            })
        
        # Check for duplicate code
        if Department.objects.filter(code__iexact=code).exists():
            return JsonResponse({
                'success': False,
                'message': f'A department with code "{code}" already exists.'
            })
        
        # Get HOD if provided
        head_of_department = None
        if hod_id:
            try:
                head_of_department = Staffs.objects.get(id=hod_id, admin__is_active=True)
            except Staffs.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Selected HOD not found or is inactive.'
                })
        
        # Create department
        department = Department.objects.create(
            name=name,
            code=code,
            description=description,
            head_of_department=head_of_department,
            is_active=is_active
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Department "{department.name}" has been created successfully.',
            'department_id': department.id
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error creating department: {str(e)}'
        })

def update_department(request):
    """
    Update an existing department
    """
    try:
        department_id = request.POST.get('id')
        
        if not department_id:
            return JsonResponse({
                'success': False,
                'message': 'Department ID is required.'
            })
        
        department = get_object_or_404(Department, id=department_id)
        
        # Get form data
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip().upper()
        description = request.POST.get('description', '').strip()
        hod_id = request.POST.get('head_of_department', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        
        # Validate required fields
        if not name:
            return JsonResponse({
                'success': False,
                'message': 'Department name is required.'
            })
        
        if not code:
            return JsonResponse({
                'success': False,
                'message': 'Department code is required.'
            })
        
        # Check for duplicate name (excluding current department)
        if Department.objects.filter(name__iexact=name).exclude(id=department_id).exists():
            return JsonResponse({
                'success': False,
                'message': f'A department with name "{name}" already exists.'
            })
        
        # Check for duplicate code (excluding current department)
        if Department.objects.filter(code__iexact=code).exclude(id=department_id).exists():
            return JsonResponse({
                'success': False,
                'message': f'A department with code "{code}" already exists.'
            })
        
        # Get HOD if provided
        head_of_department = None
        if hod_id:
            try:
                head_of_department = Staffs.objects.get(id=hod_id, admin__is_active=True)
            except Staffs.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Selected HOD not found or is inactive.'
                })
        
        # Update department
        department.name = name
        department.code = code
        department.description = description
        department.head_of_department = head_of_department
        department.is_active = is_active
        department.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Department "{department.name}" has been updated successfully.',
            'department_id': department.id
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating department: {str(e)}'
        })

def toggle_department_status(request):
    """
    Toggle department active status
    """
    try:
        department_id = request.POST.get('id')
        
        if not department_id:
            return JsonResponse({
                'success': False,
                'message': 'Department ID is required.'
            })
        
        department = get_object_or_404(Department, id=department_id)
        
        # Toggle status
        department.is_active = not department.is_active
        department.save()
        
        status_text = "activated" if department.is_active else "deactivated"
        
        return JsonResponse({
            'success': True,
            'message': f'Department "{department.name}" has been {status_text}.',
            'is_active': department.is_active
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error toggling department status: {str(e)}'
        })

def delete_department(request):
    """
    Delete a department
    """
    try:
        department_id = request.POST.get('id')
        
        if not department_id:
            return JsonResponse({
                'success': False,
                'message': 'Department ID is required.'
            })
        
        department = get_object_or_404(Department, id=department_id)
        department_name = department.name
        
        # Check if department has any staff assigned
        # You might want to add additional checks here based on your requirements
        
        # Delete department
        department.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Department "{department_name}" has been deleted successfully.'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting department: {str(e)}'
        })

def bulk_delete_departments(request):
    """
    Bulk delete multiple departments
    """
    try:
        department_ids = request.POST.getlist('department_ids[]')
        
        if not department_ids:
            return JsonResponse({
                'success': False,
                'message': 'No departments selected.'
            })
        
        departments = Department.objects.filter(id__in=department_ids)
        deleted_count = departments.count()
        department_names = list(departments.values_list('name', flat=True))
        
        if deleted_count == 0:
            return JsonResponse({
                'success': False,
                'message': 'No valid departments found to delete.'
            })
        
        # Delete departments
        departments.delete()
        
        message = f'Successfully deleted {deleted_count} department(s).'
        if deleted_count <= 5:
            names_str = ', '.join(department_names)
            message = f'Successfully deleted: {names_str}'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error bulk deleting departments: {str(e)}'
        })

def bulk_toggle_departments_status(request):
    """
    Bulk toggle status for multiple departments
    """
    try:
        department_ids = request.POST.getlist('department_ids[]')
        status_action = request.POST.get('status_action', 'activate')  # 'activate' or 'deactivate'
        
        if not department_ids:
            return JsonResponse({
                'success': False,
                'message': 'No departments selected.'
            })
        
        departments = Department.objects.filter(id__in=department_ids)
        updated_count = departments.count()
        
        if updated_count == 0:
            return JsonResponse({
                'success': False,
                'message': 'No valid departments found.'
            })
        
        # Update status based on action
        new_status = status_action == 'activate'
        departments.update(is_active=new_status)
        
        status_text = "activated" if new_status else "deactivated"
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully {status_text} {updated_count} department(s).',
            'status': new_status
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error bulk updating departments: {str(e)}'
        })

@login_required
def view_department(request, department_id):
    """
    View department details
    """
    department = get_object_or_404(Department, id=department_id)
    
    # Get staff in this department (if you have a relationship)
    # staff_in_department = Staffs.objects.filter(department=department)
    
    context = {
        'department': department,
        # 'staff_in_department': staff_in_department,
        'page_title': f'{department.name} - Department Details',
    }
    
    return render(request, 'admin/staff/view_department.html', context)

@login_required
def assign_staff_to_department(request, department_id):
    """
    Assign staff to department (if needed)
    """
    if request.method == 'POST':
        department = get_object_or_404(Department, id=department_id)
        staff_ids = request.POST.getlist('staff_ids[]')
        
        try:
            # Update staff department assignments
            # This depends on your Staffs model structure
            # Example: Staffs.objects.filter(id__in=staff_ids).update(department=department)
            
            return JsonResponse({
                'success': True,
                'message': f'Staff assigned to {department.name} successfully.'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error assigning staff: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    })
    

@login_required
def department_staff_assignment(request, department_id):
    """
    View to manage staff assignment in a specific department
    """

    department = get_object_or_404(
        Department.objects.select_related('head_of_department__admin'),
        id=department_id
    )
    role_choices = ROLE_CHOICES
    # Staff already assigned to this department
    staff_list = Staffs.objects.filter(
        department=department,
        admin__is_active=True
    ).select_related(
        'admin', 'department'
    ).order_by(
        'admin__first_name', 'admin__last_name'
    )

    # Staff available for assignment (not assigned to ANY department)
    available_staff = Staffs.objects.filter(
        admin__is_active=True,
        department__isnull=True
    ).select_related(
        'admin'
    ).order_by(
        'admin__first_name', 'admin__last_name'
    )

    # Counts
    total_staff_in_department = staff_list.count()
    available_staff_count = available_staff.count()

    # HOD info
    hod = department.head_of_department
    has_hod = hod is not None

    context = {
        'department': department,
        'role_choices': role_choices,
        'staff_list': staff_list,
        'available_staff': available_staff,
        'total_staff_in_department': total_staff_in_department,
        'available_staff_count': available_staff_count,
        'has_hod': has_hod,
        'hod_name': hod.get_full_name() if has_hod else None,
        'page_title': f'{department.name} Department - Staff Assignment',
        'breadcrumb_title': f'Staff in {department.name}',
    }

    return render(
        request,
        'admin/staff/staff_department_assignment.html',
        context
    )


@login_required
def add_staff_to_department(request, department_id):
    """
    AJAX view to add staff to a department
    """
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            # Get staff IDs from form data
            staff_ids = request.POST.getlist('staff_ids[]')
            
            if not staff_ids:
                return JsonResponse({
                    'success': False,
                    'message': 'No staff selected.'
                })
            
            department = get_object_or_404(Department, id=department_id, is_active=True)
            added_count = 0
            failed_staff = []
            
            for staff_id in staff_ids:
                try:
                    staff = Staffs.objects.get(id=staff_id, admin__is_active=True)
                    
                    # Check if staff is already in a department
                    if staff.department:
                        failed_staff.append(f"{staff.get_full_name()} (Already in a department)")
                        continue
                    
                    # Add staff to department
                    staff.department = department
                    staff.save()
                    added_count += 1
                    
                except Staffs.DoesNotExist:
                    failed_staff.append(f"Staff ID {staff_id} (Not found)")
                    continue
            
            message = f"Successfully added {added_count} staff member(s) to the department."
            if failed_staff:
                message += f" Failed to add {len(failed_staff)} staff member(s)."
            
            # Update counts
            total_staff_in_department = Staffs.objects.filter(department=department, admin__is_active=True).count()
            
            return JsonResponse({
                'success': True,
                'message': message,
                'added_count': added_count,
                'failed_count': len(failed_staff),
                'total_staff': total_staff_in_department
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error adding staff: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    })

@login_required
def remove_staff_from_department(request, department_id):
    """
    AJAX view to remove a staff from a department
    """
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            # Try to parse as JSON first
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                staff_id = data.get('staff_id')
            else:
                # Fall back to form data
                staff_id = request.POST.get('staff_id')
            
            if not staff_id:
                return JsonResponse({
                    'success': False,
                    'message': 'Staff ID is required.'
                })
            
            # Get staff and department
            staff = get_object_or_404(Staffs, id=staff_id, admin__is_active=True)
            department = get_object_or_404(Department, id=department_id)
            
            # Verify staff is in this department
            if staff.department != department:
                return JsonResponse({
                    'success': False,
                    'message': 'Staff is not in this department.'
                })
            
            # Check if staff is HOD of this department
            if department.head_of_department == staff:
                # Remove HOD assignment
                department.head_of_department = None
                department.save()
            
            # Remove staff from department
            staff.department = None
            staff.save()
            
            # Update counts
            total_staff_in_department = Staffs.objects.filter(department=department, admin__is_active=True).count()
            
            return JsonResponse({
                'success': True,
                'message': f'{staff.get_full_name()} has been removed from the department.',
                'total_staff': total_staff_in_department,
                'staff_id': staff_id
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid request data.'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error removing staff: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    })

@login_required
def bulk_remove_staff_from_department(request, department_id):
    """
    AJAX view to bulk remove multiple staff from a department
    """
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            # Get staff IDs from form data
            staff_ids = request.POST.getlist('staff_ids[]')
            
            if not staff_ids:
                return JsonResponse({
                    'success': False,
                    'message': 'No staff selected.'
                })
            
            department = get_object_or_404(Department, id=department_id)
            removed_count = 0
            failed_staff = []
            
            # Prepare response data
            removed_staff_names = []
            
            for staff_id in staff_ids:
                try:
                    staff = Staffs.objects.get(id=staff_id, admin__is_active=True)
                    
                    # Verify staff is in this department
                    if staff.department != department:
                        failed_staff.append(f"{staff.get_full_name()} (Not in this department)")
                        continue
                    
                    # Check if staff is HOD of this department
                    if department.head_of_department == staff:
                        # Remove HOD assignment
                        department.head_of_department = None
                        department.save()
                    
                    # Remove staff from department
                    staff.department = None
                    staff.save()
                    
                    removed_count += 1
                    removed_staff_names.append(staff.get_full_name())
                    
                except Staffs.DoesNotExist:
                    failed_staff.append(f"Staff ID {staff_id} (Not found)")
                    continue
                except Exception as e:
                    failed_staff.append(f"{staff_id} (Error: {str(e)})")
                    continue
            
            # Update counts after all removals
            total_staff_in_department = Staffs.objects.filter(department=department, admin__is_active=True).count()
            
            # Prepare success message
            if removed_count > 0:
                if removed_count <= 3:
                    # Show individual names for small removals
                    staff_names_str = ', '.join(removed_staff_names)
                    message = f"Successfully removed {staff_names_str} from the department."
                else:
                    # Generic message for larger removals
                    message = f"Successfully removed {removed_count} staff members from the department."
                
                if failed_staff:
                    message += f" Failed to remove {len(failed_staff)} staff member(s)."
            else:
                message = "No staff members were removed from the department."
            
            return JsonResponse({
                'success': True,
                'message': message,
                'removed_count': removed_count,
                'failed_count': len(failed_staff),
                'total_staff': total_staff_in_department
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error removing staff: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    })


@login_required
@require_http_methods(["GET"])
def get_streams_for_class(request):
    """Get streams for a specific class level"""
    class_level_id = request.GET.get('class_level_id')
    
    try:
        streams = StreamClass.objects.filter(
            class_level_id=class_level_id,
            is_active=True
        ).order_by('stream_letter')
        
        stream_list = [{'id': s.id, 'name': str(s)} for s in streams]
        
        return JsonResponse({'success': True, 'streams': stream_list})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@require_http_methods(["POST"])
def teaching_assignments_crud(request):
    """Handle AJAX CRUD operations for teaching assignments"""
    action = request.POST.get('action', '').lower()
    
    try:
        if action == 'create_assignment':
            return create_teaching_assignment(request)
        elif action == 'toggle_assignment':
            return toggle_assignment_status(request)
        elif action == 'delete_assignment':
            return delete_teaching_assignment(request)        
        else:
            return JsonResponse({
                'success': False,
                'message': 'Invalid action specified.'
            })
            
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })

def create_teaching_assignment(request):
    """Create a new teaching assignment"""
    staff_id = request.POST.get('staff')
    subject_id = request.POST.get('subject')
    class_level_id = request.POST.get('class_level')
    stream_class_id = request.POST.get('stream_class')
    academic_year_id = request.POST.get('academic_year')
    assignment_type = request.POST.get('assignment_type')
    is_class_teacher = request.POST.get('is_class_teacher') == 'on'
    period_count = request.POST.get('period_count', 0)
    start_date = request.POST.get('start_date')
    
    # Validation
    if not staff_id or not class_level_id or not academic_year_id:
        return JsonResponse({
            'success': False,
            'message': 'Staff, class level, and academic year are required.'
        })
    
    if not is_class_teacher and not subject_id:
        return JsonResponse({
            'success': False,
            'message': 'Subject is required for non-class teacher assignments.'
        })
    
    try:
        # Get objects
        staff = Staffs.objects.get(id=staff_id)
        academic_year = AcademicYear.objects.get(id=academic_year_id)
        class_level = ClassLevel.objects.get(id=class_level_id)
        
        subject = None
        if subject_id and not is_class_teacher:
            subject = Subject.objects.get(id=subject_id)
        
        stream_class = None
        if stream_class_id:
            stream_class = StreamClass.objects.get(id=stream_class_id)
        
        # Check for duplicate assignment
        duplicate_check = TeachingAssignment.objects.filter(
            staff=staff,
            academic_year=academic_year,
            class_level=class_level,
            stream_class=stream_class,
            subject=subject,
            is_class_teacher=is_class_teacher
        ).exists()
        
        if duplicate_check:
            return JsonResponse({
                'success': False,
                'message': 'A similar assignment already exists for this teacher.'
            })
        
        # Create assignment
        assignment = TeachingAssignment(
            staff=staff,
            subject=subject,
            class_level=class_level,
            stream_class=stream_class,
            academic_year=academic_year,
            assignment_type=assignment_type,
            is_class_teacher=is_class_teacher,
            period_count=period_count,
            is_active=True
        )
        
        if start_date:
            assignment.start_date = start_date
        
        assignment.clean()  # Run validation
        assignment.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Teaching assignment created successfully.',
            'assignment_id': assignment.id
        })
        
    except Staffs.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Staff not found.'})
    except AcademicYear.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Academic year not found.'})
    except ClassLevel.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Class level not found.'})
    except Subject.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Subject not found.'})
    except StreamClass.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Stream class not found.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})



def toggle_assignment_status(request):
    """Toggle assignment active status"""
    assignment_id = request.POST.get('assignment_id')
    
    try:
        assignment = TeachingAssignment.objects.get(id=assignment_id)
        assignment.is_active = not assignment.is_active
        assignment.save()
        
        status = 'activated' if assignment.is_active else 'deactivated'
        
        return JsonResponse({
            'success': True,
            'message': f'Assignment {status} successfully.',
            'is_active': assignment.is_active
        })
        
    except TeachingAssignment.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Assignment not found.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

def delete_teaching_assignment(request):
    """Delete a teaching assignment"""
    assignment_id = request.POST.get('assignment_id')
    
    try:
        assignment = TeachingAssignment.objects.get(id=assignment_id)
        staff_name = assignment.staff.get_full_name()
        assignment.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Assignment for {staff_name} deleted successfully.'
        })
        
    except TeachingAssignment.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Assignment not found.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})



# ============================================================================
# AJAX/API ENDPOINTS
# ============================================================================

@login_required
def ajax_get_streams(request):
    """AJAX endpoint to get streams for a class level"""
    class_level_id = request.GET.get('class_level_id')
    
    if class_level_id:
        streams = StreamClass.objects.filter(
            class_level_id=class_level_id,
            is_active=True
        ).values('id', 'stream_letter')
        
        return JsonResponse(list(streams), safe=False)
    
    return JsonResponse([], safe=False)

@login_required
def ajax_get_student_details(request):
    """AJAX endpoint to get student details"""
    student_id = request.GET.get('student_id')
    
    if student_id:
        student = get_object_or_404(Student, id=student_id)
        data = {
            'id': student.id,
            'full_name': student.full_name,
            'registration_number': student.registration_number,
            'class_level': student.class_level.name if student.class_level else '',
            'stream_class': student.stream_class.stream_letter if student.stream_class else '',
            'status': student.status,
            'date_of_birth': student.date_of_birth.strftime('%Y-%m-%d') if student.date_of_birth else '',
            'gender': student.get_gender_display(),
        }
        return JsonResponse(data)
    
    return JsonResponse({'error': 'Student ID required'})




@login_required
def combinations_list(request):
    """
    Display combinations management page
    """
    # Get only A-Level educational level
    a_level = EducationalLevel.objects.filter(code='A_LEVEL').first()
    
    # Get combinations with their subjects
    combinations = Combination.objects.filter(
        educational_level=a_level
    ).prefetch_related(
        'subjects',
        'combinationsubject_set__subject'
    ).order_by('code')
    
    # Get all A-Level subjects
    a_level_subjects = Subject.objects.filter(
        educational_level=a_level,
        is_active=True
    ).order_by('name')
    
    # Get subject count statistics
    total_combinations = combinations.count()
    active_combinations = combinations.filter(is_active=True).count()
    
    # Get combination subjects grouped by role
    combination_subjects_data = {}
    for combination in combinations:
        subjects = CombinationSubject.objects.filter(
            combination=combination
        ).select_related('subject')
        
        core_subjects = subjects.filter(role='CORE').values_list('subject__name', flat=True)
        subsidiary_subjects = subjects.filter(role='SUB').values_list('subject__name', flat=True)
        
        combination_subjects_data[combination.id] = {
            'core': list(core_subjects),
            'subsidiary': list(subsidiary_subjects),
            'total_subjects': subjects.count()
        }
    
    context = {
        'combinations': combinations,
        'a_level_subjects': a_level_subjects,
        'total_combinations': total_combinations,
        'active_combinations': active_combinations,
        'combination_subjects_data': combination_subjects_data,
        'subject_role_choices': CombinationSubject.SUBJECT_ROLE_CHOICES,
        'page_title': 'Subject Combinations Management',
    }
    
    return render(request, 'admin/academic/combinations_list.html', context)


@login_required
def combinations_crud(request):
    """
    Handle AJAX CRUD operations for combinations
    """
    if request.method == 'POST':
        action = request.POST.get('action', '').lower()
        
        try:
            if action == 'create':
                return create_combination(request)
            elif action == 'update':
                return update_combination(request)
            elif action == 'toggle_status':
                return toggle_combination_status(request)
            elif action == 'delete':
                return delete_combination(request)
            elif action == 'add_subject':
                return add_subject_to_combination(request)
            elif action == 'remove_subject':
                return remove_subject_from_combination(request)
            elif action == 'update_subject_role':
                return update_subject_role(request)
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid action specified.'
                })
                
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            })
    
    # Handle GET requests
    elif request.method == 'GET':
        action = request.GET.get('action', '')
        
        if action == 'get_combination_details':
            return get_combination_details(request)
        elif action == 'get_combination_subjects':
            return get_combination_subjects(request)
        elif action == 'get_available_subjects':
            return get_available_subjects(request)
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    })


# Update the create_combination function
def create_combination(request):
    """Create a new combination"""
    try:
        # Get A-Level educational level
        a_level = EducationalLevel.objects.filter(code='A_LEVEL').first()
        if not a_level:
            return JsonResponse({
                'success': False,
                'message': 'A-Level educational level not found. Please create it first.'
            })
        
        # Validate required fields
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip().upper()
        
        if not name or not code:
            return JsonResponse({
                'success': False,
                'message': 'Name and code are required.'
            })
        
        # Validate name and code length
        if len(name) > 100:
            return JsonResponse({
                'success': False,
                'message': 'Name cannot exceed 100 characters.'
            })
        
        if len(code) > 10:
            return JsonResponse({
                'success': False,
                'message': 'Code cannot exceed 10 characters.'
            })
        
        # Check for duplicate code
        if Combination.objects.filter(code__iexact=code).exists():
            return JsonResponse({
                'success': False,
                'message': f'A combination with code "{code}" already exists.'
            })
        
        # Check for duplicate name
        if Combination.objects.filter(name__iexact=name).exists():
            return JsonResponse({
                'success': False,
                'message': f'A combination with name "{name}" already exists.'
            })
        
        # Get subjects from form
        subject_ids = request.POST.getlist('subjects[]')
        subject_roles = request.POST.getlist('subject_roles[]')
        
        # Validate subjects requirements
        if not subject_ids:
            return JsonResponse({
                'success': False,
                'message': 'At least one subject is required for a combination.'
            })
        
        # Count core subjects
        core_subjects_count = 0
        for i, subject_id in enumerate(subject_ids):
            if i < len(subject_roles) and subject_roles[i] == 'CORE':
                core_subjects_count += 1
        
        # Validate core subjects requirements
        if core_subjects_count < 2:
            return JsonResponse({
                'success': False,
                'message': 'A combination must have at least 2 core subjects.'
            })
        
        if core_subjects_count > 3:
            return JsonResponse({
                'success': False,
                'message': 'A combination cannot have more than 3 core subjects.'
            })
        
        # Validate total subjects (2-3 subjects total for combination name)
        if len(subject_ids) < 2:
            return JsonResponse({
                'success': False,
                'message': 'A combination must have at least 2 subjects.'
            })
        
        if len(subject_ids) > 6:
            return JsonResponse({
                'success': False,
                'message': 'A combination cannot have more than 6 subjects.'
            })
        
        # Get optional fields
        is_active = request.POST.get('is_active') == 'on' or request.POST.get('is_active') == 'true'
        
        with transaction.atomic():
            # Create the combination
            combination = Combination.objects.create(
                educational_level=a_level,
                name=name,
                code=code,
                is_active=is_active
            )
            
            if subject_ids:
                # Validate each subject
                for i, subject_id in enumerate(subject_ids):
                    try:
                        subject = Subject.objects.get(
                            id=subject_id,
                            educational_level=a_level,
                            is_active=True
                        )
                        
                        role = subject_roles[i] if i < len(subject_roles) else 'CORE'
                        
                        # Validate role
                        if role not in ['CORE', 'SUB']:
                            role = 'CORE'
                        
                        # Create combination subject
                        CombinationSubject.objects.create(
                            combination=combination,
                            subject=subject,
                            role=role
                        )
                        
                    except Subject.DoesNotExist:
                        continue
            
            return JsonResponse({
                'success': True,
                'message': f'Combination "{name}" created successfully.',
                'combination': {
                    'id': combination.id,
                    'name': combination.name,
                    'code': combination.code,
                    'is_active': combination.is_active,
                    'subject_count': combination.subjects.count()
                }
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error creating combination: {str(e)}'
        })


def update_combination(request):
    """Update an existing combination"""
    try:
        combination_id = request.POST.get('id')
        if not combination_id:
            return JsonResponse({
                'success': False,
                'message': 'Combination ID is required.'
            })
        
        combination = get_object_or_404(Combination, id=combination_id)
        
        # Get and validate required fields
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip().upper()
        
        if not name or not code:
            return JsonResponse({
                'success': False,
                'message': 'Name and code are required.'
            })
        
        # Validate name and code length
        if len(name) > 50:
            return JsonResponse({
                'success': False,
                'message': 'Name cannot exceed 50 characters.'
            })
        
        if len(code) > 10:
            return JsonResponse({
                'success': False,
                'message': 'Code cannot exceed 10 characters.'
            })
        
        # Check for duplicate code (excluding current)
        if Combination.objects.filter(code__iexact=code).exclude(id=combination.id).exists():
            return JsonResponse({
                'success': False,
                'message': f'A combination with code "{code}" already exists.'
            })
        
        # Check for duplicate name (excluding current)
        if Combination.objects.filter(name__iexact=name).exclude(id=combination.id).exists():
            return JsonResponse({
                'success': False,
                'message': f'A combination with name "{name}" already exists.'
            })
        
        # Get optional fields
        is_active = request.POST.get('is_active') == 'on' or request.POST.get('is_active') == 'true'
        
        with transaction.atomic():
            # Update the combination
            combination.name = name
            combination.code = code
            combination.is_active = is_active
            combination.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Combination "{name}" updated successfully.',
                'combination': {
                    'id': combination.id,
                    'name': combination.name,
                    'code': combination.code,
                    'is_active': combination.is_active
                }
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating combination: {str(e)}'
        })


def toggle_combination_status(request):
    """Toggle combination active status"""
    try:
        combination_id = request.POST.get('id')
        if not combination_id:
            return JsonResponse({
                'success': False,
                'message': 'Combination ID is required.'
            })
        
        combination = get_object_or_404(Combination, id=combination_id)
        
        # Toggle the status
        combination.is_active = not combination.is_active
        combination.save()
        
        status_text = "activated" if combination.is_active else "deactivated"
        
        return JsonResponse({
            'success': True,
            'message': f'Combination "{combination.name}" {status_text} successfully.',
            'is_active': combination.is_active
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error toggling combination status: {str(e)}'
        })


def delete_combination(request):
    """Delete a combination"""
    try:
        combination_id = request.POST.get('id')
        if not combination_id:
            return JsonResponse({
                'success': False,
                'message': 'Combination ID is required.'
            })
        
        combination = get_object_or_404(Combination, id=combination_id)
        combination_name = combination.name
        
        # Check if combination has any associated students
        # (Add this check if you have a relationship with students)
        if combination.student_set.exists():
            return JsonResponse({
                'success': False,
                'message': f'Cannot delete combination "{combination_name}". It has associated students.'
                })
            
        combination.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Combination "{combination_name}" deleted successfully.'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting combination: {str(e)}'
        })



# Update the add_subject_to_combination function
def add_subject_to_combination(request):
    """Add a subject to a combination"""
    try:
        combination_id = request.POST.get('combination_id')
        subject_id = request.POST.get('subject_id')
        role = request.POST.get('role', 'CORE')
        
        if not combination_id or not subject_id:
            return JsonResponse({
                'success': False,
                'message': 'Combination ID and Subject ID are required.'
            })
        
        combination = get_object_or_404(Combination, id=combination_id)
        
        # Get current subjects count
        current_subjects = CombinationSubject.objects.filter(combination=combination)
        core_subjects_count = current_subjects.filter(role='CORE').count()
        total_subjects_count = current_subjects.count()
        
        # Validate core subjects limit
        if role == 'CORE' and core_subjects_count >= 3:
            return JsonResponse({
                'success': False,
                'message': 'Cannot add more than 3 core subjects to a combination.'
            })
        
        # Validate total subjects limit
        if total_subjects_count >= 6:
            return JsonResponse({
                'success': False,
                'message': 'Cannot add more than 6 subjects to a combination.'
            })
        
        # Get A-Level educational level
        a_level = combination.educational_level
        
        # Get subject and validate it belongs to A-Level
        subject = get_object_or_404(
            Subject,
            id=subject_id,
            educational_level=a_level,
            is_active=True
        )
        
        # Validate role
        if role not in ['CORE', 'SUB']:
            role = 'CORE'
        
        # Check if subject is already in combination
        if CombinationSubject.objects.filter(
            combination=combination,
            subject=subject
        ).exists():
            return JsonResponse({
                'success': False,
                'message': f'Subject "{subject.name}" is already in this combination.'
            })
        
        # Create combination subject
        combination_subject = CombinationSubject.objects.create(
            combination=combination,
            subject=subject,
            role=role
        )
        
        # Update combination name to reflect subjects
        update_combination_name(combination)
        
        return JsonResponse({
            'success': True,
            'message': f'Subject "{subject.name}" added to combination successfully.',
            'combination_subject': {
                'id': combination_subject.id,
                'subject_id': subject.id,
                'subject_name': subject.name,
                'subject_code': subject.code,
                'role': role,
                'role_display': combination_subject.get_role_display()
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error adding subject to combination: {str(e)}'
        })



# Update the remove_subject_from_combination function
def remove_subject_from_combination(request):
    """Remove a subject from a combination"""
    try:
        combination_subject_id = request.POST.get('combination_subject_id')
        
        if not combination_subject_id:
            return JsonResponse({
                'success': False,
                'message': 'Combination Subject ID is required.'
            })
        
        combination_subject = get_object_or_404(CombinationSubject, id=combination_subject_id)
        combination = combination_subject.combination
        
        # Check if this is a core subject
        if combination_subject.role == 'CORE':
            # Count remaining core subjects
            remaining_core = CombinationSubject.objects.filter(
                combination=combination,
                role='CORE'
            ).exclude(id=combination_subject_id).count()
            
            # Validate minimum core subjects
            if remaining_core < 2:
                return JsonResponse({
                    'success': False,
                    'message': 'Cannot remove core subject. A combination must have at least 2 core subjects.'
                })
        
        subject_name = combination_subject.subject.name
        combination_name = combination.name
        
        combination_subject.delete()
        
        # Update combination name to reflect subjects
        update_combination_name(combination)
        
        return JsonResponse({
            'success': True,
            'message': f'Subject "{subject_name}" removed from combination "{combination_name}" successfully.'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error removing subject from combination: {str(e)}'
        })



# Update the update_subject_role function
def update_subject_role(request):
    """Update subject role in a combination"""
    try:
        combination_subject_id = request.POST.get('combination_subject_id')
        role = request.POST.get('role', 'CORE')
        
        if not combination_subject_id:
            return JsonResponse({
                'success': False,
                'message': 'Combination Subject ID is required.'
            })
        
        # Validate role
        if role not in ['CORE', 'SUB']:
            return JsonResponse({
                'success': False,
                'message': 'Invalid role specified.'
            })
        
        combination_subject = get_object_or_404(CombinationSubject, id=combination_subject_id)
        combination = combination_subject.combination
        
        # Check if changing from CORE to SUB
        if combination_subject.role == 'CORE' and role == 'SUB':
            # Count remaining core subjects
            remaining_core = CombinationSubject.objects.filter(
                combination=combination,
                role='CORE'
            ).exclude(id=combination_subject_id).count()
            
            # Validate minimum core subjects
            if remaining_core < 2:
                return JsonResponse({
                    'success': False,
                    'message': 'Cannot change role from Core to Subsidiary. A combination must have at least 2 core subjects.'
                })
        
        # Check if changing from SUB to CORE
        if combination_subject.role == 'SUB' and role == 'CORE':
            # Count current core subjects
            current_core = CombinationSubject.objects.filter(
                combination=combination,
                role='CORE'
            ).count()
            
            # Validate maximum core subjects
            if current_core >= 3:
                return JsonResponse({
                    'success': False,
                    'message': 'Cannot add more than 3 core subjects to a combination.'
                })
        
        old_role = combination_subject.role
        combination_subject.role = role
        combination_subject.save()
        
        # Update combination name to reflect subjects
        update_combination_name(combination)
        
        return JsonResponse({
            'success': True,
            'message': f'Subject role updated from {old_role} to {role} successfully.',
            'role': role,
            'role_display': combination_subject.get_role_display()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating subject role: {str(e)}'
        })
    

# Add this new helper function
def update_combination_name(combination):
    """Update combination name based on subjects"""
    subjects = CombinationSubject.objects.filter(
        combination=combination
    ).select_related('subject').order_by('-role', 'subject__name')  # Core first, then subsidiary
    
    if subjects.exists():
        # Get subject names
        subject_names = [cs.subject.name for cs in subjects]
        
        # Create combination name (e.g., "Physics, Chemistry, Mathematics")
        combination_name = ', '.join(subject_names)
        
        # Truncate if too long
        if len(combination_name) > 50:
            combination_name = combination_name[:47] + '...'
        
        # Update combination name
        combination.name = combination_name
        combination.save()

# Helper functions for GET requests
def get_combination_details(request):
    """Get combination details for editing"""
    try:
        combination_id = request.GET.get('combination_id')
        
        if not combination_id:
            return JsonResponse({
                'success': False,
                'message': 'Combination ID is required.'
            })
        
        combination = get_object_or_404(
            Combination.objects.select_related('educational_level'),
            id=combination_id
        )
        
        # Get combination subjects
        subjects = CombinationSubject.objects.filter(
            combination=combination
        ).select_related('subject').order_by('subject__name')
        
        subjects_data = []
        for cs in subjects:
            subjects_data.append({
                'id': cs.id,
                'subject_id': cs.subject.id,
                'subject_name': cs.subject.name,
                'subject_code': cs.subject.code,
                'role': cs.role,
                'role_display': cs.get_role_display()
            })
        
        return JsonResponse({
            'success': True,
            'combination': {
                'id': combination.id,
                'name': combination.name,
                'code': combination.code,
                'is_active': combination.is_active,
                'educational_level': {
                    'id': combination.educational_level.id,
                    'name': combination.educational_level.name
                }
            },
            'subjects': subjects_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error getting combination details: {str(e)}'
        })


def get_combination_subjects(request):
    """Get subjects for a specific combination"""
    try:
        combination_id = request.GET.get('combination_id')
        
        if not combination_id:
            return JsonResponse({
                'success': False,
                'message': 'Combination ID is required.'
            })
        
        combination = get_object_or_404(Combination, id=combination_id)
        
        subjects = CombinationSubject.objects.filter(
            combination=combination
        ).select_related('subject').order_by('subject__name')
        
        subjects_data = []
        for cs in subjects:
            subjects_data.append({
                'id': cs.id,
                'subject_id': cs.subject.id,
                'subject_name': cs.subject.name,
                'subject_code': cs.subject.code,
                'role': cs.role,
                'role_display': cs.get_role_display(),
                'is_compulsory': cs.subject.is_compulsory,
                'is_active': cs.subject.is_active
            })
        
        return JsonResponse({
            'success': True,
            'subjects': subjects_data,
            'count': len(subjects_data)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error getting combination subjects: {str(e)}'
        })


def get_available_subjects(request):
    """Get subjects available for adding to a combination"""
    try:
        combination_id = request.GET.get('combination_id')
        
        if not combination_id:
            return JsonResponse({
                'success': False,
                'message': 'Combination ID is required.'
            })
        
        combination = get_object_or_404(Combination, id=combination_id)
        
        # Get all A-Level subjects
        a_level_subjects = Subject.objects.filter(
            educational_level=combination.educational_level,
            is_active=True
        ).exclude(
            id__in=CombinationSubject.objects.filter(
                combination=combination
            ).values_list('subject_id', flat=True)
        ).order_by('name')
        
        subjects_data = []
        for subject in a_level_subjects:
            subjects_data.append({
                'id': subject.id,
                'name': subject.name,
                'code': subject.code,
                'is_compulsory': subject.is_compulsory,
                'description': subject.description
            })
        
        return JsonResponse({
            'success': True,
            'subjects': subjects_data,
            'count': len(subjects_data)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error getting available subjects: {str(e)}'
        })


# accounts/views/admin_views.py
@login_required
def assign_student_combination(request, student_id):
    """
    View for assigning students to combinations
    """
    # Get student
    student = get_object_or_404(Student, id=student_id)
    
    # Check if student is in A-Level
    if not student.class_level or student.class_level.educational_level.code != 'A_LEVEL':
        messages.error(request, 'Combination assignment is only available for A-Level students.')
        return redirect('admin_student_detail', id=student_id)
    
    # Get A-Level educational level
    a_level = EducationalLevel.objects.filter(code='A_LEVEL').first()
    if not a_level:
        messages.error(request, 'A-Level educational level not found.')
        return redirect('admin_student_detail', id=student_id)
    
    # Get all active combinations for A-Level
    combinations = Combination.objects.filter(
        educational_level=a_level,
        is_active=True
    ).prefetch_related(
        'subjects',
        'combinationsubject_set__subject'
    ).order_by('code')
    
    # Get combination subjects data for display
    combination_subjects_data = {}
    for combination in combinations:
        subjects = CombinationSubject.objects.filter(
            combination=combination
        ).select_related('subject')
        
        core_subjects = subjects.filter(role='CORE').values_list('subject__name', flat=True)
        subsidiary_subjects = subjects.filter(role='SUB').values_list('subject__name', flat=True)
        
        combination_subjects_data[combination.id] = {
            'core': list(core_subjects),
            'subsidiary': list(subsidiary_subjects),
            'total_subjects': subjects.count()
        }
    
    # Get statistics
    active_combinations_count = combinations.filter(is_active=True).count()
    total_combinations_count = combinations.count()
    students_in_same_class = Student.objects.filter(
        class_level=student.class_level,
        status='active'
    ).count()
    
    context = {
        'student': student,
        'combinations': combinations,
        'combination_subjects_data': combination_subjects_data,
        'active_combinations_count': active_combinations_count,
        'total_combinations_count': total_combinations_count,
        'students_in_same_class': students_in_same_class,
        'page_title': f'Assign Combination - {student.full_name}',
    }
    
    return render(request, 'admin/students/assign_combination.html', context)

@login_required
@require_POST
def assign_student_combination_ajax(request, student_id):
    """
    AJAX endpoint for assigning/removing combinations
    """
    student = get_object_or_404(Student, id=student_id)
    action = request.POST.get('action', '').lower()

    try:
        if action == 'assign':
            combination_id = request.POST.get('combination_id')

            if not combination_id:
                return JsonResponse({
                    'success': False,
                    'message': 'Combination ID is required.'
                })

            combination = get_object_or_404(
                Combination,
                id=combination_id,
                is_active=True
            )

            # Check if combination belongs to A-Level
            if combination.educational_level.code != 'A_LEVEL':
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid combination selected.'
                })

            # Assign combination to student
            student.combination = combination
            student.save()

            # Log the action
            SystemLog.objects.create(
                user=request.user,
                log_type='update',
                description=f'Assigned combination {combination.code} to student {student.full_name}',
                ip_address=request.META.get('REMOTE_ADDR')
            )

            return JsonResponse({
                'success': True,
                'message': f'Successfully assigned {student.full_name} to {combination.code}.',
                'combination': {
                    'id': combination.id,
                    'code': combination.code,
                    'name': combination.name
                }
            })

        elif action == 'remove':
            if not student.combination:
                return JsonResponse({
                    'success': False,
                    'message': 'Student has no combination assigned.'
                })

            removed_combination = student.combination
            student.combination = None
            student.save()

            # Log the action
            SystemLog.objects.create(
                user=request.user,
                log_type='update',
                description=f'Removed combination assignment from student {student.full_name}',
                ip_address=request.META.get('REMOTE_ADDR')
            )

            return JsonResponse({
                'success': True,
                'message': f'Successfully removed combination assignment from {student.full_name}.',
                'removed_combination': {
                    'id': removed_combination.id,
                    'code': removed_combination.code
                }
            })

        else:
            return JsonResponse({
                'success': False,
                'message': 'Invalid action specified.'
            })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        })


@login_required
def student_combinations_list(request):
    """
    View for managing student combinations assignments
    """
    # Get A-Level educational level
    a_level = EducationalLevel.objects.filter(code='A_LEVEL').first()
    
    # Get all A-Level students
    a_level_students = Student.objects.filter(
        class_level__educational_level=a_level,
        is_active=True
    ).select_related(
        'class_level', 'stream_class', 'combination'
    ).prefetch_related(
        'optional_subjects',
        'combination__combinationsubject_set__subject'
    ).order_by('class_level__order', 'first_name')
    
    # Get active combinations
    active_combinations = Combination.objects.filter(
        educational_level=a_level,
        is_active=True
    ).prefetch_related('combinationsubject_set__subject').annotate(
        core_count=Count('combinationsubject', filter=Q(combinationsubject__role='CORE')),
        subsidiary_count=Count('combinationsubject', filter=Q(combinationsubject__role='SUB'))
    )
    
    # Get statistics
    total_students = a_level_students.count()
    assigned_students = a_level_students.filter(combination__isnull=False).count()
    unassigned_students = total_students - assigned_students
    
    # Calculate percentage
    assigned_percentage = round((assigned_students / total_students * 100) if total_students > 0 else 0, 1)
    
    # Prepare combination data for template
    for combination in active_combinations:
        combination.subjects_info = json.dumps(list(
            combination.combinationsubject_set.values('subject__name', 'subject__code', 'role')
        ))
    
    # Get eligible students (A-Level without combination)
    eligible_students = a_level_students.filter(combination__isnull=True)
    
    context = {
        'students': a_level_students,
        'active_combinations': active_combinations,
        'eligible_students': eligible_students,
        'total_students': total_students,
        'assigned_count': assigned_students,
        'unassigned_count': unassigned_students,
        'assigned_percentage': assigned_percentage,
        'a_level_students': total_students,
        'page_title': 'Student Combinations Management',
    }
    
    return render(request, 'admin/students/student_combinations_list.html', context)


@login_required
def assign_student_combination(request):
    """
    Handle AJAX operations for assigning combinations to students
    """
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        action = request.POST.get('action', '').lower()
        
        try:
            if action == 'assign':
                return assign_single_combination(request)
            elif action == 'change':
                return change_student_combination(request)
            elif action == 'bulk_assign':
                return bulk_assign_combinations(request)
            elif action == 'remove':
                return remove_combination(request)
            elif action == 'bulk_remove':
                return bulk_remove_combinations(request)
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid action specified.'
                })
                
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    })


def change_student_combination(request):
    """Change a student's existing combination to a new one"""
    student_id = request.POST.get('student_id')
    new_combination_id = request.POST.get('new_combination_id')
    current_combination_id = request.POST.get('current_combination_id')
    
    if not student_id or not new_combination_id:
        return JsonResponse({
            'success': False,
            'message': 'Student ID and New Combination ID are required.'
        })
    
    try:
        student = Student.objects.get(id=student_id, is_active=True)
        new_combination = Combination.objects.get(id=new_combination_id, is_active=True)
        
        # Check if student is A-Level
        a_level = EducationalLevel.objects.filter(code='A_LEVEL').first()
        if not student.class_level or student.class_level.educational_level != a_level:
            return JsonResponse({
                'success': False,
                'message': 'Only A-Level students can have combinations.'
            })
        
        # Check if student has a current combination
        if not student.combination:
            return JsonResponse({
                'success': False,
                'message': f'Student {student.full_name} does not have a current combination to change.'
            })
        
        # Verify current combination matches if provided
        if current_combination_id and student.combination.id != int(current_combination_id):
            return JsonResponse({
                'success': False,
                'message': 'Current combination mismatch. Please refresh the page.'
            })
        
        # Check if new combination is the same as current
        if student.combination.id == new_combination.id:
            return JsonResponse({
                'success': False,
                'message': f'Student already has combination "{new_combination.code}".'
            })
        
        # Store old combination info for the message
        old_combination_code = student.combination.code
        old_combination_name = student.combination.name
        
        # Change the combination
        student.combination = new_combination
        student.save()
        
        # Log the change
        SystemLog.objects.create(
            user=request.user,
            log_type='update',
            description=f'Changed combination for {student.full_name} from {old_combination_code} to {new_combination.code}',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        # Get combination details for UI update
        combination_data = {
            'id': new_combination.id,
            'code': new_combination.code,
            'name': new_combination.name,
            'student_name': student.full_name,
            'old_combination_code': old_combination_code,
            'old_combination_name': old_combination_name,
            'total_subjects': new_combination.combinationsubject_set.count(),
            'core_subjects': list(new_combination.combinationsubject_set.filter(
                role='CORE'
            ).values('subject__name', 'subject__code')),
            'subsidiary_subjects': list(new_combination.combinationsubject_set.filter(
                role='SUB'
            ).values('subject__name', 'subject__code')),
        }
        
        return JsonResponse({
            'success': True,
            'message': f'Changed combination for {student.full_name} from "{old_combination_code}" to "{new_combination.code}".',
            'combination': combination_data
        })
        
    except Student.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Student not found or is inactive.'
        })
    except Combination.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Combination not found or is inactive.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error changing combination: {str(e)}'
        })


def assign_single_combination(request):
    """Assign a combination to a single student"""
    student_id = request.POST.get('student_id')
    combination_id = request.POST.get('combination_id')
    
    if not student_id or not combination_id:
        return JsonResponse({
            'success': False,
            'message': 'Student ID and Combination ID are required.'
        })
    
    try:
        student = Student.objects.get(id=student_id, is_active=True)
        combination = Combination.objects.get(id=combination_id, is_active=True)
        
        # Check if student is A-Level
        a_level = EducationalLevel.objects.filter(code='A_LEVEL').first()
        if not student.class_level or student.class_level.educational_level != a_level:
            return JsonResponse({
                'success': False,
                'message': 'Only A-Level students can be assigned combinations.'
            })
        
        # Check if student already has a combination
        if student.combination:
            return JsonResponse({
                'success': False,
                'message': f'Student {student.full_name} already has combination "{student.combination.code}". Use "Change" instead.'
            })
        
        # Assign combination
        student.combination = combination
        student.save()
        
        # Log the assignment
        SystemLog.objects.create(
            user=request.user,
            log_type='create',
            description=f'Assigned combination {combination.code} to student {student.full_name}',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        # Get combination details for UI update
        combination_data = {
            'id': combination.id,
            'code': combination.code,
            'name': combination.name,
            'student_name': student.full_name,
            'total_subjects': combination.combinationsubject_set.count(),
            'core_subjects': list(combination.combinationsubject_set.filter(
                role='CORE'
            ).values('subject__name', 'subject__code')),
            'subsidiary_subjects': list(combination.combinationsubject_set.filter(
                role='SUB'
            ).values('subject__name', 'subject__code')),
        }
        
        return JsonResponse({
            'success': True,
            'message': f'Combination "{combination.code}" assigned to {student.full_name} successfully.',
            'combination': combination_data
        })
        
    except Student.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Student not found or is inactive.'
        })
    except Combination.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Combination not found or is inactive.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error assigning combination: {str(e)}'
        })


def bulk_assign_combinations(request):
    """Assign the same combination to multiple students"""
    student_ids = request.POST.getlist('student_ids[]')
    combination_id = request.POST.get('combination_id')
    
    if not student_ids or not combination_id:
        return JsonResponse({
            'success': False,
            'message': 'No students selected or combination not specified.'
        })
    
    try:
        combination = Combination.objects.get(id=combination_id, is_active=True)
        a_level = EducationalLevel.objects.filter(code='A_LEVEL').first()
        
        assigned_count = 0
        failed_students = []
        
        for student_id in student_ids:
            try:
                student = Student.objects.get(id=student_id, is_active=True)
                
                # Check if student is A-Level
                if not student.class_level or student.class_level.educational_level != a_level:
                    failed_students.append(f"{student.full_name} (Not A-Level)")
                    continue
                
                # Check if already has a combination
                if student.combination:
                    failed_students.append(f"{student.full_name} (Already has combination)")
                    continue
                
                # Assign combination
                student.combination = combination
                student.save()
                assigned_count += 1
                
                # Log individual assignment
                SystemLog.objects.create(
                    user=request.user,
                    log_type='create',
                    description=f'Bulk assigned combination {combination.code} to student {student.full_name}',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
            except Student.DoesNotExist:
                failed_students.append(f"ID {student_id} (Not found)")
                continue
        
        message = f'Successfully assigned combination "{combination.code}" to {assigned_count} student(s).'
        if failed_students:
            message += f' Failed: {len(failed_students)} student(s).'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'assigned_count': assigned_count,
            'failed_count': len(failed_students)
        })
        
    except Combination.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Combination not found or is inactive.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error bulk assigning combinations: {str(e)}'
        })


def remove_combination(request):
    """Remove combination from a student"""
    student_id = request.POST.get('student_id')
    
    if not student_id:
        return JsonResponse({
            'success': False,
            'message': 'Student ID is required.'
        })
    
    try:
        student = Student.objects.get(id=student_id, is_active=True)
        
        if not student.combination:
            return JsonResponse({
                'success': False,
                'message': 'Student does not have a combination assigned.'
            })
        
        combination_code = student.combination.code
        student.combination = None
        student.save()
        
        # Log the removal
        SystemLog.objects.create(
            user=request.user,
            log_type='delete',
            description=f'Removed combination {combination_code} from student {student.full_name}',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Combination "{combination_code}" removed from {student.full_name} successfully.'
        })
        
    except Student.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Student not found or is inactive.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error removing combination: {str(e)}'
        })


def bulk_remove_combinations(request):
    """Remove combinations from multiple students"""
    student_ids = request.POST.getlist('student_ids[]')
    
    if not student_ids:
        return JsonResponse({
            'success': False,
            'message': 'No students selected.'
        })
    
    try:
        removed_count = 0
        failed_students = []
        
        for student_id in student_ids:
            try:
                student = Student.objects.get(id=student_id, is_active=True)
                
                if not student.combination:
                    failed_students.append(f"{student.full_name} (No combination)")
                    continue
                
                combination_code = student.combination.code
                student.combination = None
                student.save()
                removed_count += 1
                
                # Log individual removal
                SystemLog.objects.create(
                    user=request.user,
                    log_type='delete',
                    description=f'Bulk removed combination {combination_code} from student {student.full_name}',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
            except Student.DoesNotExist:
                failed_students.append(f"ID {student_id} (Not found)")
                continue
        
        message = f'Successfully removed combinations from {removed_count} student(s).'
        if failed_students:
            message += f' Failed: {len(failed_students)} student(s).'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'removed_count': removed_count,
            'failed_count': len(failed_students)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error bulk removing combinations: {str(e)}'
        })


@login_required
def get_combination_details_ajax(request):
    """Get combination details for AJAX requests"""
    combination_id = request.GET.get('combination_id')
    
    if not combination_id:
        return JsonResponse({
            'success': False,
            'message': 'Combination ID is required.'
        })
    
    try:
        combination = Combination.objects.get(id=combination_id)
        
        # Get subjects
        subjects = combination.combinationsubject_set.select_related('subject').all()
        
        # Get students in this combination
        students = Student.objects.filter(
            combination=combination,
            is_active=True
        ).select_related('class_level', 'stream_class')
        
        data = {
            'success': True,
            'combination': {
                'id': combination.id,
                'code': combination.code,
                'name': combination.name,
                'is_active': combination.is_active,
                'core_count': subjects.filter(role='CORE').count(),
                'subsidiary_count': subjects.filter(role='SUB').count(),
                'student_count': students.count(),
                'subjects': list(subjects.values(
                    'subject__id', 'subject__name', 'subject__code', 'role'
                )),
                'students': list(students.values(
                    'id', 'full_name', 'registration_number',
                    'class_level__name', 'stream_class__stream_letter',
                    'is_active'
                )[:10])  # Limit to 10 students for preview
            }
        }
        
        return JsonResponse(data)
        
    except Combination.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Combination not found.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error getting combination details: {str(e)}'
        })


@login_required
def combination_students(request, combination_id):
    """
    View students who are assigned to a specific combination
    """
    # Get the combination
    combination = get_object_or_404(
        Combination.objects.select_related('educational_level'),
        id=combination_id
    )
    
    # Get students assigned to this combination
    students = Student.objects.filter(
        combination=combination,
        is_active=True
    ).select_related(
        'class_level', 'stream_class'
    ).prefetch_related(
        'parents', 'optional_subjects'
    ).order_by('class_level__order', 'first_name', 'last_name')
    
    # Get combination subjects
    combination_subjects = CombinationSubject.objects.filter(
        combination=combination
    ).select_related('subject').order_by('-role', 'subject__name')  # Core first
    
    # Get statistics
    total_students = students.count()
    male_students = students.filter(gender='male').count()
    female_students = students.filter(gender='female').count()
    
    # Calculate percentages
    male_percentage = (male_students / total_students * 100) if total_students > 0 else 0
    female_percentage = (female_students / total_students * 100) if total_students > 0 else 0
    
    # Group by class
    class_distribution = students.values(
        'class_level__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')

    for item in class_distribution:
        item['percentage'] = (item['count'] / total_students * 100) if total_students > 0 else 0

    # Get streams distribution
    stream_distribution = students.values(
        'stream_class__stream_letter'
    ).annotate(
        count=Count('id')
    ).order_by('stream_class__stream_letter')
    
    # Get recent assignments - use updated_at field instead
    # Filter students who were updated in the last 30 days (likely when combination was assigned)
    recent_assignments = students.filter(
        updated_at__gte=timezone.now() - timedelta(days=30)
    ).order_by('-updated_at')[:10]

    context = {
        'combination': combination,
        'students': students,
        'combination_subjects': combination_subjects,
        'total_students': total_students,
        'male_students': male_students,
        'female_students': female_students,
        'class_distribution': class_distribution,
        'stream_distribution': stream_distribution,
        'recent_assignments': recent_assignments,
        'male_percentage': round(male_percentage, 1),
        'female_percentage': round(female_percentage, 1),
        'page_title': f'Students in {combination.code} - {combination.name}',
    }
    
    return render(request, 'admin/academic/combination_students.html', context)


@login_required
def combination_pdf_report(request, combination_id):
    """
    Generate and download PDF report for a combination
    """
    try:
        # Get the combination
        combination = get_object_or_404(
            Combination.objects.select_related('educational_level'),
            id=combination_id
        )
        
        # Get students assigned to this combination
        students = Student.objects.filter(
            combination=combination,
            is_active=True
        ).select_related(
            'class_level', 'stream_class'
        ).prefetch_related(
            'parents', 'optional_subjects'
        ).order_by('class_level__order', 'first_name', 'last_name')
        
        # Get combination subjects
        combination_subjects = CombinationSubject.objects.filter(
            combination=combination
        ).select_related('subject').order_by('-role', 'subject__name')
        
        # Get statistics
        total_students = students.count()
        male_students = students.filter(gender='male').count()
        female_students = students.filter(gender='female').count()
        
        # Calculate percentages
        male_percentage = (male_students / total_students * 100) if total_students > 0 else 0
        female_percentage = (female_students / total_students * 100) if total_students > 0 else 0
        
        # Group by class
        class_distribution = students.values(
            'class_level__name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Prepare context
        context = {
            'combination': combination,
            'students': students,
            'combination_subjects': combination_subjects,
            'total_students': total_students,
            'male_students': male_students,
            'female_students': female_students,
            'class_distribution': class_distribution,
            'male_percentage': round(male_percentage, 1),
            'female_percentage': round(female_percentage, 1),
            'generated_date': timezone.now(),
            'request': request,
        }
        
        # Render HTML template
        html_string = render_to_string('admin/academic/combination_pdf_report.html', context)
        
        # Create PDF
        font_config = FontConfiguration()
        html = HTML(string=html_string, base_url=request.build_absolute_uri())
        
        # Generate PDF
        pdf_file = html.write_pdf(font_config=font_config)
        
        # Create response
        response = HttpResponse(pdf_file, content_type='application/pdf')
        filename = f'combination_{combination.code}_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        messages.error(request, f'Error generating PDF report: {str(e)}')
        return redirect('admin_combination_students', combination_id=combination_id)    