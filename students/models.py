from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from accounts.models import GENDER_CHOICES, CustomUser
from core.models import ClassLevel, StreamClass, Subject

class PreviousSchool(models.Model):
    SCHOOL_LEVEL_CHOICES = [
        ('nursery', 'Nursery'),
        ('primary', 'Primary'),
        ('o-level', 'O-Level'),
        ('a-level', 'A-Level'),
    ]

    name = models.CharField(max_length=200)
    school_level = models.CharField(max_length=20, choices=SCHOOL_LEVEL_CHOICES)
    location = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Previous School'
        verbose_name_plural = 'Previous Schools'

    def __str__(self):
        return f"{self.name} ({self.school_level})"


STATUS_CHOICES = [
    ('active', 'Active'),
    ('completed', 'Completed'),
    ('suspended', 'Suspended'),
    ('withdrawn', 'Withdrawn'),
    ('transferred', 'Transferred'),
]

GENDER_CHOICES = [
    ('male', 'Male'),
    ('female', 'Female'),
    ('other', 'Other'),
]

class Student(models.Model):
    # Personal info
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    address = models.CharField(max_length=200, null=True, blank=True)
    profile_pic = models.FileField(upload_to='student_profile_pic', null=True, blank=True)
    physical_disabilities_condition = models.CharField(max_length=100, null=True, blank=True)

    # Academic info
    class_level = models.ForeignKey(ClassLevel, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    stream_class = models.ForeignKey(StreamClass, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    
    previous_school = models.ForeignKey('PreviousSchool', on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    previous_class_level = models.ForeignKey(ClassLevel, on_delete=models.SET_NULL, null=True, blank=True, related_name='previous_students')
    transfer_from_school = models.ForeignKey('PreviousSchool', on_delete=models.SET_NULL, null=True, blank=True, related_name='transferred_students')
    
    optional_subjects = models.ManyToManyField(Subject, blank=True, related_name='optional_students')

    # Identification
    registration_number = models.CharField(max_length=30, unique=True, blank=True, null=True)
    examination_number = models.CharField(max_length=30, null=True, blank=True)
    previously_examination_number = models.CharField(max_length=30, null=True, blank=True)

    # Auto-increment serial per year
    serial_number = models.PositiveIntegerField(editable=False, null=True, blank=True)
    admission_year = models.IntegerField(null=True, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_active = models.BooleanField(default=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Student'
        verbose_name_plural = 'Students'
        ordering = ['registration_number']
        constraints = [
            models.UniqueConstraint(fields=['first_name', 'middle_name', 'last_name'], name='unique_student')
        ]

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f'{self.first_name} {self.middle_name} {self.last_name}'.strip()

    @property
    def age(self):
        if self.date_of_birth:
            today = timezone.now().date()
            return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        return None

    # Get primary contact number from parent
    @property
    def primary_contact(self):
        fee_responsible = self.parents.filter(is_fee_responsible=True).first()
        if fee_responsible:
            return fee_responsible.phone
        first_parent = self.parents.first()
        return first_parent.phone if first_parent else None

    @property
    def emergency_contact(self):
        fee_responsible = self.parents.filter(is_fee_responsible=True).first()
        if fee_responsible and fee_responsible.first_phone_number:
            return fee_responsible.first_phone_number
        first_parent = self.parents.first()
        return first_parent.first_phone_number if first_parent else None

    def save(self, *args, **kwargs):
        # Set admission year if not provided
        if not self.admission_year:
            self.admission_year = timezone.now().year

        # Auto-generate serial number per year
        if not self.serial_number:
            last_student = Student.objects.filter(admission_year=self.admission_year).order_by('-serial_number').first()
            self.serial_number = 1 if not last_student else last_student.serial_number + 1

        # Auto-generate registration number if blank
        if not self.registration_number:
            school_code = 'S2348'  # Your school code
            serial_str = str(self.serial_number).zfill(4)
            self.registration_number = f'{school_code}/{serial_str}/{self.admission_year}'

        super().save(*args, **kwargs)
        

RELATIONSHIP_CHOICES = [
    ("Father", "Father"),
    ("Mother", "Mother"),
    ("Guardian", "Guardian"),
    ("Brother", "Brother"),
    ("Sister", "Sister"),
    ("Uncle", "Uncle"),
    ("Aunt", "Aunt"),
    ("Grandfather", "Grandfather"),
    ("Grandmother", "Grandmother"),
    ("Cousin", "Cousin"),
    ("Stepfather", "Stepfather"),
    ("Stepmother", "Stepmother"),
    ("Other", "Other"),
]

class Parent(models.Model):
    full_name = models.CharField(max_length=255)
    relationship = models.CharField(
        max_length=50,
        choices=RELATIONSHIP_CHOICES,
        default="Other"
    )
    address = models.CharField(max_length=255)    
    email = models.EmailField(blank=True, null=True)
    first_phone_number = models.CharField(max_length=20)
    second_phone_number = models.CharField(max_length=20, blank=True, null=True)    
    is_fee_responsible = models.BooleanField(default=False, help_text="Primary fee payer for this student")

    # Relation to students
    students = models.ManyToManyField('Student', related_name='parents')

    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Parent"
        verbose_name_plural = "Parents"
        ordering = ['full_name']

    def __str__(self):
        student_names = ", ".join([student.full_name for student in self.students.all()])
        return f"{self.full_name} ({self.relationship}) - {student_names if student_names else 'No Students'}"



