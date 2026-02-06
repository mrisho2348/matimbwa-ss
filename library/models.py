# library/models.py - Updated to support both staff and students
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import uuid
from accounts.models import Staffs
from students.models import Student
from django.dispatch import receiver

class BookCategory(models.Model):
    """Categories for books (e.g., Science, Literature, Reference)"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True, help_text="Category code (e.g., SCI, LIT, REF)")
    description = models.TextField(blank=True)   
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Book Category'
        verbose_name_plural = 'Book Categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Book(models.Model):
    """Book information model"""
    BOOK_STATUS_CHOICES = [
        ('available', 'Available'),
        ('borrowed', 'Borrowed'),
        ('reserved', 'Reserved'),
        ('damaged', 'Damaged'),
        ('lost', 'Lost'),
        ('under_maintenance', 'Under Maintenance'),
    ]
    
    BOOK_TYPE_CHOICES = [
        ('textbook', 'Textbook'),
        ('reference', 'Reference Book'),
        ('fiction', 'Fiction'),
        ('non_fiction', 'Non-Fiction'),
        ('academic', 'Academic'),
        ('general', 'General'),
    ]
    
    # Basic Information
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200)
    isbn = models.CharField(max_length=20, unique=True, verbose_name="ISBN", blank=True, null=True)
    publisher = models.CharField(max_length=100, blank=True)
    publication_year = models.IntegerField(null=True, blank=True)
    edition = models.CharField(max_length=50, blank=True)
    
    # Classification
    category = models.ForeignKey(BookCategory, on_delete=models.SET_NULL, null=True, related_name='books')
    book_type = models.CharField(max_length=20, choices=BOOK_TYPE_CHOICES, default='textbook')
    
    # Identification
    accession_number = models.CharField(max_length=50, unique=True, help_text="Unique library accession number")
    barcode = models.CharField(max_length=50, unique=True, blank=True, null=True, help_text="Barcode for quick scanning")
    location_code = models.CharField(max_length=20, blank=True, help_text="Shelf location code")
    
    # Book Details
    pages = models.PositiveIntegerField(null=True, blank=True)
    language = models.CharField(max_length=50, default='English')
    description = models.TextField(blank=True)
    keywords = models.CharField(max_length=200, blank=True, help_text="Comma-separated keywords for search")
    
    # Physical Condition
    condition = models.CharField(max_length=20, choices=[
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('damaged', 'Damaged'),
    ], default='good')
    
    # Status
    status = models.CharField(max_length=20, choices=BOOK_STATUS_CHOICES, default='available')
    is_reference = models.BooleanField(default=False, help_text="Reference books cannot be borrowed")
    is_reserved = models.BooleanField(default=False)
    
    # Pricing for fines (per day)
    fine_amount = models.DecimalField(max_digits=10, decimal_places=2, default=500.00, 
                                     help_text="Fine per day for overdue (TZS)")
    
    # Availability
    total_copies = models.PositiveIntegerField(default=1)
    available_copies = models.PositiveIntegerField(default=1)
    borrowed_copies = models.PositiveIntegerField(default=0)
    
    # Timestamps
    date_added = models.DateField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Book'
        verbose_name_plural = 'Books'
        ordering = ['title', 'author']
        indexes = [
            models.Index(fields=['title', 'author']),
            models.Index(fields=['isbn']),
            models.Index(fields=['accession_number']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.title} by {self.author}"
    
    def clean(self):
        """Validate book data"""
        if self.available_copies > self.total_copies:
            raise ValidationError("Available copies cannot exceed total copies")
        if self.borrowed_copies > self.total_copies:
            raise ValidationError("Borrowed copies cannot exceed total copies")
        if self.pk:
            self.available_copies = self.total_copies - self.borrowed_copies
    
    def save(self, *args, **kwargs):
        if not self.accession_number:
            last_book = Book.objects.order_by('-id').first()
            last_number = int(last_book.accession_number.split('-')[-1]) if last_book and '-' in last_book.accession_number else 0
            self.accession_number = f"LIB-{self.category.code if self.category else 'GEN'}-{last_number + 1:06d}"
        
        if not self.barcode:
            self.barcode = str(uuid.uuid4().int)[:12]
        
        self.available_copies = self.total_copies - self.borrowed_copies
        
        if self.available_copies == 0:
            self.status = 'borrowed'
        elif self.status == 'borrowed' and self.available_copies > 0:
            self.status = 'available'
        
        super().save(*args, **kwargs)
    
    def is_available(self):
        """Check if book is available for borrowing"""
        return self.status == 'available' and self.available_copies > 0 and not self.is_reference
    
    def get_available_copies(self):
        """Get all available copies of this book"""
        return self.copies.filter(status='available')
    
    def update_copies_on_borrow(self):
        """Update copy counts when book is borrowed"""
        if self.available_copies > 0:
            self.borrowed_copies += 1
            self.available_copies = self.total_copies - self.borrowed_copies
            if self.available_copies == 0:
                self.status = 'borrowed'
            self.save(update_fields=['borrowed_copies', 'available_copies', 'status'])
            return True
        return False
    
    def update_copies_on_return(self):
        """Update copy counts when book is returned"""
        if self.borrowed_copies > 0:
            self.borrowed_copies -= 1
            self.available_copies = self.total_copies - self.borrowed_copies
            self.status = 'available' if self.available_copies > 0 else 'borrowed'
            self.save(update_fields=['borrowed_copies', 'available_copies', 'status'])
            return True
        return False


class BookCopy(models.Model):
    """Individual copy tracking for books"""
    COPY_STATUS_CHOICES = [
        ('available', 'Available'),
        ('borrowed', 'Borrowed'),
        ('reserved', 'Reserved'),
        ('damaged', 'Damaged'),
        ('lost', 'Lost'),
        ('under_maintenance', 'Under Maintenance'),
    ]
    
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='copies')
    copy_number = models.CharField(max_length=10, help_text="Copy number (e.g., 001, 002)")
    barcode = models.CharField(max_length=50, unique=True)
    accession_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=COPY_STATUS_CHOICES, default='available')
    condition = models.CharField(max_length=20, choices=[
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('damaged', 'Damaged'),
    ], default='good')
    notes = models.TextField(blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Book Copy'
        verbose_name_plural = 'Book Copies'
        unique_together = ['book', 'copy_number']
        ordering = ['book', 'copy_number']
    
    def __str__(self):
        return f"{self.book.title} - Copy {self.copy_number}"
    
    def is_available(self):
        """Check if this specific copy is available"""
        return self.status == 'available'
    
    def save(self, *args, **kwargs):
        if not self.barcode:
            self.barcode = str(uuid.uuid4().int)[:12]
        
        if not self.accession_number:
            temp_accession = f"{self.book.accession_number}-C{self.copy_number}"
            self.accession_number = temp_accession
        
        super().save(*args, **kwargs)
        
        # Generate unique accession number
        if self.accession_number.startswith(self.book.accession_number + "-C"):
            import re
            base = self.book.accession_number
            pattern = re.compile(rf'^{re.escape(base)}-C(\d+)$')
            existing_numbers = []
            
            for copy in BookCopy.objects.filter(book=self.book).exclude(id=self.id):
                match = pattern.match(copy.accession_number)
                if match:
                    try:
                        existing_numbers.append(int(match.group(1)))
                    except ValueError:
                        pass
            
            if existing_same_accession := BookCopy.objects.filter(
                accession_number=self.accession_number
            ).exclude(id=self.id).exists():
                next_num = max(existing_numbers) + 1 if existing_numbers else 1
                self.accession_number = f"{base}-C{next_num:03d}"
                super().save(update_fields=['accession_number'])
        
        super().save(*args, **kwargs)


class BorrowingRules(models.Model):
    """Rules for borrowing books"""
    BORROWER_TYPE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('staff', 'Staff'),
        ('guest', 'Guest'),
    ]
    
    borrower_type = models.CharField(max_length=20, choices=BORROWER_TYPE_CHOICES, unique=True)
    max_books_allowed = models.PositiveIntegerField(default=1, help_text="Maximum number of books that can be borrowed at once")
    borrowing_duration_days = models.PositiveIntegerField(default=7, help_text="Maximum borrowing period in days")
    renewal_allowed = models.BooleanField(default=True)
    max_renewals = models.PositiveIntegerField(default=1, help_text="Maximum number of renewals allowed")
    renewal_duration_days = models.PositiveIntegerField(default=7, help_text="Duration for each renewal in days")
    fine_per_day = models.DecimalField(max_digits=10, decimal_places=2, default=500.00, help_text="Fine per day for overdue (TZS)")
    max_fine_amount = models.DecimalField(max_digits=10, decimal_places=2, default=10000.00, help_text="Maximum fine amount (TZS)")
    can_borrow_reference = models.BooleanField(default=False, help_text="Can borrow reference books")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Borrowing Rule'
        verbose_name_plural = 'Borrowing Rules'
        ordering = ['borrower_type']
    
    def __str__(self):
        return f"{self.get_borrower_type_display()} Rules"
    
    def get_borrowing_duration(self):
        """Get borrowing duration in days"""
        return self.borrowing_duration_days
    
    def get_renewal_duration(self):
        """Get renewal duration in days"""
        return self.renewal_duration_days if self.renewal_allowed else 0


class BookBorrow(models.Model):
    """Record of book borrowing - supports both Staff and Student"""
    BORROW_STATUS_CHOICES = [
        ('active', 'Active'),
        ('returned', 'Returned'),
        ('overdue', 'Overdue'),
        ('lost', 'Lost'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Borrower Information (can be either Staff or Student)
    borrower_type = models.CharField(max_length=20, choices=[
        ('staff', 'Staff'),
        ('student', 'Student'),
    ])
    
    # Generic borrower fields (one will be filled based on borrower_type)
    staff_borrower = models.ForeignKey(
        Staffs, 
        on_delete=models.CASCADE, 
        related_name='book_borrows_staff',
        null=True, 
        blank=True
    )
    student_borrower = models.ForeignKey(
        Student, 
        on_delete=models.CASCADE, 
        related_name='book_borrows_student',
        null=True, 
        blank=True
    )
    
    # Book Information
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='borrows')
    book_copy = models.ForeignKey(
        BookCopy, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='borrows', 
        help_text="Specific copy borrowed"
    )
    
    # Borrowing Details
    borrow_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=BORROW_STATUS_CHOICES, default='active')
    
    # Book Details at time of borrowing (for record keeping)
    borrowed_book_title = models.CharField(max_length=200, blank=True)
    borrowed_book_author = models.CharField(max_length=200, blank=True)
    borrowed_accession_number = models.CharField(max_length=50, blank=True)
    borrowed_barcode = models.CharField(max_length=50, blank=True)
    
    # Renewal Information
    renewed_count = models.PositiveIntegerField(default=0)
    last_renewal_date = models.DateField(null=True, blank=True)
    
    # Fine Information
    fine_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    fine_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    fine_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    fine_notes = models.TextField(blank=True)
    
    # Issued by (always staff)
    issued_by = models.ForeignKey(
        Staffs, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='issued_borrows', 
        help_text="Librarian who issued the book"
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Book Borrow'
        verbose_name_plural = 'Book Borrows'
        ordering = ['-borrow_date', '-created_at']
        indexes = [
            models.Index(fields=['borrow_date', 'status']),
            models.Index(fields=['due_date', 'status']),
            models.Index(fields=['book', 'status']),
        ]
    
    def __str__(self):
        borrower_name = self.get_borrower_name()
        return f"{self.book.title} - {borrower_name} ({self.status})"
    
    def get_borrower(self):
        """Get the borrower object based on borrower_type"""
        if self.borrower_type == 'staff' and self.staff_borrower:
            return self.staff_borrower
        elif self.borrower_type == 'student' and self.student_borrower:
            return self.student_borrower
        return None
    
    def get_borrower_name(self):
        """Get borrower's name"""
        borrower = self.get_borrower()
        if not borrower:
            return "Unknown Borrower"
        
        if hasattr(borrower, 'get_full_name'):
            return borrower.get_full_name()
        elif hasattr(borrower, 'full_name'):
            return borrower.full_name
        elif hasattr(borrower, 'username'):
            return borrower.username
        return str(borrower)
    
    def get_borrower_display(self):
        """Get borrower display with type"""
        borrower_name = self.get_borrower_name()
        borrower_type_display = "Staff" if self.borrower_type == 'staff' else "Student"
        return f"{borrower_name} ({borrower_type_display})"
    
    def clean(self):
        """Validate borrowing rules"""
        # Ensure only one borrower type is set
        if self.borrower_type == 'staff' and not self.staff_borrower:
            raise ValidationError("Staff borrower must be selected for staff borrow")
        if self.borrower_type == 'student' and not self.student_borrower:
            raise ValidationError("Student borrower must be selected for student borrow")
        
        # Get borrower and rules
        borrower = self.get_borrower()
        if not borrower:
            raise ValidationError("Borrower not found")
        
        # Determine borrower type for rules
        rule_borrower_type = 'student' if self.borrower_type == 'student' else 'teacher'
        
        # Get borrowing rules
        try:
            rules = BorrowingRules.objects.get(borrower_type=rule_borrower_type)
        except BorrowingRules.DoesNotExist:
            rules = BorrowingRules.objects.filter(borrower_type='student').first()
        
        if not rules:
            raise ValidationError("No borrowing rules found for this user type")
        
        # Check if book is reference and user can borrow reference
        if self.book.is_reference and not rules.can_borrow_reference:
            raise ValidationError("Reference books cannot be borrowed")
        
        # Check if user has reached max books limit
        if self.borrower_type == 'staff':
            active_borrows = BookBorrow.objects.filter(
                staff_borrower=self.staff_borrower,
                status__in=['active', 'overdue']
            ).count()
        else:
            active_borrows = BookBorrow.objects.filter(
                student_borrower=self.student_borrower,
                status__in=['active', 'overdue']
            ).count()
        
        if active_borrows >= rules.max_books_allowed and not self.pk:
            raise ValidationError(f"You can only borrow {rules.max_books_allowed} book(s) at a time")
    
    def save(self, *args, **kwargs):
        # Set due date based on borrower type if not set
        if not self.due_date:
            # Determine borrower type for rules
            rule_borrower_type = 'student' if self.borrower_type == 'student' else 'teacher'
            
            try:
                rules = BorrowingRules.objects.get(borrower_type=rule_borrower_type)
                self.due_date = timezone.now().date() + timedelta(days=rules.borrowing_duration_days)
            except BorrowingRules.DoesNotExist:
                self.due_date = timezone.now().date() + timedelta(days=7)
        
        # Store book details for record keeping
        if self.book:
            self.borrowed_book_title = self.book.title
            self.borrowed_book_author = self.book.author
            self.borrowed_accession_number = self.book.accession_number
            self.borrowed_barcode = self.book.barcode
        
        # Calculate fine balance
        self.fine_balance = self.fine_amount - self.fine_paid
        
        # Update status based on dates
        if self.actual_return_date:
            self.status = 'returned'
        elif self.due_date and self.due_date < timezone.now().date():
            self.status = 'overdue'
        
        super().save(*args, **kwargs)
    
    def calculate_overdue_days(self):
        """Calculate number of overdue days"""
        if self.status == 'returned' and self.actual_return_date:
            if self.actual_return_date > self.due_date:
                return (self.actual_return_date - self.due_date).days
        elif self.status in ['active', 'overdue']:
            if self.due_date < timezone.now().date():
                return (timezone.now().date() - self.due_date).days
        return 0
    
    def calculate_fine(self):
        """Calculate fine amount"""
        overdue_days = self.calculate_overdue_days()
        if overdue_days > 0:
            # Get fine per day from book or rules
            fine_per_day = self.book.fine_amount if self.book else Decimal('500.00')
            
            # Calculate fine
            fine_amount = Decimal(overdue_days) * fine_per_day
            
            # Apply maximum fine limit
            try:
                rule_borrower_type = 'student' if self.borrower_type == 'student' else 'teacher'
                rules = BorrowingRules.objects.get(borrower_type=rule_borrower_type)
                if fine_amount > rules.max_fine_amount:
                    fine_amount = rules.max_fine_amount
            except BorrowingRules.DoesNotExist:
                pass
            
            return fine_amount
        return Decimal('0.00')
    
    def update_fine(self):
        """Update fine amount"""
        self.fine_amount = self.calculate_fine()
        self.fine_balance = self.fine_amount - self.fine_paid
        
        if self.fine_amount > 0 and self.status == 'active':
            self.status = 'overdue'
        
        self.save(update_fields=['fine_amount', 'fine_balance', 'status'])
        return self.fine_amount
    
    def renew_book(self, renewed_by):
        """Renew the book borrowing"""
        # Determine borrower type for rules
        rule_borrower_type = 'student' if self.borrower_type == 'student' else 'teacher'
        
        try:
            rules = BorrowingRules.objects.get(borrower_type=rule_borrower_type)
        except BorrowingRules.DoesNotExist:
            rules = None
        
        # Check if renewal is allowed
        if not rules or not rules.renewal_allowed:
            raise ValidationError("Renewal is not allowed for this user type")
        
        # Check max renewals
        if self.renewed_count >= rules.max_renewals:
            raise ValidationError(f"Maximum renewals ({rules.max_renewals}) reached")
        
        # Check if book is reserved by someone else
        if self.book.is_reserved:
            raise ValidationError("Cannot renew. Book is reserved by another user")
        
        # Update renewal information
        self.renewed_count += 1
        self.last_renewal_date = timezone.now().date()
        
        # Extend due date
        renewal_days = rules.renewal_duration_days if rules else 7
        self.due_date = self.due_date + timedelta(days=renewal_days)
        
        # Update fine if any
        self.update_fine()
        
        self.save()
        
        # Create renewal record
        BookRenewal.objects.create(
            borrow=self,
            renewed_by=renewed_by,
            previous_due_date=self.due_date - timedelta(days=renewal_days),
            new_due_date=self.due_date
        )
        
        return True
    
    def return_book(self, return_date=None, condition=None, notes=None):
        """Return borrowed book"""
        if self.status == 'returned':
            raise ValidationError("Book is already returned")
        
        # Set return date
        self.actual_return_date = return_date or timezone.now().date()
        
        # Update book copies
        if self.book:
            self.book.update_copies_on_return()
        
        # Update book copy status if specific copy was borrowed
        if self.book_copy:
            if condition:
                self.book_copy.condition = condition
                self.book_copy.save()
        
        # Calculate final fine
        self.update_fine()
        self.status = 'returned'
        
        if notes:
            self.fine_notes = notes
        
        self.save()
        
        # Create return record
        BookReturn.objects.create(
            borrow=self,
            return_date=self.actual_return_date,
            condition=condition or 'good',
            notes=notes or ''
        )
        
        return True


# The rest of the models remain similar...
class BookRenewal(models.Model):
    """Record of book renewals"""
    borrow = models.ForeignKey(BookBorrow, on_delete=models.CASCADE, related_name='renewals')
    renewal_date = models.DateField(auto_now_add=True)
    renewed_by = models.ForeignKey(Staffs, on_delete=models.SET_NULL, null=True, 
                                  related_name='book_renewals')
    previous_due_date = models.DateField()
    new_due_date = models.DateField()
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Book Renewal'
        verbose_name_plural = 'Book Renewals'
        ordering = ['-renewal_date']
    
    def __str__(self):
        return f"Renewal for {self.borrow.book.title}"


class BookReturn(models.Model):
    """Record of book returns"""
    borrow = models.ForeignKey(BookBorrow, on_delete=models.CASCADE, related_name='returns')
    return_date = models.DateField()
    returned_by = models.ForeignKey(Staffs, on_delete=models.SET_NULL, null=True, 
                                   related_name='book_returns', help_text="Person who processed the return")
    condition = models.CharField(max_length=20, choices=[
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('damaged', 'Damaged'),
    ], default='good')
    notes = models.TextField(blank=True)
    fine_collected = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Book Return'
        verbose_name_plural = 'Book Returns'
        ordering = ['-return_date']
    
    def __str__(self):
        return f"Return of {self.borrow.book.title}"


class FinePayment(models.Model):
    """Record of fine payments"""
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('mobile', 'Mobile Money'),
        ('other', 'Other'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    borrow = models.ForeignKey(BookBorrow, on_delete=models.CASCADE, related_name='fine_payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField(auto_now_add=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cash')
    transaction_id = models.CharField(max_length=100, blank=True, help_text="Bank/Mobile transaction ID")
    receipt_number = models.CharField(max_length=50, unique=True)
    
    # Payer can be either Staff or Student
    payer_type = models.CharField(max_length=20, choices=[
        ('staff', 'Staff'),
        ('student', 'Student'),
    ], default='student')
    
    staff_payer = models.ForeignKey(
        Staffs, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='fine_payments_made_staff'
    )
    
    student_payer = models.ForeignKey(
        Student,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fine_payments_made_student'
    )
    
    received_by = models.ForeignKey(
        Staffs, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='fine_payments_received', 
        help_text="Staff who received payment"
    )
    
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='completed')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Fine Payment'
        verbose_name_plural = 'Fine Payments'
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"Payment of {self.amount} for {self.borrow.book.title}"
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            last_payment = FinePayment.objects.order_by('-id').first()
            last_number = int(last_payment.receipt_number.split('-')[-1]) if last_payment and '-' in last_payment.receipt_number else 0
            self.receipt_number = f"FP-{timezone.now().strftime('%Y%m')}-{last_number + 1:06d}"
        
        super().save(*args, **kwargs)
        
        if self.status == 'completed':
            self.borrow.fine_paid += self.amount
            self.borrow.fine_balance = self.borrow.fine_amount - self.borrow.fine_paid
            self.borrow.save()
    
    def get_payer(self):
        """Get the payer object based on payer_type"""
        if self.payer_type == 'staff' and self.staff_payer:
            return self.staff_payer
        elif self.payer_type == 'student' and self.student_payer:
            return self.student_payer
        return None
    
    def get_payer_name(self):
        """Get payer's name"""
        payer = self.get_payer()
        if not payer:
            return "Unknown Payer"
        
        if hasattr(payer, 'get_full_name'):
            return payer.get_full_name()
        elif hasattr(payer, 'full_name'):
            return payer.full_name
        elif hasattr(payer, 'username'):
            return payer.username
        return str(payer)


# Utility functions
def check_borrower_eligibility(user, book):
    """Check if user is eligible to borrow a book"""
    # Determine user type
    borrower_type = None
    if hasattr(user, 'staff'):
        borrower_type = 'teacher'  # Teacher type in rules
        borrower = user.staff
    elif hasattr(user, 'student'):
        borrower_type = 'student'
        borrower = user.student
    else:
        return False, "User type not supported for borrowing"
    
    # Get borrowing rules
    try:
        rules = BorrowingRules.objects.get(borrower_type=borrower_type)
    except BorrowingRules.DoesNotExist:
        return False, "No borrowing rules found for your user type"
    
    # Check active borrows
    if borrower_type == 'student':
        active_borrows = BookBorrow.objects.filter(
            student_borrower=borrower,
            status__in=['active', 'overdue']
        ).count()
    else:
        active_borrows = BookBorrow.objects.filter(
            staff_borrower=borrower,
            status__in=['active', 'overdue']
        ).count()
    
    if active_borrows >= rules.max_books_allowed:
        return False, f"You can only borrow {rules.max_books_allowed} book(s) at a time"
    
    # Check if book is available
    if not book.is_available():
        return False, "Book is not available for borrowing"
    
    # Check if book is reference and user can borrow reference
    if book.is_reference and not rules.can_borrow_reference:
        return False, "Reference books cannot be borrowed"
    
    return True, "Eligible to borrow"


# Signals
@receiver(models.signals.pre_save, sender=BookBorrow)
def update_book_status_on_borrow(sender, instance, **kwargs):
    """Update book status when borrowed"""
    if instance.status == 'active' and instance.book:
        instance.book.update_copies_on_borrow()
        if instance.book_copy:
            instance.book_copy.status = 'borrowed'
            instance.book_copy.save()


@receiver(models.signals.pre_save, sender=BookBorrow)
def update_book_status_on_return(sender, instance, **kwargs):
    """Update book status when returned"""
    if instance.status == 'returned' and instance.book:
        instance.book.update_copies_on_return()
        if instance.book_copy:
            instance.book_copy.status = 'available'
            instance.book_copy.save()