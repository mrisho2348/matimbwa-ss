# accounts/forms/staff_forms.py
from django import forms
from accounts.models import Staffs, CustomUser, ROLE_CHOICES, GENDER_CHOICES


class StaffForm(forms.ModelForm):
    """Form for creating and updating staff records"""
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password (leave blank to keep current)'
        }),
        required=False,
        label='Password'
    )
    
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm Password'
        }),
        required=False,
        label='Confirm Password'
    )
    
    class Meta:
        model = Staffs
        fields = ['middle_name', 'gender', 'date_of_birth', 'phone_number', 
                  'marital_status', 'role', 'work_place', 'joining_date',
                  'profile_picture', 'signature']
        widgets = {
            'middle_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Middle Name'
            }),
            'gender': forms.Select(attrs={
                'class': 'form-control'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone Number'
            }),
            'marital_status': forms.Select(attrs={
                'class': 'form-control'
            }),
            'role': forms.Select(attrs={
                'class': 'form-control'
            }),
            'work_place': forms.Select(attrs={
                'class': 'form-control'
            }),
            'joining_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'signature': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and password != confirm_password:
            raise forms.ValidationError('Passwords do not match.')
        
        return cleaned_data


class StaffUserForm(forms.ModelForm):
    """Form for managing staff user account"""
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username',
                'required': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email Address',
                'required': True
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First Name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last Name'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email__iexact=email).exclude(id=self.instance.id).exists():
            raise forms.ValidationError('This email is already in use.')
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if CustomUser.objects.filter(username__iexact=username).exclude(id=self.instance.id).exists():
            raise forms.ValidationError('This username is already taken.')
        return username
