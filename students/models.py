from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from accounts.models import GENDER_CHOICES, CustomUser, Staffs
from core.models import AcademicYear, ClassLevel, Combination, StreamClass, Subject

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

    # Academic info & Relationships
    # Link to AcademicYear (The year the student joined/is currently registered in)
    academic_year = models.ForeignKey(
        AcademicYear, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='students'
    )

    combination = models.ForeignKey(
        Combination,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students'
    )
    
    class_level = models.ForeignKey(ClassLevel, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    stream_class = models.ForeignKey(StreamClass, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    
    previous_school = models.ForeignKey(PreviousSchool, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    previous_class_level = models.ForeignKey(ClassLevel, on_delete=models.SET_NULL, null=True, blank=True, related_name='previous_students')
    transfer_from_school = models.ForeignKey(PreviousSchool, on_delete=models.SET_NULL, null=True, blank=True, related_name='transferred_students')
    
    optional_subjects = models.ManyToManyField(Subject, blank=True, related_name='optional_students')

    # Identification
    registration_number = models.CharField(max_length=30, unique=True, blank=True, null=True)
    examination_number = models.CharField(max_length=30, null=True, blank=True)
    previously_examination_number = models.CharField(max_length=30, null=True, blank=True)

    # Auto-increment logic
    serial_number = models.PositiveIntegerField(editable=False, null=True, blank=True)
    admission_year = models.IntegerField(null=True, blank=True, help_text="Generated from Academic Year")

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

    def save(self, *args, **kwargs):
        from .models import AcademicYear  # Local import to prevent circularity

        # 1. Logic to set Academic Year and Admission Year
        if not self.academic_year:
            active_year = AcademicYear.objects.filter(is_active=True).first()
            if active_year:
                self.academic_year = active_year
        
        # Sync admission_year (integer) with the linked academic_year
        if self.academic_year and not self.admission_year:
            self.admission_year = self.academic_year.start_date.year
        elif not self.admission_year:
            self.admission_year = timezone.now().year

        # 2. Auto-generate serial number per admission year
        if not self.serial_number:
            last_student = Student.objects.filter(admission_year=self.admission_year).order_by('-serial_number').first()
            if last_student and last_student.serial_number:
                self.serial_number = last_student.serial_number + 1
            else:
                self.serial_number = 1

        # 3. Auto-generate registration number (S2348/SERIAL/YEAR)
        if not self.registration_number:
            school_code = 'S2348'
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



class AttendanceSession(models.Model):
    ATTENDANCE_TYPE_CHOICES = (
        ('CLASS', 'Class Wise'),
        ('SUBJECT', 'Subject Wise'),
    )

    class_level = models.ForeignKey(ClassLevel, on_delete=models.CASCADE)
    stream = models.ForeignKey(StreamClass, on_delete=models.CASCADE)

    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    attendance_type = models.CharField(
        max_length=10,
        choices=ATTENDANCE_TYPE_CHOICES
    )

    date = models.DateField()
    period = models.PositiveIntegerField(null=True, blank=True)

    # 🔹 timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.attendance_type == 'CLASS':
            return f"{self.class_level}-{self.stream} Class Attendance {self.date}"
        return f"{self.subject} - {self.class_level}-{self.stream} ({self.date})"

    

class StudentAttendance(models.Model):
    STATUS_CHOICES = (
        ('P', 'Present'),
        ('A', 'Absent'),
        ('L', 'Late'),
        ('E', 'Excused'),
    )

    attendance_session = models.ForeignKey(
        AttendanceSession,
        on_delete=models.CASCADE,
        related_name='attendances'
    )

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE
    )

    status = models.CharField(
        max_length=1,
        choices=STATUS_CHOICES
    )

    remark = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        unique_together = ('attendance_session', 'student')


class Hostel(models.Model):
    HOSTEL_TYPES = [
        ('boys', 'Boys'),
        ('girls', 'Girls'),
        ('mixed', 'Mixed'),
    ]

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    hostel_type = models.CharField(max_length=10, choices=HOSTEL_TYPES)

    max_students = models.PositiveIntegerField(
        help_text="Maximum students this hostel can hold"
    )

    # Fees
    total_fee = models.DecimalField(max_digits=10, decimal_places=2)

    PAYMENT_MODE = [
        ('yearly', 'Yearly'),
        ('monthly', 'Monthly'),
        ('installments', 'Installments'),
    ]
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODE)
    installments_count = models.PositiveIntegerField(default=1)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class HostelRoom(models.Model):
    hostel = models.ForeignKey(
        Hostel,
        on_delete=models.CASCADE,
        related_name='rooms'
    )

    room_number = models.CharField(max_length=20)
    capacity = models.PositiveIntegerField(
        help_text="How many students this room can hold"
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('hostel', 'room_number')

    def __str__(self):
        return f"{self.hostel.code} - Room {self.room_number}"


class Bed(models.Model):
    BED_TYPES = [
        ('single', 'Single'),
        ('bunk_upper', 'Bunk Upper'),
        ('bunk_lower', 'Bunk Lower'),
    ]

    room = models.ForeignKey(
        HostelRoom,
        on_delete=models.CASCADE,
        related_name='beds'
    )

    bed_number = models.CharField(max_length=20)
    bed_type = models.CharField(max_length=20, choices=BED_TYPES)

    is_occupied = models.BooleanField(default=False)

    class Meta:
        unique_together = ('room', 'bed_number')

    def __str__(self):
        return f"{self.room} - Bed {self.bed_number}"


class StudentHostelAllocation(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='hostel_allocations'
    )

    hostel = models.ForeignKey(
        Hostel,
        on_delete=models.CASCADE
    )

    # OPTIONAL (Level B)
    room = models.ForeignKey(
        HostelRoom,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # OPTIONAL (Level C)
    bed = models.ForeignKey(
        Bed,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE
    )

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    @property
    def total_fee(self):
        return self.hostel.total_fee


    @property
    def total_paid(self):
        return sum(payment.amount_paid for payment in self.payments.all())


    @property
    def balance(self):
        return self.total_fee - self.total_paid
    def __str__(self):
        return f"{self.student} - {self.hostel}"

class HostelInstallmentPlan(models.Model):
    hostel = models.ForeignKey(
        Hostel,
        on_delete=models.CASCADE,
        related_name='installment_plans'
    )

    installment_number = models.PositiveIntegerField()

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    # Date range (recurring yearly)
    start_month = models.PositiveIntegerField()
    start_day = models.PositiveIntegerField()

    end_month = models.PositiveIntegerField()
    end_day = models.PositiveIntegerField()

    class Meta:
        unique_together = ('hostel', 'installment_number')
        ordering = ['installment_number']

    def total_paid_by_student(self, allocation):
        return sum(
            payment.amount_paid
            for payment in self.student_payments.filter(allocation=allocation)
        )

    def remaining_amount(self, allocation):
        return self.amount - self.total_paid_by_student(allocation)
    
    def clean(self):
        if self.installment_number > 4:
            raise ValidationError("Maximum 4 installments allowed per hostel.")
    
    def __str__(self):
        return f"{self.hostel.name} - Installment {self.installment_number}"



class HostelPayment(models.Model):
    allocation = models.ForeignKey(
        StudentHostelAllocation,
        on_delete=models.CASCADE,
        related_name='payments'
    )

    installment_plan = models.ForeignKey(
        HostelInstallmentPlan,
        on_delete=models.CASCADE,
        related_name='student_payments'
    )

    PAYMENT_STATUS = [
    ('partial', 'Partial'),
    ('paid', 'Paid'),
]

    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default='partial'
    )


    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    payment_date = models.DateField(auto_now_add=True)

    receipt_number = models.CharField(
        max_length=50,
        unique=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        total_paid_for_installment = sum(
            payment.amount_paid
            for payment in HostelPayment.objects.filter(
                allocation=self.allocation,
                installment_plan=self.installment_plan
            )
        )

        if total_paid_for_installment + self.amount_paid > self.installment_plan.amount:
            raise ValidationError("Payment exceeds installment required amount.")
        
    def __str__(self):
        return f"{self.receipt_number} - {self.amount_paid}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        remaining = self.installment_plan.remaining_amount(self.allocation)

        if remaining <= 0:
            self.status = 'paid'
        else:
            self.status = 'partial'

        super().save(update_fields=['status'])
