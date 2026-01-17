# Quick Reference - Form Implementation Examples

## Using StudentForm in Views

```python
from accounts.forms.student_forms import StudentForm, ParentForm, PreviousSchoolForm
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

@login_required
def students_add(request):
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES)
        if form.is_valid():
            student = form.save()
            # Handle many-to-many relationships
            parents_ids = request.POST.getlist('parents')
            if parents_ids:
                student.parents.set(parents_ids)
            
            subject_ids = request.POST.getlist('optional_subjects')
            if subject_ids:
                student.optional_subjects.set(subject_ids)
            
            return JsonResponse({
                'success': True,
                'message': f'Student {student.full_name} added successfully!'
            })
        else:
            errors = {field: error[0] for field, error in form.errors.items()}
            return JsonResponse({
                'success': False,
                'errors': errors
            })
    
    form = StudentForm()
    context = {
        'form': form,
        'class_levels': ClassLevel.objects.filter(is_active=True),
        'stream_classes': StreamClass.objects.filter(is_active=True),
        'subjects': Subject.objects.filter(is_active=True),
        'previous_schools': PreviousSchool.objects.all(),
        'parents': Parent.objects.all(),
    }
    return render(request, 'admin/students/student_add.html', context)


@login_required
def students_ajax(request):
    """Handle AJAX requests for student operations"""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'delete':
            student_id = request.POST.get('id')
            student = get_object_or_404(Student, id=student_id)
            student_name = student.full_name
            student.delete()
            return JsonResponse({'success': True, 'message': f'Student {student_name} deleted!'})
        
        elif action == 'get_student':
            student_id = request.POST.get('id')
            student = get_object_or_404(Student, id=student_id)
            return JsonResponse({
                'success': True,
                'student': {
                    'id': student.id,
                    'full_name': student.full_name,
                    'registration_number': student.registration_number,
                    'class_level': student.class_level.name if student.class_level else '',
                    'status': student.status,
                }
            })
    
    return JsonResponse({'success': False})
```

---

## Using StaffForm in Views

```python
from accounts.forms.staff_forms import StaffForm, StaffUserForm
from accounts.models import CustomUser, Staffs

@login_required
def staff_add(request):
    if request.method == 'POST':
        try:
            # Create user account first
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password,
                user_type=2,  # Staff
                first_name=first_name,
                last_name=last_name
            )
            
            # Create staff profile
            staff = Staffs.objects.create(
                admin=user,
                middle_name=request.POST.get('middle_name', ''),
                gender=request.POST.get('gender'),
                phone_number=request.POST.get('phone_number', ''),
                role=request.POST.get('role'),
                marital_status=request.POST.get('marital_status', ''),
                joining_date=request.POST.get('joining_date')
            )
            
            # Handle file uploads
            if 'profile_picture' in request.FILES:
                staff.profile_picture = request.FILES['profile_picture']
                staff.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Staff member {first_name} {last_name} added successfully!'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error adding staff: {str(e)}'
            })
    
    context = {
        'role_choices': Staffs._meta.get_field('role').choices,
        'gender_choices': Staffs._meta.get_field('gender').choices,
    }
    return render(request, 'admin/staff/add.html', context)
```

---

## Using UserCreateForm in Views

```python
from accounts.forms.user_forms import UserCreateForm, UserEditForm
from accounts.models import CustomUser

@login_required
def users_add(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            return JsonResponse({
                'success': True,
                'message': f'User "{user.username}" created successfully!',
                'redirect': reverse('admin:admin_users_list')
            })
        else:
            errors = {field: error[0] for field, error in form.errors.items()}
            return JsonResponse({
                'success': False,
                'errors': errors
            })
    
    form = UserCreateForm()
    context = {
        'form': form,
        'user_type_choices': CustomUser._meta.get_field('user_type').choices,
    }
    return render(request, 'admin/users/add.html', context)


@login_required
def users_edit(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return JsonResponse({
                'success': True,
                'message': f'User "{user.username}" updated successfully!'
            })
        else:
            errors = {field: error[0] for field, error in form.errors.items()}
            return JsonResponse({
                'success': False,
                'errors': errors
            })
    
    form = UserEditForm(instance=user)
    context = {
        'form': form,
        'user': user,
    }
    return render(request, 'admin/users/edit.html', context)
```

---

## Form Template Usage in Views

```python
# Context needed for student_add.html
context = {
    'form': StudentForm(),
    'class_levels': ClassLevel.objects.filter(is_active=True),
    'stream_classes': StreamClass.objects.filter(is_active=True),
    'subjects': Subject.objects.filter(is_active=True),
    'previous_schools': PreviousSchool.objects.all(),
    'parents': Parent.objects.all(),
    'status_choices': Student.STATUS_CHOICES,
    'gender_choices': Student.GENDER_CHOICES,
}

# Context needed for staff/add.html
context = {
    'role_choices': Staffs._meta.get_field('role').choices,
    'gender_choices': Staffs._meta.get_field('gender').choices,
}

# Context needed for users/add.html
context = {
    'user_type_choices': CustomUser._meta.get_field('user_type').choices,
}
```

---

## Form Validation Examples

```python
# In your view, handle form validation errors
if form.is_valid():
    # Save the form
    instance = form.save()
else:
    # Form has errors
    error_messages = {}
    for field, errors in form.errors.items():
        error_messages[field] = errors[0]  # Get first error
    
    return JsonResponse({
        'success': False,
        'errors': error_messages
    })
```

---

## AJAX Data Submission

```javascript
// JavaScript example for form submission via AJAX
document.getElementById('studentForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    
    fetch('/admin/students/add/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(data.message);
            window.location.href = data.redirect_url;
        } else {
            // Display errors
            Object.keys(data.errors).forEach(field => {
                const errorElement = document.querySelector(`[name="${field}"]`);
                if (errorElement) {
                    errorElement.classList.add('is-invalid');
                    const feedback = document.createElement('div');
                    feedback.className = 'invalid-feedback';
                    feedback.textContent = data.errors[field];
                    errorElement.parentNode.appendChild(feedback);
                }
            });
        }
    });
});
```

---

## Model Integration

### Ensure models have these methods/properties:

```python
class Student(models.Model):
    # Existing fields...
    
    @property
    def full_name(self):
        return f'{self.first_name} {self.middle_name} {self.last_name}'.strip()
    
    @property
    def age(self):
        if self.date_of_birth:
            today = timezone.now().date()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < 
                (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None
    
    class Meta:
        ordering = ['registration_number']

class Parent(models.Model):
    # Existing fields...
    
    def __str__(self):
        student_names = ", ".join([s.full_name for s in self.students.all()])
        return f"{self.full_name} - {student_names if student_names else 'No Students'}"

class Staffs(models.Model):
    # Existing fields...
    
    def __str__(self):
        return f"{self.admin.first_name} {self.admin.last_name}"
```

---

## Testing Forms

```python
# Django test example
from django.test import TestCase
from accounts.forms.student_forms import StudentForm

class StudentFormTest(TestCase):
    def test_valid_student_form(self):
        form = StudentForm(data={
            'first_name': 'John',
            'middle_name': 'Michael',
            'last_name': 'Doe',
            'gender': 'male',
            'status': 'active'
        })
        self.assertTrue(form.is_valid())
    
    def test_invalid_student_form_missing_name(self):
        form = StudentForm(data={
            'first_name': '',
            'last_name': '',
        })
        self.assertFalse(form.is_valid())
```

---

## Helpful Snippets

### Get all form field choices dynamically
```python
STATUS_CHOICES = Student._meta.get_field('status').choices
GENDER_CHOICES = Student._meta.get_field('gender').choices
ROLE_CHOICES = Staffs._meta.get_field('role').choices
```

### Render form fields individually in template
```django
<!-- Render specific form field -->
<div class="mb-3">
    {{ form.first_name.label_tag }}
    {{ form.first_name }}
    {% if form.first_name.errors %}
        <div class="text-danger">{{ form.first_name.errors.0 }}</div>
    {% endif %}
</div>

<!-- Render all form fields -->
{% for field in form %}
    <div class="mb-3">
        {{ field.label_tag }}
        {{ field }}
        {% if field.errors %}
            <div class="text-danger">{{ field.errors.0 }}</div>
        {% endif %}
    </div>
{% endfor %}
```

---

*For more details, refer to FORMS_TEMPLATES_URLS_GUIDE.md*
