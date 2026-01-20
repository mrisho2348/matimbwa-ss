from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError

from core.models import AcademicYear, ClassLevel, StreamClass, Subject


class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, password=None, user_type=1, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, user_type=user_type, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 1)  # Set the default user_type for superusers
        return self.create_user(username, email, password, **extra_fields)
    
        
class CustomUser(AbstractUser):
    user_type_data = (
        (1, "HOD"),
        (2, "Staff"),
           
    )
    user_type = models.CharField(default=1, choices=user_type_data, max_length=15)
    is_active = models.BooleanField(default=True)  # Add the is_active field here

    # Replace the default manager with the custom manager
    objects = CustomUserManager()

    def __str__(self):
        return self.username

class AdminHOD(models.Model):
    id = models.AutoField(primary_key=True)
    admin = models.OneToOneField(CustomUser,on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)    
    updated_at = models.DateTimeField(auto_now=True)
    objects = models.Manager()






   # Existing fields...
MARITAL_STATUS_CHOICES = [
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
    ]

ROLE_CHOICES = [
     ("Academic", "Academic"),
    ("Secretary", "Secretary"),
    ("Headmaster", "Headmaster"),
    ("Accountant", "Accountant"),
    ("Librarian", "Librarian"),
    ("Administrator", "Administrator"),
    ("Staff", "Staff"),
]

# Existing fields...
work_place_choices = [
        ('resa', 'Resa'),
        ('kahama', 'Kahama'),
        ('pemba', 'Pemba'),
        # Add more choices as needed
    ]

GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
      
    ]

class Department(models.Model):
    """Department model for staff assignment"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True, help_text="Short code for department")
    description = models.TextField(blank=True)
    head_of_department = models.ForeignKey(
        'Staffs',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='departments_heading'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'

    def __str__(self):
        return self.name


class Staffs(models.Model):
    id = models.AutoField(primary_key=True)
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='staff')
    middle_name = models.TextField(blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True)
    
    from datetime import date
    date_of_birth = models.DateField(blank=True, default=date(2000, 1, 1))
    phone_number = models.CharField(max_length=14, blank=True)
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICES, blank=True)
    # Remove the old role field since we're using TeachingAssignment model now
    work_place = models.CharField(max_length=50, choices=work_place_choices, blank=True)
    joining_date = models.DateField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    signature = models.ImageField(upload_to='signatures/', blank=True, null=True, help_text="Upload digital signature")
    
    # Department and position fields
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_members',
        help_text="Primary department"
    )
    
    position_title = models.CharField(
        max_length=100,
        blank=True,
        choices= ROLE_CHOICES,
        help_text="Official position/title (e.g., Senior Teacher, Head of Department)"
    )
    
    employment_type = models.CharField(
        max_length=50,
        choices=[
            ('permanent', 'Permanent'),
            ('contract', 'Contract'),
            ('part_time', 'Part Time'),
            ('temporary', 'Temporary'),
        ],
        default='permanent',
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = models.Manager()
    
    class Meta:
        verbose_name = 'Staff'
        verbose_name_plural = 'Staff'
    
    def clean(self):
        """Ensure unique staff full name (first_name + middle_name + last_name)."""
        if Staffs.objects.filter(
            admin__first_name=self.admin.first_name,
            middle_name=self.middle_name,
            admin__last_name=self.admin.last_name
        ).exclude(id=self.id).exists():
            raise ValidationError("A staff member with this full name already exists.")
    
    def get_full_name(self):
        return f"{self.admin.first_name} {self.middle_name} {self.admin.last_name}"

    def __str__(self):
        return f"{self.admin.first_name} {self.middle_name} {self.admin.last_name}"
    
    def get_teaching_assignments(self, academic_year=None):
        """Get all teaching assignments for this staff"""
        assignments = self.teaching_assignments.all()
        if academic_year:
            assignments = assignments.filter(academic_year=academic_year)
        return assignments
    
    def get_subjects_taught(self, academic_year=None):
        """Get unique subjects taught by this staff"""
        assignments = self.get_teaching_assignments(academic_year)
        return Subject.objects.filter(
            teaching_assignments__in=assignments
        ).distinct()
    
    def get_classes_taught(self, academic_year=None):
        """Get unique classes taught by this staff"""
        assignments = self.get_teaching_assignments(academic_year)
        return ClassLevel.objects.filter(
            teaching_assignments__in=assignments
        ).distinct()
    
    def get_streams_taught(self, academic_year=None):
        """Get unique streams taught by this staff"""
        assignments = self.get_teaching_assignments(academic_year)
        return StreamClass.objects.filter(
            teaching_assignments__in=assignments
        ).distinct()
    
    @property
    def is_class_teacher(self):
        """Check if staff is assigned as a class teacher for any class"""
        return self.teaching_assignments.filter(is_class_teacher=True, is_active=True).exists()
    
    def get_class_teacher_assignments(self, academic_year=None):
        """Get all class teacher assignments"""
        return self.teaching_assignments.filter(
            is_class_teacher=True,
            is_active=True
        ).select_related('class_level', 'stream_class', 'academic_year')
    

class TeachingAssignment(models.Model):
    ASSIGNMENT_TYPES = [
        ('class', 'Class Level'),
        ('stream', 'Stream Specific'),
        ('both', 'Class and Stream'),
    ]
    
    staff = models.ForeignKey(
        Staffs,
        on_delete=models.CASCADE,
        related_name='teaching_assignments'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='teaching_assignments'
    )
    
    # Class level assignment (e.g., teach Physics to all Form 1 classes)
    class_level = models.ForeignKey(
        ClassLevel,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='teaching_assignments'
    )
    
    # Specific stream assignment (e.g., teach Chemistry only to Form 2A)
    stream_class = models.ForeignKey(
        StreamClass,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='teaching_assignments'
    )
    
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name='teaching_assignments'
    )
    
    assignment_type = models.CharField(
        max_length=20,
        choices=ASSIGNMENT_TYPES,
        default='class'
    )
    
    is_class_teacher = models.BooleanField(
        default=False,
        help_text="Is this staff the class teacher for this class/stream?"
    )
    
    period_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of periods per week"
    )
    
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [
            ['staff', 'subject', 'class_level', 'academic_year'],
            ['staff', 'subject', 'stream_class', 'academic_year'],
        ]
        verbose_name = 'Teaching Assignment'
        verbose_name_plural = 'Teaching Assignments'
    
    def clean(self):
        """Validate the assignment"""
        if not self.class_level and not self.stream_class:
            raise ValidationError("Either class level or stream class must be specified")
        
        if self.stream_class and self.class_level:
            if self.stream_class.class_level != self.class_level:
                raise ValidationError("Stream class must belong to the specified class level")
        
        if self.is_class_teacher and self.subject:
            raise ValidationError("Class teacher assignment should not have a subject")
    
    def save(self, *args, **kwargs):
        """Auto-set assignment type based on fields"""
        if self.stream_class and not self.class_level:
            self.class_level = self.stream_class.class_level
        
        if self.stream_class:
            self.assignment_type = 'stream'
        elif self.class_level:
            self.assignment_type = 'class'
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        if self.stream_class:
            return f"{self.staff} -> {self.subject or 'Class Teacher'} ({self.stream_class})"
        return f"{self.staff} -> {self.subject or 'Class Teacher'} ({self.class_level})"
    

# accounts/models.py (add these models)
class SystemLog(models.Model):
    """System activity log for audit trail"""
    LOG_TYPES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('security', 'Security'),
        ('system', 'System'),
        ('error', 'Error'),
        ('warning', 'Warning'),
        ('info', 'Info'),
        ('success', 'Success'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    log_type = models.CharField(max_length=20, choices=LOG_TYPES)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'System Log'
        verbose_name_plural = 'System Logs'
    
    def __str__(self):
        return f"{self.get_log_type_display()} - {self.user or 'System'} - {self.timestamp}"


class Notification(models.Model):
    """System notifications for administrators"""
    NOTIFICATION_TYPES = [
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('info', 'Info'),
        ('security', 'Security'),
        ('system', 'System'),
    ]
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info')
    icon = models.CharField(max_length=50, blank=True)
    read = models.BooleanField(default=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    action_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
    
    def __str__(self):
        return f"{self.title} - {self.get_notification_type_display()}"
    
    def save(self, *args, **kwargs):
        # Auto-set icon based on type if not provided
        if not self.icon:
            icon_map = {
                'success': 'check-circle',
                'warning': 'exclamation-triangle',
                'error': 'x-circle',
                'info': 'info-circle',
                'security': 'shield-exclamation',
                'system': 'gear',
            }
            self.icon = icon_map.get(self.notification_type, 'bell')
        super().save(*args, **kwargs)

@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.user_type == 1:  # HOD
            AdminHOD.objects.create(admin=instance)


@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    if instance.user_type == 1:
        instance.adminhod.save()
  