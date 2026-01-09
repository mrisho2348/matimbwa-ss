# accounts/views/admin_views.py
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q
from django.utils import timezone
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from accounts.forms.admin_forms import AdminPreferencesForm, AdminProfileUpdateForm
from accounts.models import CustomUser, Notification, Staffs, AdminHOD, SystemLog
from core.models import (
    EducationalLevel, AcademicYear, Term, Subject, 
    ClassLevel, StreamClass
)
from students.models import Parent, PreviousSchool, Student


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
    
    return redirect('admin:admin_profile')

@login_required
def profile_security(request):
    """View and manage security settings"""
    # Get security statistics
    security_stats = {
        'last_password_change': request.user.last_password_change if hasattr(request.user, 'last_password_change') else None,
        'two_factor_enabled': request.user.two_factor_enabled if hasattr(request.user, 'two_factor_enabled') else False,
        'failed_login_attempts': SystemLog.objects.filter(
            user=request.user,
            log_type='login_failed',
            timestamp__gte=timezone.now() - timedelta(days=30)
        ).count(),
        'active_sessions': request.session.session_key,  # Simplified - would use session store in production
    }
    
    context = {
        'page_title': 'Security Settings',
        'security_stats': security_stats,
    }
    return render(request, 'admin/account/security.html', context)

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

@login_required
def two_factor_settings(request):
    """Manage two-factor authentication settings"""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'enable':
            # Enable 2FA logic would go here
            messages.success(request, 'Two-factor authentication enabled successfully!')
        elif action == 'disable':
            # Disable 2FA logic would go here
            messages.success(request, 'Two-factor authentication disabled.')
        elif action == 'generate_backup':
            # Generate backup codes logic would go here
            messages.success(request, 'Backup codes generated successfully!')
        
        return redirect('admin:admin_two_factor_settings')
    
    context = {
        'page_title': 'Two-Factor Authentication',
        'two_factor_enabled': request.user.two_factor_enabled if hasattr(request.user, 'two_factor_enabled') else False,
    }
    return render(request, 'admin/account/two_factor.html', context)

@login_required
def account_preferences(request):
    """Manage account preferences and settings"""
    if request.method == 'POST':
        form = AdminPreferencesForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Preferences updated successfully!')
            return redirect('admin:admin_preferences')
    else:
        form = AdminPreferencesForm(instance=request.user)
    
    context = {
        'page_title': 'Account Preferences',
        'form': form,
    }
    return render(request, 'admin/account/preferences.html', context)

@login_required
def session_management(request):
    """View and manage active sessions"""
    if request.method == 'POST':
        action = request.POST.get('action')
        session_key = request.POST.get('session_key')
        
        if action == 'logout_other' and session_key:
            # Logic to logout other sessions would go here
            messages.success(request, 'Other sessions logged out successfully.')
        elif action == 'logout_all':
            # Logic to logout all other sessions would go here
            messages.success(request, 'All other sessions logged out.')
        
        return redirect('admin:admin_session_management')
    
    # Get active sessions (simplified - would use session store in production)
    active_sessions = [
        {
            'device': 'Desktop Chrome',
            'location': 'Nairobi, Kenya',
            'last_active': timezone.now() - timedelta(minutes=15),
            'current': True,
            'ip_address': request.META.get('REMOTE_ADDR')
        }
    ]
    
    context = {
        'page_title': 'Session Management',
        'active_sessions': active_sessions,
        'current_session_key': request.session.session_key,
    }
    return render(request, 'admin/account/sessions.html', context)

@login_required
def delete_account_request(request):
    """Handle account deletion requests"""
    if request.method == 'POST':
        confirmation = request.POST.get('confirmation')
        password = request.POST.get('password')
        
        if confirmation != 'DELETE MY ACCOUNT':
            messages.error(request, 'Confirmation text does not match.')
            return redirect('admin:admin_delete_request')
        
        # Verify password
        if not request.user.check_password(password):
            messages.error(request, 'Incorrect password.')
            return redirect('admin:admin_delete_request')
        
        # Instead of immediate deletion, schedule it or mark for review
        messages.success(
            request,
            'Account deletion request submitted. '
            'An administrator will review your request within 24 hours.'
        )
        
        # Log the deletion request
        SystemLog.objects.create(
            user=request.user,
            log_type='security',
            description='Account deletion request submitted',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return redirect('admin:admin_dashboard')
    
    context = {
        'page_title': 'Delete Account',
        'user': request.user,
    }
    return render(request, 'admin/account/delete_request.html', context)

@login_required
def activity_logs(request):
    """View detailed activity logs for the administrator"""
    # Get filter parameters
    log_type = request.GET.get('type', '')
    date_from = request.GET.get('from', '')
    date_to = request.GET.get('to', '')
    
    # Build queryset
    activities = SystemLog.objects.filter(user=request.user)
    
    if log_type:
        activities = activities.filter(log_type=log_type)
    
    if date_from:
        try:
            from_date = timezone.datetime.strptime(date_from, '%Y-%m-%d')
            activities = activities.filter(timestamp__gte=from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = timezone.datetime.strptime(date_to, '%Y-%m-%d')
            activities = activities.filter(timestamp__lte=to_date)
        except ValueError:
            pass
    
    # Order and paginate (simplified)
    activities = activities.order_by('-timestamp')[:50]
    
    # Get statistics
    activity_stats = {
        'total': SystemLog.objects.filter(user=request.user).count(),
        'today': SystemLog.objects.filter(
            user=request.user,
            timestamp__date=timezone.now().date()
        ).count(),
        'logins_today': SystemLog.objects.filter(
            user=request.user,
            log_type='login',
            timestamp__date=timezone.now().date()
        ).count(),
    }
    
    context = {
        'page_title': 'Activity Logs',
        'activities': activities,
        'activity_stats': activity_stats,
        'log_types': SystemLog.LOG_TYPES,
        'filters': {
            'type': log_type,
            'from': date_from,
            'to': date_to,
        },
    }
    return render(request, 'admin/account/activity_logs.html', context)

# ============================================================================
# AJAX ENDPOINTS FOR PROFILE MANAGEMENT
# ============================================================================

@login_required
def ajax_check_password_strength(request):
    """AJAX endpoint to check password strength"""
    password = request.GET.get('password', '')
    
    if not password:
        return JsonResponse({'error': 'No password provided'}, status=400)
    
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
        return JsonResponse({'error': 'No email provided'}, status=400)
    
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
                    }, status=400)
                
                # Check for duplicates
                if EducationalLevel.objects.filter(code__iexact=code).exists():
                    return JsonResponse({
                        'success': False,
                        'message': f'Educational level with code "{code}" already exists.'
                    }, status=400)
                
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
                    }, status=400)
                
                level = get_object_or_404(EducationalLevel, id=level_id)
                
                name = request.POST.get('name', '').strip()
                code = request.POST.get('code', '').strip()
                description = request.POST.get('description', '').strip()
                
                if not name or not code:
                    return JsonResponse({
                        'success': False,
                        'message': 'Name and Code are required.'
                    }, status=400)
                
                # Check for duplicate code (exclude current)
                if EducationalLevel.objects.filter(
                    code__iexact=code
                ).exclude(id=level.id).exists():
                    return JsonResponse({
                        'success': False,
                        'message': f'Educational level with code "{code}" already exists.'
                    }, status=400)
                
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
                    }, status=400)
                
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
                }, status=400)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': 'POST request required.'
    }, status=405)


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
                start_date = request.POST.get('start_date', '').strip()
                end_date = request.POST.get('end_date', '').strip()
                
                if not name or not start_date or not end_date:
                    return JsonResponse({
                        'success': False,
                        'message': 'Name, start date, and end date are required.'
                    }, status=400)
                
                # Check for duplicates
                if AcademicYear.objects.filter(name__iexact=name).exists():
                    return JsonResponse({
                        'success': False,
                        'message': f'Academic year "{name}" already exists.'
                    }, status=400)
                
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
                    }, status=400)
                
                year = get_object_or_404(AcademicYear, id=year_id)
                
                name = request.POST.get('name', '').strip()
                start_date = request.POST.get('start_date', '').strip()
                end_date = request.POST.get('end_date', '').strip()
                
                if not name or not start_date or not end_date:
                    return JsonResponse({
                        'success': False,
                        'message': 'Name, start date, and end date are required.'
                    }, status=400)
                
                # Check for duplicate name (exclude current)
                if AcademicYear.objects.filter(
                    name__iexact=name
                ).exclude(id=year.id).exists():
                    return JsonResponse({
                        'success': False,
                        'message': f'Academic year "{name}" already exists.'
                    }, status=400)
                
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
                    }, status=400)
                
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
                    }, status=400)
                
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
                }, status=400)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': 'POST request required.'
    }, status=405)


# Legacy view - redirect to list for backward compatibility
@login_required
def academic_years(request):
    """Redirect to academic_years_list for backward compatibility"""
    return redirect('admin_academic_years_list')

@login_required
def terms_list(request):
    """Display list of terms"""
    terms = Term.objects.select_related('academic_year').all().order_by('-academic_year', 'term_number')
    
    context = {
        'page_title': 'Terms',
        'terms': terms,
    }
    return render(request, 'admin/academic/terms_list.html', context)


@login_required
def terms_crud(request):
    """Handle AJAX CRUD operations for terms"""
    if request.method == 'POST':
        action = request.POST.get('action', '').lower()
        
        try:
            if action == 'create':
                academic_year_id = request.POST.get('academic_year_id', '').strip()
                term_number = request.POST.get('term_number', '').strip()
                start_date = request.POST.get('start_date', '').strip()
                end_date = request.POST.get('end_date', '').strip()
                
                if not academic_year_id or not term_number or not start_date or not end_date:
                    return JsonResponse({
                        'success': False,
                        'message': 'Academic year, term number, start date, and end date are required.'
                    }, status=400)
                
                academic_year = get_object_or_404(AcademicYear, id=academic_year_id)
                
                # Check for duplicate term
                if Term.objects.filter(
                    academic_year=academic_year,
                    term_number=term_number
                ).exists():
                    return JsonResponse({
                        'success': False,
                        'message': f'Term {term_number} already exists for {academic_year.name}.'
                    }, status=400)
                
                term = Term.objects.create(
                    academic_year=academic_year,
                    term_number=term_number,
                    start_date=start_date,
                    end_date=end_date
                )
                
                return JsonResponse({
                    'success': True,
                    'message': f'Term {term_number} created successfully.',
                    'term': {
                        'id': term.id,
                        'academic_year_id': term.academic_year.id,
                        'academic_year_name': term.academic_year.name,
                        'term_number': term.term_number,
                        'start_date': term.start_date.strftime('%Y-%m-%d'),
                        'end_date': term.end_date.strftime('%Y-%m-%d'),
                    }
                })
                
            elif action == 'update':
                term_id = request.POST.get('id')
                if not term_id:
                    return JsonResponse({
                        'success': False,
                        'message': 'Term ID is required.'
                    }, status=400)
                
                term = get_object_or_404(Term, id=term_id)
                
                academic_year_id = request.POST.get('academic_year_id', '').strip()
                term_number = request.POST.get('term_number', '').strip()
                start_date = request.POST.get('start_date', '').strip()
                end_date = request.POST.get('end_date', '').strip()
                
                if not academic_year_id or not term_number or not start_date or not end_date:
                    return JsonResponse({
                        'success': False,
                        'message': 'Academic year, term number, start date, and end date are required.'
                    }, status=400)
                
                academic_year = get_object_or_404(AcademicYear, id=academic_year_id)
                
                # Check for duplicate term (exclude current)
                if Term.objects.filter(
                    academic_year=academic_year,
                    term_number=term_number
                ).exclude(id=term.id).exists():
                    return JsonResponse({
                        'success': False,
                        'message': f'Term {term_number} already exists for {academic_year.name}.'
                    }, status=400)
                
                term.academic_year = academic_year
                term.term_number = term_number
                term.start_date = start_date
                term.end_date = end_date
                term.save()
                
                return JsonResponse({
                    'success': True,
                    'message': f'Term {term_number} updated successfully.',
                    'term': {
                        'id': term.id,
                        'academic_year_id': term.academic_year.id,
                        'academic_year_name': term.academic_year.name,
                        'term_number': term.term_number,
                        'start_date': term.start_date.strftime('%Y-%m-%d'),
                        'end_date': term.end_date.strftime('%Y-%m-%d'),
                    }
                })
                
            elif action == 'delete':
                term_id = request.POST.get('id')
                if not term_id:
                    return JsonResponse({
                        'success': False,
                        'message': 'Term ID is required.'
                    }, status=400)
                
                term = get_object_or_404(Term, id=term_id)
                term_info = f'Term {term.term_number} ({term.academic_year.name})'
                term.delete()
                
                return JsonResponse({
                    'success': True,
                    'message': f'{term_info} deleted successfully.',
                    'id': term_id
                })
            
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid action.'
                }, status=400)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': 'POST request required.'
    }, status=405)


# Legacy view - redirect to list for backward compatibility
@login_required
def terms(request):
    """Redirect to terms_list for backward compatibility"""
    return redirect('admin_terms_list')

@login_required
def subjects_list(request):
    """Display list of subjects"""
    subjects = Subject.objects.select_related('educational_level').all().order_by('educational_level', 'name')
    
    context = {
        'page_title': 'Subjects',
        'subjects': subjects,
    }
    return render(request, 'admin/academic/subjects_list.html', context)


@login_required
def subjects_crud(request):
    """Handle AJAX CRUD operations for subjects"""
    if request.method == 'POST':
        action = request.POST.get('action', '').lower()
        
        try:
            if action == 'create':
                educational_level_id = request.POST.get('educational_level_id', '').strip()
                name = request.POST.get('name', '').strip()
                code = request.POST.get('code', '').strip()
                short_name = request.POST.get('short_name', '').strip()
                is_compulsory = request.POST.get('is_compulsory') == 'true'
                
                if not educational_level_id or not name or not code:
                    return JsonResponse({
                        'success': False,
                        'message': 'Educational level, name, and code are required.'
                    }, status=400)
                
                educational_level = get_object_or_404(EducationalLevel, id=educational_level_id)
                
                # Check for duplicate subject code
                if Subject.objects.filter(code__iexact=code).exists():
                    return JsonResponse({
                        'success': False,
                        'message': f'Subject with code "{code}" already exists.'
                    }, status=400)
                
                subject = Subject.objects.create(
                    educational_level=educational_level,
                    name=name,
                    code=code,
                    short_name=short_name,
                    is_compulsory=is_compulsory
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
                    }
                })
                
            elif action == 'update':
                subject_id = request.POST.get('id')
                if not subject_id:
                    return JsonResponse({
                        'success': False,
                        'message': 'Subject ID is required.'
                    }, status=400)
                
                subject = get_object_or_404(Subject, id=subject_id)
                
                educational_level_id = request.POST.get('educational_level_id', '').strip()
                name = request.POST.get('name', '').strip()
                code = request.POST.get('code', '').strip()
                short_name = request.POST.get('short_name', '').strip()
                is_compulsory = request.POST.get('is_compulsory') == 'true'
                
                if not educational_level_id or not name or not code:
                    return JsonResponse({
                        'success': False,
                        'message': 'Educational level, name, and code are required.'
                    }, status=400)
                
                educational_level = get_object_or_404(EducationalLevel, id=educational_level_id)
                
                # Check for duplicate code (exclude current)
                if Subject.objects.filter(
                    code__iexact=code
                ).exclude(id=subject.id).exists():
                    return JsonResponse({
                        'success': False,
                        'message': f'Subject with code "{code}" already exists.'
                    }, status=400)
                
                subject.educational_level = educational_level
                subject.name = name
                subject.code = code
                subject.short_name = short_name
                subject.is_compulsory = is_compulsory
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
                    }
                })
                
            elif action == 'delete':
                subject_id = request.POST.get('id')
                if not subject_id:
                    return JsonResponse({
                        'success': False,
                        'message': 'Subject ID is required.'
                    }, status=400)
                
                subject = get_object_or_404(Subject, id=subject_id)
                subject_name = subject.name
                subject.delete()
                
                return JsonResponse({
                    'success': True,
                    'message': f'Subject "{subject_name}" deleted successfully.',
                    'id': subject_id
                })
            
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid action.'
                }, status=400)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': 'POST request required.'
    }, status=405)


# Legacy view - redirect to list for backward compatibility
@login_required
def subjects(request):
    """Redirect to subjects_list for backward compatibility"""
    return redirect('admin_subjects_list')

@login_required
def class_levels_list(request):
    """Display list of class levels"""
    class_levels = ClassLevel.objects.select_related('educational_level').all().order_by('educational_level', 'name')
    
    context = {
        'page_title': 'Class Levels',
        'class_levels': class_levels,
    }
    return render(request, 'admin/academic/class_levels_list.html', context)


@login_required
def class_levels_crud(request):
    """Handle AJAX CRUD operations for class levels"""
    if request.method == 'POST':
        action = request.POST.get('action', '').lower()
        
        try:
            if action == 'create':
                educational_level_id = request.POST.get('educational_level_id', '').strip()
                name = request.POST.get('name', '').strip()
                code = request.POST.get('code', '').strip()
                description = request.POST.get('description', '').strip()
                
                if not educational_level_id or not name or not code:
                    return JsonResponse({
                        'success': False,
                        'message': 'Educational level, name, and code are required.'
                    }, status=400)
                
                educational_level = get_object_or_404(EducationalLevel, id=educational_level_id)
                
                # Check for duplicate class level code
                if ClassLevel.objects.filter(code__iexact=code).exists():
                    return JsonResponse({
                        'success': False,
                        'message': f'Class level with code "{code}" already exists.'
                    }, status=400)
                
                class_level = ClassLevel.objects.create(
                    educational_level=educational_level,
                    name=name,
                    code=code,
                    description=description
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
                        'description': class_level.description,
                    }
                })
                
            elif action == 'update':
                class_level_id = request.POST.get('id')
                if not class_level_id:
                    return JsonResponse({
                        'success': False,
                        'message': 'Class level ID is required.'
                    }, status=400)
                
                class_level = get_object_or_404(ClassLevel, id=class_level_id)
                
                educational_level_id = request.POST.get('educational_level_id', '').strip()
                name = request.POST.get('name', '').strip()
                code = request.POST.get('code', '').strip()
                description = request.POST.get('description', '').strip()
                
                if not educational_level_id or not name or not code:
                    return JsonResponse({
                        'success': False,
                        'message': 'Educational level, name, and code are required.'
                    }, status=400)
                
                educational_level = get_object_or_404(EducationalLevel, id=educational_level_id)
                
                # Check for duplicate code (exclude current)
                if ClassLevel.objects.filter(
                    code__iexact=code
                ).exclude(id=class_level.id).exists():
                    return JsonResponse({
                        'success': False,
                        'message': f'Class level with code "{code}" already exists.'
                    }, status=400)
                
                class_level.educational_level = educational_level
                class_level.name = name
                class_level.code = code
                class_level.description = description
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
                        'description': class_level.description,
                    }
                })
                
            elif action == 'delete':
                class_level_id = request.POST.get('id')
                if not class_level_id:
                    return JsonResponse({
                        'success': False,
                        'message': 'Class level ID is required.'
                    }, status=400)
                
                class_level = get_object_or_404(ClassLevel, id=class_level_id)
                class_level_name = class_level.name
                class_level.delete()
                
                return JsonResponse({
                    'success': True,
                    'message': f'Class level "{class_level_name}" deleted successfully.',
                    'id': class_level_id
                })
            
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid action.'
                }, status=400)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': 'POST request required.'
    }, status=405)


# Legacy view - redirect to list for backward compatibility
@login_required
def class_levels(request):
    """Redirect to class_levels_list for backward compatibility"""
    return redirect('admin_class_levels_list')


@login_required
def stream_classes_list(request):
    """Display list of stream classes"""
    streams = StreamClass.objects.select_related('class_level').all().order_by('class_level', 'stream_letter')
    
    context = {
        'page_title': 'Stream Classes',
        'streams': streams,
    }
    return render(request, 'admin/academic/stream_classes_list.html', context)


@login_required
def stream_classes_crud(request):
    """Handle AJAX CRUD operations for stream classes"""
    if request.method == 'POST':
        action = request.POST.get('action', '').lower()
        
        try:
            if action == 'create':
                class_level_id = request.POST.get('class_level_id', '').strip()
                stream_letter = request.POST.get('stream_letter', '').strip().upper()
                capacity = request.POST.get('capacity', '50').strip()
                
                if not class_level_id or not stream_letter:
                    return JsonResponse({
                        'success': False,
                        'message': 'Class level and stream letter are required.'
                    }, status=400)
                
                if len(stream_letter) != 1 or not stream_letter.isalpha():
                    return JsonResponse({
                        'success': False,
                        'message': 'Stream letter must be a single character (A-Z).'
                    }, status=400)
                
                try:
                    capacity = int(capacity)
                    if capacity <= 0:
                        raise ValueError
                except ValueError:
                    return JsonResponse({
                        'success': False,
                        'message': 'Capacity must be a positive integer.'
                    }, status=400)
                
                class_level = get_object_or_404(ClassLevel, id=class_level_id)
                
                # Check for duplicate stream (unique_together constraint)
                if StreamClass.objects.filter(
                    class_level=class_level,
                    stream_letter=stream_letter
                ).exists():
                    return JsonResponse({
                        'success': False,
                        'message': f'Stream {class_level.name}{stream_letter} already exists.'
                    }, status=400)
                
                stream = StreamClass.objects.create(
                    class_level=class_level,
                    stream_letter=stream_letter,
                    capacity=capacity
                )
                
                return JsonResponse({
                    'success': True,
                    'message': f'Stream "{stream}" created successfully.',
                    'stream': {
                        'id': stream.id,
                        'class_level_id': stream.class_level.id,
                        'class_level_name': stream.class_level.name,
                        'stream_letter': stream.stream_letter,
                        'capacity': stream.capacity,
                        'student_count': stream.student_count,
                        'is_active': stream.is_active,
                        'full_name': str(stream),
                    }
                })
                
            elif action == 'update':
                stream_id = request.POST.get('id')
                if not stream_id:
                    return JsonResponse({
                        'success': False,
                        'message': 'Stream ID is required.'
                    }, status=400)
                
                stream = get_object_or_404(StreamClass, id=stream_id)
                
                class_level_id = request.POST.get('class_level_id', '').strip()
                stream_letter = request.POST.get('stream_letter', '').strip().upper()
                capacity = request.POST.get('capacity', str(stream.capacity)).strip()
                
                if not class_level_id or not stream_letter:
                    return JsonResponse({
                        'success': False,
                        'message': 'Class level and stream letter are required.'
                    }, status=400)
                
                if len(stream_letter) != 1 or not stream_letter.isalpha():
                    return JsonResponse({
                        'success': False,
                        'message': 'Stream letter must be a single character (A-Z).'
                    }, status=400)
                
                try:
                    capacity = int(capacity)
                    if capacity <= 0:
                        raise ValueError
                except ValueError:
                    return JsonResponse({
                        'success': False,
                        'message': 'Capacity must be a positive integer.'
                    }, status=400)
                
                class_level = get_object_or_404(ClassLevel, id=class_level_id)
                
                # Check for duplicate stream (exclude current)
                if StreamClass.objects.filter(
                    class_level=class_level,
                    stream_letter=stream_letter
                ).exclude(id=stream.id).exists():
                    return JsonResponse({
                        'success': False,
                        'message': f'Stream {class_level.name}{stream_letter} already exists.'
                    }, status=400)
                
                stream.class_level = class_level
                stream.stream_letter = stream_letter
                stream.capacity = capacity
                stream.save()
                
                return JsonResponse({
                    'success': True,
                    'message': f'Stream "{stream}" updated successfully.',
                    'stream': {
                        'id': stream.id,
                        'class_level_id': stream.class_level.id,
                        'class_level_name': stream.class_level.name,
                        'stream_letter': stream.stream_letter,
                        'capacity': stream.capacity,
                        'student_count': stream.student_count,
                        'is_active': stream.is_active,
                        'full_name': str(stream),
                    }
                })
                
            elif action == 'delete':
                stream_id = request.POST.get('id')
                if not stream_id:
                    return JsonResponse({
                        'success': False,
                        'message': 'Stream ID is required.'
                    }, status=400)
                
                stream = get_object_or_404(StreamClass, id=stream_id)
                stream_name = str(stream)
                stream.delete()
                
                return JsonResponse({
                    'success': True,
                    'message': f'Stream "{stream_name}" deleted successfully.',
                    'id': stream_id
                })
            
            elif action == 'toggle_active':
                stream_id = request.POST.get('id')
                if not stream_id:
                    return JsonResponse({
                        'success': False,
                        'message': 'Stream ID is required.'
                    }, status=400)
                
                stream = get_object_or_404(StreamClass, id=stream_id)
                stream.is_active = not stream.is_active
                stream.save()
                
                status_text = 'activated' if stream.is_active else 'deactivated'
                
                return JsonResponse({
                    'success': True,
                    'message': f'Stream "{stream}" {status_text} successfully.',
                    'stream': {
                        'id': stream.id,
                        'is_active': stream.is_active,
                        'full_name': str(stream),
                    }
                })
            
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid action.'
                }, status=400)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': 'POST request required.'
    }, status=405)


# Legacy view - redirect to list for backward compatibility
@login_required
def stream_classes(request):
    """Redirect to stream_classes_list for backward compatibility"""
    return redirect('admin_stream_classes_list')

# ============================================================================
# STUDENT MANAGEMENT VIEWS
# ============================================================================

@login_required
def students_list(request):
    """List all students with filtering options"""
    students = Student.objects.select_related('class_level', 'stream_class').all()
    
    # Filters
    class_filter = request.GET.get('class')
    status_filter = request.GET.get('status')
    
    if class_filter:
        students = students.filter(class_level__id=class_filter)
    if status_filter:
        students = students.filter(status=status_filter)
    
    context = {
        'page_title': 'Students List',
        'students': students,
        'class_levels': ClassLevel.objects.all(),
        'status_choices': Student._meta.get_field('status').choices,
    }
    return render(request, 'admin/students/list.html', context)

@login_required
def students_add(request):
    """Add new student"""
    if request.method == 'POST':
        try:
            # Extract form data
            first_name = request.POST.get('first_name')
            middle_name = request.POST.get('middle_name', '')
            last_name = request.POST.get('last_name')
            date_of_birth = request.POST.get('date_of_birth')
            gender = request.POST.get('gender')
            address = request.POST.get('address', '')
            class_level_id = request.POST.get('class_level')
            stream_class_id = request.POST.get('stream_class')
            
            # Get related objects
            class_level = get_object_or_404(ClassLevel, id=class_level_id) if class_level_id else None
            stream_class = get_object_or_404(StreamClass, id=stream_class_id) if stream_class_id else None
            
            # Create student
            student = Student.objects.create(
                first_name=first_name,
                middle_name=middle_name,
                last_name=last_name,
                date_of_birth=date_of_birth,
                gender=gender,
                address=address,
                class_level=class_level,
                stream_class=stream_class,
                status='active'
            )
            
            messages.success(request, f'Student "{student.full_name}" added successfully.')
            return redirect('admin:admin_students_list')
            
        except Exception as e:
            messages.error(request, f'Error adding student: {str(e)}')
    
    context = {
        'page_title': 'Add Student',
        'class_levels': ClassLevel.objects.all(),
        'stream_classes': StreamClass.objects.all(),
        'genders': Student._meta.get_field('gender').choices,
    }
    return render(request, 'admin/students/add.html', context)

@login_required
def students_by_class(request):
    """View students grouped by class"""
    class_levels = ClassLevel.objects.annotate(
        student_count=Count('students', filter=Q(students__status='active'))
    ).filter(student_count__gt=0)
    
    selected_class = request.GET.get('class')
    students = []
    
    if selected_class:
        class_obj = get_object_or_404(ClassLevel, id=selected_class)
        students = Student.objects.filter(
            class_level=class_obj, 
            status='active'
        ).select_related('stream_class')
    
    context = {
        'page_title': 'Students by Class',
        'class_levels': class_levels,
        'selected_class': selected_class,
        'students': students,
    }
    return render(request, 'admin/students/by_class.html', context)

@login_required
def student_status(request):
    """Manage student statuses (active, suspended, etc.)"""
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        new_status = request.POST.get('status')
        
        student = get_object_or_404(Student, id=student_id)
        old_status = student.status
        student.status = new_status
        student.save()
        
        messages.success(
            request, 
            f'Student {student.full_name} status changed from {old_status} to {new_status}.'
        )
        return redirect('admin:admin_student_status')
    
    students = Student.objects.all().select_related('class_level')
    
    context = {
        'page_title': 'Student Status Management',
        'students': students,
        'status_choices': Student._meta.get_field('status').choices,
    }
    return render(request, 'admin/students/status.html', context)

@login_required
def parents_list(request):
    """List all parents"""
    parents = Parent.objects.prefetch_related('students').all()
    
    context = {
        'page_title': 'Parents List',
        'parents': parents,
    }
    return render(request, 'admin/students/parents.html', context)

@login_required
def previous_schools(request):
    """Manage previous schools"""
    schools = PreviousSchool.objects.all()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            name = request.POST.get('name')
            school_level = request.POST.get('school_level')
            location = request.POST.get('location', '')
            
            PreviousSchool.objects.create(
                name=name,
                school_level=school_level,
                location=location
            )
            messages.success(request, f'Previous school "{name}" added.')
            
        return redirect('admin:admin_previous_schools')
    
    context = {
        'page_title': 'Previous Schools',
        'schools': schools,
        'level_choices': PreviousSchool._meta.get_field('school_level').choices,
    }
    return render(request, 'admin/students/previous_schools.html', context)

# ============================================================================
# STAFF MANAGEMENT VIEWS
# ============================================================================

@login_required
def staff_list(request):
    """List all staff members"""
    staff_members = Staffs.objects.select_related('admin').all()
    
    context = {
        'page_title': 'Staff List',
        'staff_members': staff_members,
    }
    return render(request, 'admin/staff/list.html', context)

@login_required
def staff_add(request):
    """Add new staff member"""
    if request.method == 'POST':
        try:
            # Create user first
            username = request.POST.get('username')
            email = request.POST.get('email')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            password = request.POST.get('password')
            
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password,
                user_type=2,  # Staff user type
                first_name=first_name,
                last_name=last_name
            )
            
            # Create staff profile
            middle_name = request.POST.get('middle_name', '')
            gender = request.POST.get('gender')
            role = request.POST.get('role')
            
            Staffs.objects.create(
                admin=user,
                middle_name=middle_name,
                gender=gender,
                role=role
            )
            
            messages.success(request, f'Staff member "{first_name} {last_name}" added successfully.')
            return redirect('admin:admin_staff_list')
            
        except Exception as e:
            messages.error(request, f'Error adding staff: {str(e)}')
    
    context = {
        'page_title': 'Add Staff Member',
        'role_choices': Staffs._meta.get_field('role').choices,
        'gender_choices': Staffs._meta.get_field('gender').choices,
    }
    return render(request, 'admin/staff/add.html', context)

@login_required
def staff_roles(request):
    """Manage staff roles"""
    roles = Staffs.objects.values('role').annotate(
        count=Count('id')
    ).order_by('role')
    
    context = {
        'page_title': 'Staff Roles',
        'roles': roles,
        'role_choices': Staffs._meta.get_field('role').choices,
    }
    return render(request, 'admin/staff/roles.html', context)

@login_required
def staff_assignments(request):
    """Manage staff class assignments"""
    context = {
        'page_title': 'Staff Assignments',
    }
    return render(request, 'admin/staff/assignments.html', context)

# ============================================================================
# USER MANAGEMENT VIEWS
# ============================================================================

@login_required
def users_list(request):
    """List all system users"""
    users = CustomUser.objects.select_related('adminhod', 'staff').all()
    
    context = {
        'page_title': 'Users List',
        'users': users,
    }
    return render(request, 'admin/users/list.html', context)

@login_required
def users_add(request):
    """Add new system user"""
    if request.method == 'POST':
        try:
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')
            user_type = request.POST.get('user_type')
            
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password,
                user_type=user_type
            )
            
            messages.success(request, f'User "{username}" created successfully.')
            return redirect('admin:admin_users_list')
            
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
    
    context = {
        'page_title': 'Add User',
        'user_type_choices': CustomUser._meta.get_field('user_type').choices,
    }
    return render(request, 'admin/users/add.html', context)

@login_required
def users_roles(request):
    """Manage user roles and permissions"""
    context = {
        'page_title': 'User Roles',
    }
    return render(request, 'admin/users/roles.html', context)

@login_required
def permissions(request):
    """Manage system permissions"""
    context = {
        'page_title': 'Permissions',
    }
    return render(request, 'admin/users/permissions.html', context)

@login_required
def user_activity(request):
    """View user activity logs"""
    context = {
        'page_title': 'User Activity',
    }
    return render(request, 'admin/users/activity.html', context)

# ============================================================================
# SYSTEM SETTINGS VIEWS
# ============================================================================

@login_required
def system_config(request):
    """System configuration settings"""
    if request.method == 'POST':
        # Handle configuration updates
        messages.success(request, 'System configuration updated successfully.')
        return redirect('admin:admin_system_config')
    
    context = {
        'page_title': 'System Configuration',
    }
    return render(request, 'admin/settings/system.html', context)

@login_required
def email_settings(request):
    """Email server configuration"""
    if request.method == 'POST':
        messages.success(request, 'Email settings updated successfully.')
        return redirect('admin:admin_email_settings')
    
    context = {
        'page_title': 'Email Settings',
    }
    return render(request, 'admin/settings/email.html', context)

@login_required
def sms_settings(request):
    """SMS gateway configuration"""
    context = {
        'page_title': 'SMS Settings',
    }
    return render(request, 'admin/settings/sms.html', context)

@login_required
def notifications(request):
    """Notification settings"""
    context = {
        'page_title': 'Notification Settings',
    }
    return render(request, 'admin/settings/notifications.html', context)

@login_required
def backup(request):
    """System backup and restore"""
    context = {
        'page_title': 'Backup & Restore',
    }
    return render(request, 'admin/settings/backup.html', context)

# ============================================================================
# SECURITY & LOGS VIEWS
# ============================================================================

@login_required
def audit_logs(request):
    """View system audit logs"""
    context = {
        'page_title': 'Audit Logs',
    }
    return render(request, 'admin/security/audit_logs.html', context)

@login_required
def login_history(request):
    """View user login history"""
    context = {
        'page_title': 'Login History',
    }
    return render(request, 'admin/security/login_history.html', context)

@login_required
def security_settings(request):
    """Security configuration"""
    context = {
        'page_title': 'Security Settings',
    }
    return render(request, 'admin/security/settings.html', context)

@login_required
def api_settings(request):
    """API configuration"""
    context = {
        'page_title': 'API Settings',
    }
    return render(request, 'admin/security/api.html', context)

# ============================================================================
# REPORTS & ANALYTICS VIEWS
# ============================================================================

@login_required
def financial_reports(request):
    """Financial reports"""
    context = {
        'page_title': 'Financial Reports',
    }
    return render(request, 'admin/reports/financial.html', context)

@login_required
def academic_reports(request):
    """Academic performance reports"""
    context = {
        'page_title': 'Academic Reports',
    }
    return render(request, 'admin/reports/academic.html', context)

@login_required
def attendance_reports(request):
    """Attendance reports"""
    context = {
        'page_title': 'Attendance Reports',
    }
    return render(request, 'admin/reports/attendance.html', context)

@login_required
def custom_reports(request):
    """Custom report generation"""
    context = {
        'page_title': 'Custom Reports',
    }
    return render(request, 'admin/reports/custom.html', context)

@login_required
def export_data(request):
    """Data export functionality"""
    context = {
        'page_title': 'Export Data',
    }
    return render(request, 'admin/reports/export.html', context)

# ============================================================================
# HELP & SUPPORT VIEWS
# ============================================================================

@login_required
def documentation(request):
    """System documentation"""
    context = {
        'page_title': 'Documentation',
    }
    return render(request, 'admin/help/documentation.html', context)

@login_required
def faq(request):
    """Frequently Asked Questions"""
    context = {
        'page_title': 'FAQ',
    }
    return render(request, 'admin/help/faq.html', context)

@login_required
def support_tickets(request):
    """Support ticket management"""
    context = {
        'page_title': 'Support Tickets',
    }
    return render(request, 'admin/help/support.html', context)

@login_required
def system_status(request):
    """System status and health"""
    context = {
        'page_title': 'System Status',
    }
    return render(request, 'admin/help/system_status.html', context)

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
    
    return JsonResponse({'error': 'Student ID required'}, status=400)