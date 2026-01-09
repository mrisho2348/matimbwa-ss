from django.shortcuts import redirect, HttpResponseRedirect
from django.utils.deprecation import MiddlewareMixin
from django.urls import reverse
from django.contrib import messages
from django.conf import settings
import logging
from accounts.models import Staffs

logger = logging.getLogger(__name__)

class RoleBasedAccessControlMiddleware(MiddlewareMixin):
    """
    Enhanced middleware for role-based access control with the following features:
    1. Public/private URL classification
    2. User type validation (1=Admin/HOD, 2=Staff)
    3. Staff role-based module access
    4. Comprehensive logging and monitoring
    5. Error handling and graceful redirects
    """

    def __init__(self, get_response):
        super().__init__(get_response)
        
        # Configuration for public paths (no authentication required)
        self.PUBLIC_PATHS = [
            '/', '/home/',
            '/about/', '/programs/',
            '/news/', '/gallery/',
            '/contact/',
            '/login/', '/login/process/',
            '/logout/',
            '/register/', '/register/check/', '/register/ajax/',
            '/static/', '/media/',
            '/favicon.ico', '/robots.txt',
        ]
        
        # Configuration for public modules (Django core modules)
        self.PUBLIC_MODULES = [
            'django.contrib.auth.views',
            'django.views.static',
            'django.contrib.staticfiles.views',
        ]
        
        # Admin/HOD configuration
        self.ADMIN_CONFIG = {
            'allowed_modules': [
                'accounts.views.administrator_views',
                'accounts.administrator_views',
                'core.views',              
                'django.views.static',
            ],
            'redirect_url': 'admin_dashboard',
            'role_name': 'Administrator/HOD'
        }
        
        # Staff role configurations
        self.STAFF_ROLES_CONFIG = {
            'Secretary': {
                'modules': ['accounts.views.secretary_views', 'accounts.views', 'django.views.static'],
                'redirect_url': 'secretary_dashboard',
                'role_name': 'Secretary'
            },
            'Staff': {
                'modules': ['accounts.views.staff_views', 'accounts.views', 'django.views.static'],
                'redirect_url': 'staff_dashboard',
                'role_name': 'Staff'
            },
            'Accountant': {
                'modules': ['accounts.views.accountant_views', 'accounts.views', 'django.views.static'],
                'redirect_url': 'accountant_dashboard',
                'role_name': 'Accountant'
            },
            'Academic': {
                'modules': ['accounts.views.academic_views', 'accounts.views', 'django.views.static'],
                'redirect_url': 'academic_dashboard',
                'role_name': 'Academic Officer'
            },
            'Headmaster': {
                'modules': ['accounts.views.headmaster_views', 'accounts.views', 'django.views.static'],
                'redirect_url': 'headmaster_dashboard',
                'role_name': 'Headmaster'
            },
            'Librarian': {
                'modules': ['accounts.views.librarian_views', 'accounts.views', 'django.views.static'],
                'redirect_url': 'librarian_dashboard',
                'role_name': 'Librarian'
            },
            'Admin': {
                'modules': ['accounts.views.admin_views', 'accounts.views', 'django.views.static'],
                'redirect_url': 'admin_dashboard',
                'role_name': 'Administrator'
            }
        }

    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Main entry point for view-level access control.
        """
        # Get current path and module
        current_path = request.path_info
        current_module = view_func.__module__
        
        # Log access attempt
        self._log_access_attempt(request, current_path, current_module)
        
        # Check if path is public
        if self._is_public_path(current_path) or self._is_public_module(current_module):
            return None
        
        # Check authentication
        if not request.user.is_authenticated:
            return self._handle_unauthenticated_access(request, current_path)
        
        # Validate user type
        if not self._validate_user_type(request.user):
            return self._handle_invalid_user_type(request)
        
        # Role-based access control
        user_type = str(request.user.user_type)
        
        if user_type == "1":  # Admin/HOD
            return self._handle_admin_access(request, current_module, current_path)
        
        elif user_type == "2":  # Staff
            return self._handle_staff_access(request, current_module, current_path)
        
        # Unknown user type
        logger.error(f'Unknown user type: {user_type} for user {request.user.username}')
        messages.error(request, 'Invalid account configuration.')
        return redirect('public_login')

    def _is_public_path(self, path):
        """Check if path is in public paths list."""
        return any(path.startswith(public_path) for public_path in self.PUBLIC_PATHS)

    def _is_public_module(self, module):
        """Check if module is in public modules list."""
        return any(module.startswith(public_module) for public_module in self.PUBLIC_MODULES)

    def _log_access_attempt(self, request, path, module):
        """Log access attempts for monitoring."""
        if request.user.is_authenticated:
            logger.info(
                f'Access attempt - User: {request.user.username}, '
                f'Type: {request.user.user_type}, Path: {path}, Module: {module}'
            )
        else:
            logger.info(f'Unauthenticated access attempt - Path: {path}, Module: {module}')

    def _handle_unauthenticated_access(self, request, path):
        """Handle unauthenticated access to protected resources."""
        logger.warning(f'Unauthenticated access to protected path: {path}')
        messages.info(request, '🔒 Please login to access this page.')
        
        # Store attempted URL for redirect after login
        if not path.startswith('/login/'):
            request.session['next_url'] = path
        
        return redirect('public_login')

    def _validate_user_type(self, user):
        """Validate that user has proper user_type attribute."""
        if not hasattr(user, 'user_type'):
            logger.error(f'User {user.username} missing user_type attribute')
            return False
        
        if user.user_type not in ['1', '2']:
            logger.error(f'Invalid user_type: {user.user_type} for user {user.username}')
            return False
        
        return True

    def _handle_invalid_user_type(self, request):
        """Handle users with invalid user_type configuration."""
        messages.error(
            request,
            '⚠️ Account Error\n'
            'Your account is not properly configured. Please contact support.'
        )
        return redirect('public_login')

    def _handle_admin_access(self, request, module, path):
        """Handle access control for Admin/HOD users."""
        # Check if user is active
        if not request.user.is_active:
            return self._handle_inactive_account(request, 'administrator')
        
        # Check module access
        if not self._is_module_allowed(module, self.ADMIN_CONFIG['allowed_modules']):
            logger.warning(
                f'Admin {request.user.username} attempted to access unauthorized module: {module}'
            )
            messages.warning(
                request,
                f'⛔ Access Restricted\n'
                f'This area is not accessible to {self.ADMIN_CONFIG["role_name"]} accounts.'
            )
            return redirect(self.ADMIN_CONFIG['redirect_url'])
        
        # Update session for security tracking
        request.session['last_access_role'] = 'admin'
        request.session['last_access_time'] = self._get_current_timestamp()
        
        logger.info(f'Admin access granted to {request.user.username} for module: {module}')
        return None

    def _handle_staff_access(self, request, module, path):
        """Handle access control for Staff users."""
        # Check if user is active
        if not request.user.is_active:
            return self._handle_inactive_account(request, 'staff')
        
        # Get staff profile
        staff_profile = self._get_staff_profile(request.user)
        if not staff_profile:
            return self._handle_missing_staff_profile(request)
        
        # Get role configuration
        role_config = self.STAFF_ROLES_CONFIG.get(staff_profile.role)
        if not role_config:
            return self._handle_unknown_staff_role(request, staff_profile.role)
        
        # Check if staff has no role assigned
        if not staff_profile.role or staff_profile.role.strip() == '':
            return self._handle_unassigned_staff_role(request)
        
        # Check module access
        if not self._is_module_allowed(module, role_config['modules']):
            logger.warning(
                f'{role_config["role_name"]} {request.user.username} '
                f'attempted to access unauthorized module: {module}'
            )
            messages.error(
                request,
                f'🚫 Access Denied\n'
                f'This area is restricted to {role_config["role_name"]} role.'
            )
            return redirect(role_config['redirect_url'])
        
        # Update session for security tracking
        request.session['last_access_role'] = staff_profile.role.lower()
        request.session['last_access_time'] = self._get_current_timestamp()
        
        logger.info(
            f'{role_config["role_name"]} access granted to {request.user.username} '
            f'for module: {module}'
        )
        return None

    def _get_staff_profile(self, user):
        """Get staff profile with error handling."""
        try:
            return Staffs.objects.get(admin=user)
        except Staffs.DoesNotExist:
            logger.error(f'Staff profile not found for user: {user.username}')
            return None
        except Exception as e:
            logger.error(f'Error fetching staff profile for {user.username}: {e}')
            return None

    def _is_module_allowed(self, module, allowed_modules):
        """Check if module is allowed for current role."""
        return any(module.startswith(allowed) for allowed in allowed_modules)

    def _handle_inactive_account(self, request, account_type):
        """Handle inactive account access attempts."""
        logger.warning(f'Inactive {account_type} account access: {request.user.username}')
        messages.error(
            request,
            f'⛔ Account Inactive\n'
            f'Your {account_type} account has been deactivated.\n'
            f'Please contact the system administrator.'
        )
        return redirect('public_login')

    def _handle_missing_staff_profile(self, request):
        """Handle missing staff profile."""
        logger.error(f'Missing staff profile for user: {request.user.username}')
        messages.error(
            request,
            '🔍 Profile Not Found\n'
            'Your staff profile could not be found.\n'
            'Please contact the system administrator.'
        )
        return redirect('public_login')

    def _handle_unknown_staff_role(self, request, role_name):
        """Handle unknown staff role configuration."""
        logger.error(f'Unknown staff role: {role_name} for user {request.user.username}')
        messages.error(
            request,
            f'⚙️ Configuration Error\n'
            f'Unknown staff role "{role_name}" detected.\n'
            f'Please contact the system administrator.'
        )
        return redirect('public_login')

    def _handle_unassigned_staff_role(self, request):
        """Handle staff users without assigned roles."""
        logger.warning(f'Staff without assigned role: {request.user.username}')
        messages.error(
            request,
            '📝 Role Assignment Required\n'
            'Your staff role has not been assigned yet.\n'
            'Please contact your supervisor or administrator.'
        )
        return redirect('public_login')

    def _get_current_timestamp(self):
        """Get current timestamp for logging."""
        from datetime import datetime
        return datetime.now().isoformat()

    def process_response(self, request, response):
        """
        Add security headers and additional logging to responses.
        """
        # Add security headers to all responses
        security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
        }
        
        for header, value in security_headers.items():
            response[header] = value
        
        # Log successful access to protected areas
        if request.user.is_authenticated and response.status_code == 200:
            path = request.path_info
            if not self._is_public_path(path):
                logger.info(
                    f'Protected access completed - '
                    f'User: {request.user.username}, Path: {path}, Status: {response.status_code}'
                )
        
        return response

