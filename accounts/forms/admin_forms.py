# accounts/forms/admin_forms.py
from django import forms
from django.contrib.auth.forms import UserChangeForm
from django.core.validators import EmailValidator
from accounts.models import CustomUser

class AdminProfileUpdateForm(UserChangeForm):
    """Form for updating admin profile information"""
    
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'username']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First Name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last Name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email Address'
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username'
            }),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        
        # Check if email is already in use (excluding current user)
        if CustomUser.objects.filter(email__iexact=email).exclude(id=self.instance.id).exists():
            raise forms.ValidationError('This email address is already in use.')
        
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        
        # Check if username is already in use (excluding current user)
        if CustomUser.objects.filter(username__iexact=username).exclude(id=self.instance.id).exists():
            raise forms.ValidationError('This username is already taken.')
        
        return username

class AdminSecuritySettingsForm(forms.Form):
    """Form for admin security settings"""
    
    enable_two_factor = forms.BooleanField(
        required=False,
        label='Enable Two-Factor Authentication',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    security_notifications = forms.BooleanField(
        required=False,
        label='Receive Security Notifications',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    login_notifications = forms.BooleanField(
        required=False,
        label='Notify on New Login',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    session_timeout = forms.IntegerField(
        required=False,
        label='Session Timeout (minutes)',
        min_value=5,
        max_value=1440,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    def clean_session_timeout(self):
        timeout = self.cleaned_data.get('session_timeout')
        if timeout and timeout < 15:
            raise forms.ValidationError('Session timeout must be at least 15 minutes.')
        return timeout

class AdminPreferencesForm(forms.ModelForm):
    """Form for admin preferences"""
    
    class Meta:
        model = CustomUser
        fields = []  # Add preference fields as they're created
        
    # Example preferences (you would add these to your CustomUser model)
    email_notifications = forms.BooleanField(
        required=False,
        label='Email Notifications',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    dashboard_layout = forms.ChoiceField(
        required=False,
        choices=[
            ('default', 'Default Layout'),
            ('compact', 'Compact Layout'),
            ('expanded', 'Expanded Layout'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    theme_preference = forms.ChoiceField(
        required=False,
        choices=[
            ('light', 'Light Theme'),
            ('dark', 'Dark Theme'),
            ('auto', 'Auto (System)'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )