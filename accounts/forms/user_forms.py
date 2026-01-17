# accounts/forms/user_forms.py
from django import forms
from accounts.models import CustomUser


class UserCreateForm(forms.ModelForm):
    """Form for creating new system users"""
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'required': True
        }),
        label='Password'
    )
    
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm Password',
            'required': True
        }),
        label='Confirm Password'
    )
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 'user_type']
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
            'user_type': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and password != confirm_password:
            raise forms.ValidationError('Passwords do not match.')
        
        return cleaned_data
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('This email is already in use.')
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if CustomUser.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username


class UserEditForm(forms.ModelForm):
    """Form for editing existing users"""
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 'user_type', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email Address'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First Name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last Name'
            }),
            'user_type': forms.Select(attrs={
                'class': 'form-control'
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


class UserPasswordChangeForm(forms.Form):
    """Form for changing user password"""
    
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Current Password'
        }),
        label='Current Password'
    )
    
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New Password'
        }),
        label='New Password'
    )
    
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm New Password'
        }),
        label='Confirm Password'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password and new_password != confirm_password:
            raise forms.ValidationError('New passwords do not match.')
        
        if new_password and len(new_password) < 8:
            raise forms.ValidationError('New password must be at least 8 characters long.')
        
        return cleaned_data
