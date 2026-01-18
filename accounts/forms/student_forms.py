# accounts/forms/student_forms.py
from datetime import datetime, date
import re
from django import forms
from accounts.models import GENDER_CHOICES
from students.models import RELATIONSHIP_CHOICES, STATUS_CHOICES, Student, Parent, PreviousSchool
from core.models import ClassLevel, StreamClass, Subject
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

class ParentStudentForm(forms.ModelForm):
    full_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter full name'
        })
    )
    
    relationship = forms.ChoiceField(
        choices=RELATIONSHIP_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control select2'
        })
    )
    
    first_phone_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 712345678'
        })
    )
    
    second_phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 712345678 (optional)'
        })
    )
    
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email address (optional)'
        })
    )
    
    address = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Enter complete address'
        })
    )
    
    is_fee_responsible = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'custom-control-input'
        })
    )
    
    class Meta:
        model = Parent
        fields = [
            'full_name', 'relationship', 'first_phone_number', 
            'second_phone_number', 'email', 'address', 'is_fee_responsible'
        ]
    
    def clean_first_phone_number(self):
        phone = self.cleaned_data.get('first_phone_number', '').strip()
        
        # Remove any non-digit characters
        phone = re.sub(r'\D', '', phone)
        
        # Tanzanian phone number validation (starting with 0 or 255)
        if phone.startswith('0'):
            phone = '255' + phone[1:]
        elif phone.startswith('255'):
            pass
        else:
            phone = '255' + phone
        
        # Check if it's a valid Tanzanian mobile number
        if not re.match(r'^255(6|7|8|9)\d{8}$', phone):
            raise ValidationError(_('Please enter a valid Tanzanian phone number.'))
        
        return phone
    
    def clean_second_phone_number(self):
        phone = self.cleaned_data.get('second_phone_number', '').strip()
        
        if phone:
            # Remove any non-digit characters
            phone = re.sub(r'\D', '', phone)
            
            # Tanzanian phone number validation
            if phone.startswith('0'):
                phone = '255' + phone[1:]
            elif phone.startswith('255'):
                pass
            else:
                phone = '255' + phone
            
            # Check if it's a valid Tanzanian mobile number
            if not re.match(r'^255(6|7|8|9)\d{8}$', phone):
                raise ValidationError(_('Please enter a valid Tanzanian phone number.'))
            
            # Check if second phone is same as first
            first_phone = self.cleaned_data.get('first_phone_number', '')
            if phone == first_phone:
                raise ValidationError(_('Second phone number cannot be the same as first phone number.'))
        
        return phone
    
    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        
        if email:
            # Check if email already exists for another parent
            existing_parent = Parent.objects.filter(email=email)
            if self.instance and self.instance.pk:
                existing_parent = existing_parent.exclude(pk=self.instance.pk)
            
            if existing_parent.exists():
                raise ValidationError(_('This email is already associated with another parent.'))
        
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Check for duplicate phone numbers
        first_phone = cleaned_data.get('first_phone_number')
        second_phone = cleaned_data.get('second_phone_number')
        
        if first_phone and second_phone and first_phone == second_phone:
            self.add_error('second_phone_number', 
                _('Second phone number cannot be the same as first phone number.')
            )
        
        return cleaned_data
    
class StudentForm(forms.ModelForm):
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'max': date.today().isoformat()
        }),
        required=False
    )
    
    # Optional subjects field
    optional_subjects = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.filter(is_active=True),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-control select2'}),
        help_text="Hold Ctrl/Cmd to select multiple subjects"
    )
    
    class Meta:
        model = Student
        fields = [
            'first_name', 'middle_name', 'last_name',
            'date_of_birth', 'gender', 'address',
            'profile_pic', 'physical_disabilities_condition',
            'class_level', 'stream_class',
            'previous_school', 'previous_class_level',
            'transfer_from_school',
            'registration_number', 'examination_number',
            'previously_examination_number',
            'status', 'is_active'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'profile_pic': forms.FileInput(attrs={'class': 'form-control'}),
            'physical_disabilities_condition': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'class_level': forms.Select(attrs={'class': 'form-control'}),
            'stream_class': forms.Select(attrs={'class': 'form-control'}),
            'previous_school': forms.Select(attrs={'class': 'form-control'}),
            'previous_class_level': forms.Select(attrs={'class': 'form-control'}),
            'transfer_from_school': forms.Select(attrs={'class': 'form-control'}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control'}),
            'examination_number': forms.TextInput(attrs={'class': 'form-control'}),
            'previously_examination_number': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'registration_number': 'Leave blank to auto-generate',
            'admission_year': 'Leave blank to use current year',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial for optional subjects if editing
        if self.instance and self.instance.pk:
            self.fields['optional_subjects'].initial = self.instance.optional_subjects.all()
        
        # Filter active class levels and streams
        self.fields['class_level'].queryset = ClassLevel.objects.filter(is_active=True)
        self.fields['stream_class'].queryset = StreamClass.objects.filter(is_active=True)
        self.fields['previous_class_level'].queryset = ClassLevel.objects.filter(is_active=True)
    
    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob:
            if dob > date.today():
                raise ValidationError("Date of birth cannot be in the future.")
            
            # Calculate age
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            
            if age < 3:
                raise ValidationError("Student must be at least 3 years old.")
            if age > 25:
                raise ValidationError("Student age seems unrealistic (over 25).")
        
        return dob
    
    def clean_registration_number(self):
        reg_no = self.cleaned_data.get('registration_number')
        if reg_no:
            # Check if registration number already exists (excluding current instance)
            query = Student.objects.filter(registration_number=reg_no)
            if self.instance and self.instance.pk:
                query = query.exclude(pk=self.instance.pk)
            
            if query.exists():
                raise ValidationError(f"Registration number '{reg_no}' already exists.")
        
        return reg_no
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate stream class matches class level
        class_level = cleaned_data.get('class_level')
        stream_class = cleaned_data.get('stream_class')
        
        if class_level and stream_class:
            if stream_class.class_level != class_level:
                raise ValidationError({
                    'stream_class': f"Selected stream class doesn't belong to {class_level.name}"
                })
        
        # Validate examination number uniqueness if provided
        exam_no = cleaned_data.get('examination_number')
        if exam_no:
            query = Student.objects.filter(examination_number=exam_no)
            if self.instance and self.instance.pk:
                query = query.exclude(pk=self.instance.pk)
            
            if query.exists():
                raise ValidationError({
                    'examination_number': f"Examination number '{exam_no}' already exists."
                })
        
        return cleaned_data
    
    def save(self, commit=True):
        # Get the instance without saving yet
        student = super().save(commit=False)
        
        # Handle optional subjects
        optional_subjects = self.cleaned_data.get('optional_subjects', [])
        
        if commit:
            # Save student first (this will trigger the save() method in model)
            student.save()
            
            # Save many-to-many relationships
            self.save_m2m()
            
            # Clear and set optional subjects
            student.optional_subjects.clear()
            if optional_subjects:
                student.optional_subjects.set(optional_subjects)
        
        return student


class StudentEditForm(forms.ModelForm):
    # Add custom fields for multi-select subjects
    subjects = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.none(),
        widget=forms.SelectMultiple(attrs={'class': 'select2'}),
        required=True,
        help_text="Select at least one subject"
    )
    
    class Meta:
        model = Student
        fields = [
            'first_name', 'middle_name', 'last_name',
            'date_of_birth', 'gender', 'address',
            'profile_pic', 'physical_disabilities_condition',
            'class_level', 'stream_class',
            'registration_number', 'examination_number',
            'previous_school', 'previous_class_level',
            'transfer_from_school', 'previously_examination_number',
            'status', 'is_active'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'max': timezone.now().date()}),
            'gender': forms.Select(attrs={'class': 'select2bs4'}),
            'address': forms.Textarea(attrs={'rows': 3}),
            'class_level': forms.Select(attrs={'class': 'select2', 'data-current-value': ''}),
            'stream_class': forms.Select(attrs={'class': 'select2', 'data-current-stream-id': ''}),
            'previous_school': forms.Select(attrs={'class': 'select2'}),
            'previous_class_level': forms.Select(attrs={'class': 'select2'}),
            'transfer_from_school': forms.Select(attrs={'class': 'select2'}),
            'status': forms.Select(attrs={'class': 'select2'}),
            'physical_disabilities_condition': forms.Textarea(attrs={'rows': 2}),
        }
        help_texts = {
            'registration_number': 'Registration number cannot be changed',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set registration number as readonly
        self.fields['registration_number'].widget.attrs['readonly'] = True
        
        # Filter querysets
        self.fields['previous_class_level'].queryset = ClassLevel.objects.filter(is_active=True)
        self.fields['transfer_from_school'].queryset = PreviousSchool.objects.all()
        self.fields['previous_school'].queryset = PreviousSchool.objects.all()
        
        # Get instance (student) if exists
        student = self.instance
        
        # If student exists, set up form fields
        if student and student.pk:
            # Set initial subjects
            if hasattr(student, 'optional_subjects'):
                self.fields['subjects'].initial = student.optional_subjects.all()
            
            # Filter subjects based on current class level
            if student.class_level:
                # Get subjects for the educational level
                subjects_qs = Subject.objects.filter(
                    educational_level=student.class_level.educational_level,
                    is_active=True
                ).order_by('name')
                self.fields['subjects'].queryset = subjects_qs
                
                # Filter streams for the current class level
                stream_qs = StreamClass.objects.filter(
                    class_level=student.class_level,
                    is_active=True
                ).order_by('stream_letter')
                
                # If student has a stream that's not active, include it
                if student.stream_class and not stream_qs.filter(id=student.stream_class.id).exists():
                    stream_qs = stream_qs | StreamClass.objects.filter(id=student.stream_class.id)
                
                self.fields['stream_class'].queryset = stream_qs
                
                # Store current values for JavaScript
                self.fields['class_level'].widget.attrs['data-current-value'] = str(student.class_level.id)
                if student.stream_class:
                    self.fields['stream_class'].widget.attrs['data-current-stream-id'] = str(student.stream_class.id)
            else:
                # If no class level, show all active subjects
                self.fields['subjects'].queryset = Subject.objects.filter(is_active=True)
                self.fields['stream_class'].queryset = StreamClass.objects.filter(is_active=True)
        else:
            # For new students, show no subjects initially
            self.fields['subjects'].queryset = Subject.objects.none()
            self.fields['stream_class'].queryset = StreamClass.objects.none()
        
        # Set today's date as max for date of birth
        self.fields['date_of_birth'].widget.attrs['max'] = timezone.now().date().isoformat()
        
        # Add form-control class to all fields
        for field_name, field in self.fields.items():
            if field_name != 'is_active':  # Don't add to checkbox
                field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'
    
    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob:
            if dob > timezone.now().date():
                raise ValidationError("Date of birth cannot be in the future.")
            
            # Calculate age
            today = timezone.now().date()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            
            if age < 3:
                raise ValidationError("Student must be at least 3 years old.")
            elif age > 25:
                raise ValidationError("Student age seems unrealistic (over 25 years).")
        
        return dob
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate that at least one subject is selected
        subjects = cleaned_data.get('subjects')
        if not subjects:
            raise ValidationError({
                'subjects': 'At least one subject must be selected.'
            })
        
        # Validate class level and stream compatibility
        class_level = cleaned_data.get('class_level')
        stream_class = cleaned_data.get('stream_class')
        
        if stream_class and class_level:
            if stream_class.class_level != class_level:
                raise ValidationError({
                    'stream_class': f'Selected stream "{stream_class}" does not belong to class level "{class_level}".'
                })
        
        # Validate registration number uniqueness (if being changed)
        registration_number = cleaned_data.get('registration_number')
        if registration_number and self.instance.pk:
            if Student.objects.filter(registration_number=registration_number).exclude(pk=self.instance.pk).exists():
                raise ValidationError({
                    'registration_number': 'This registration number is already assigned to another student.'
                })
        
        return cleaned_data
    
    def save(self, commit=True):
        # Get the instance without saving yet
        student = super().save(commit=False)
        
        # Handle profile picture removal
        remove_profile = self.data.get('remove_profile_pic') == 'on'
        if remove_profile and student.profile_pic:
            student.profile_pic.delete(save=False)
            student.profile_pic = None
        
        # Save the student instance
        if commit:
            student.save()
            
            # Save many-to-many relationships
            self.save_m2m()
            
            # Update subjects
            subjects = self.cleaned_data.get('subjects', [])
            if subjects:
                student.optional_subjects.set(subjects)
        
        return student
    
    
class ParentForm(forms.ModelForm):
    student_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    
    class Meta:
        model = Parent
        fields = ['full_name', 'relationship', 'address', 'email', 
                 'first_phone_number', 'second_phone_number', 'is_fee_responsible']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 4}),
            'full_name': forms.TextInput(attrs={
                'placeholder': 'Enter full name',
                'class': 'form-control'
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': 'Enter email address',
                'class': 'form-control'
            }),
            'first_phone_number': forms.TextInput(attrs={
                'placeholder': 'e.g., 712 345 678',
                'class': 'form-control',
                'pattern': '[0-9]{9}',
                'maxlength': '9'
            }),
            'second_phone_number': forms.TextInput(attrs={
                'placeholder': 'e.g., 712 345 678',
                'class': 'form-control',
                'pattern': '[0-9]{9}',
                'maxlength': '9'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.student = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)
        
        if self.student:
            self.fields['student_id'].initial = self.student.id
        
        # Add form-control class to all fields
        for field_name, field in self.fields.items():
            if field_name not in ['is_fee_responsible', 'student_id']:  # Don't add to checkbox/hidden
                field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'
        
        # Make relationship field required
        self.fields['relationship'].required = True
    
    def clean_first_phone_number(self):
        phone = self.cleaned_data.get('first_phone_number')
        if phone:
            # Remove any spaces and clean
            phone = self._clean_phone_number(phone)
            
            # Validate it's 9 digits
            if not phone.isdigit() or len(phone) != 9:
                raise ValidationError('Phone number must be 9 digits (e.g., 712345678)')
            
            # Format with spaces for display
            phone = f'{phone[:3]} {phone[3:6]} {phone[6:]}'
        
        return phone
    
    def clean_second_phone_number(self):
        phone = self.cleaned_data.get('second_phone_number')
        if phone:
            # Remove any spaces
            phone = self._clean_phone_number(phone)
            
            # Validate it's 9 digits
            if not phone.isdigit() or len(phone) != 9:
                raise ValidationError('Phone number must be 9 digits (e.g., 712345678)')
            
            # Format with spaces for display
            phone = f'{phone[:3]} {phone[3:6]} {phone[6:]}'
        
        return phone
    
    def _clean_phone_number(self, phone):
        """Helper method to clean phone numbers"""
        # Remove all non-digits
        phone = ''.join(filter(str.isdigit, phone))
        
        # Remove country code if present (255)
        if phone.startswith('255'):
            phone = phone[3:]
        
        return phone
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower().strip()
        return email
    
    def clean_full_name(self):
        """Clean and format full name"""
        full_name = self.cleaned_data.get('full_name')
        if full_name:
            # Title case the name
            full_name = full_name.strip()
            full_name = ' '.join(word.capitalize() for word in full_name.split())
        return full_name
    
    def clean_relationship(self):
        """Validate relationship field"""
        relationship = self.cleaned_data.get('relationship')
        if not relationship:
            raise ValidationError('Relationship is required')
        return relationship
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Ensure at least one phone number is provided
        if not cleaned_data.get('first_phone_number') and not cleaned_data.get('second_phone_number'):
            raise ValidationError({
                'first_phone_number': 'At least one phone number is required.'
            })
        
        # Prevent duplicate phone numbers
        first_phone = cleaned_data.get('first_phone_number')
        second_phone = cleaned_data.get('second_phone_number')
        
        if first_phone and second_phone and first_phone == second_phone:
            raise ValidationError({
                'second_phone_number': 'Second phone number cannot be the same as first phone number.'
            })
        
        # Check for duplicate parent-student relationship
        self._validate_unique_parent_student(cleaned_data)
        
        # Check for duplicate phone numbers across different parents
        self._validate_unique_phone_numbers(cleaned_data)
        
        return cleaned_data
    
    def _validate_unique_parent_student(self, cleaned_data):
        """
        Validate that this parent-student combination is unique.
        Prevent adding the same parent (by name + phone) to the same student multiple times.
        """
        if not self.student:
            return
        
        full_name = cleaned_data.get('full_name')
        first_phone = cleaned_data.get('first_phone_number')
        relationship = cleaned_data.get('relationship')
        
        if not full_name or not relationship:
            return
        
        # Normalize phone for comparison
        first_phone_clean = self._clean_phone_number(first_phone) if first_phone else None
        
        # Check for existing parent with same name and phone for this student
        existing_parents = Parent.objects.filter(
            students=self.student,
            full_name__iexact=full_name,
            relationship=relationship
        )
        
        # Exclude current instance if editing
        if self.instance and self.instance.pk:
            existing_parents = existing_parents.exclude(pk=self.instance.pk)
        
        # If we have phone number, also check by phone
        if first_phone_clean:
            existing_by_phone = Parent.objects.filter(
                students=self.student,
                first_phone_number__icontains=first_phone_clean.replace(' ', '')
            )
            if self.instance and self.instance.pk:
                existing_by_phone = existing_by_phone.exclude(pk=self.instance.pk)
            
            if existing_by_phone.exists():
                raise ValidationError(
                    f"A parent with phone number {first_phone} is already registered for this student."
                )
        
        if existing_parents.exists():
            raise ValidationError(
                f"A parent named {full_name} with relationship '{relationship}' is already registered for this student."
            )
    
    def _validate_unique_phone_numbers(self, cleaned_data):
        """
        Validate that phone numbers are not shared across different parents for the same student.
        Also check if phone numbers are already associated with other students.
        """
        if not self.student:
            return
        
        first_phone = cleaned_data.get('first_phone_number')
        second_phone = cleaned_data.get('second_phone_number')
        
        # Clean phone numbers for comparison
        first_phone_clean = self._clean_phone_number(first_phone) if first_phone else None
        second_phone_clean = self._clean_phone_number(second_phone) if second_phone else None
        
        phone_numbers_to_check = []
        if first_phone_clean:
            phone_numbers_to_check.append(('first_phone_number', first_phone_clean))
        if second_phone_clean:
            phone_numbers_to_check.append(('second_phone_number', second_phone_clean))
        
        for field_name, phone_clean in phone_numbers_to_check:
            # Find parents with this phone number (excluding current instance if editing)
            parents_with_same_phone = Parent.objects.filter(
                Q(first_phone_number__icontains=phone_clean) |
                Q(second_phone_number__icontains=phone_clean)
            )
            
            if self.instance and self.instance.pk:
                parents_with_same_phone = parents_with_same_phone.exclude(pk=self.instance.pk)
            
            for parent in parents_with_same_phone:
                # Check if this parent is already associated with our student
                if parent.students.filter(id=self.student.id).exists():
                    raise ValidationError({
                        field_name: f'Phone number {phone_clean} is already registered for this student under {parent.full_name}.'
                    })
                
                # Check if phone belongs to a parent of a different student
                other_students = parent.students.exclude(id=self.student.id)
                if other_students.exists():
                    student_names = ', '.join([s.full_name for s in other_students[:3]])
                    if other_students.count() > 3:
                        student_names += f' and {other_students.count() - 3} more'
                    
                    raise ValidationError({
                        field_name: f'Phone number {phone_clean} is already registered for other student(s): {student_names}.'
                    })
    
    def save(self, commit=True):
        """Save the parent and associate with student"""
        parent = super().save(commit=False)
        
        if commit:
            parent.save()
            
            # Associate with student if provided
            if self.student:
                parent.students.add(self.student)
                parent.save()
                
                # If this parent is fee responsible, ensure no other parent is
                if parent.is_fee_responsible:
                    # Remove fee responsibility from other parents of this student
                    self.student.parents.filter(is_fee_responsible=True).exclude(id=parent.id).update(is_fee_responsible=False)
        
        return parent
    
    
class PreviousSchoolForm(forms.ModelForm):
    """Form for creating and updating previous school records"""
    
    class Meta:
        model = PreviousSchool
        fields = ['name', 'school_level', 'location']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'School Name',
                'required': True
            }),
            'school_level': forms.Select(attrs={
                'class': 'form-control'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Location'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        school_level = cleaned_data.get('school_level')
        
        if not name:
            raise forms.ValidationError('School name is required.')
        
        if not school_level:
            raise forms.ValidationError('School level is required.')
        
        return cleaned_data
class StudentFilterForm(forms.Form):
    class_level = forms.ModelChoiceField(
        queryset=ClassLevel.objects.filter(is_active=True),
        required=False,
        label="Class Level",
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    
    stream = forms.ModelChoiceField(
        queryset=StreamClass.objects.none(),
        required=False,
        label="Stream",
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + list(STATUS_CHOICES),
        required=False,
        label="Status",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    gender = forms.ChoiceField(
        choices=[('', 'All Gender')] + list(GENDER_CHOICES),
        required=False,
        label="Gender",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    search = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, registration number...'
        })
    )
    
    date_from = forms.DateField(
        required=False,
        label="From Date",
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'max': timezone.now().date().isoformat()
        })
    )
    
    date_to = forms.DateField(
        required=False,
        label="To Date",
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'max': timezone.now().date().isoformat()
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Update stream queryset based on selected class
        if 'class_level' in self.data:
            try:
                class_level_id = int(self.data.get('class_level'))
                self.fields['stream'].queryset = StreamClass.objects.filter(
                    class_level_id=class_level_id,
                    is_active=True
                ).order_by('stream_letter')
            except (ValueError, TypeError):
                self.fields['stream'].queryset = StreamClass.objects.none()
        else:
            self.fields['stream'].queryset = StreamClass.objects.none()