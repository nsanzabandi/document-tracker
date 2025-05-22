from django import forms
from django.contrib.auth.models import User
from .models import Division, Document, Staff
from django.core.exceptions import ValidationError

class DocumentForm(forms.ModelForm):
    division = forms.ModelChoiceField(
        queryset=Division.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select select2'})
    )
    
    receiver = forms.ModelChoiceField(
        queryset=Staff.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select select2'})
    )
    
    doc_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    follow_up = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    class Meta:
        model = Document
        fields = ['title', 'purpose', 'doc_date', 'follow_up', 'receiver', 'division']


class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    division = forms.ModelChoiceField(
        queryset=Division.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select select2'})
    )
    
    # Option 1: Select from existing staff
    staff_member = forms.ModelChoiceField(
        queryset=Staff.objects.all(),
        required=False,
        empty_label="-- Select existing staff member --",
        widget=forms.Select(attrs={'class': 'form-select select2'})
    )
    
    # Option 2: Type new full name
    full_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Or type full name'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
    
    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm_password")
        staff_member = cleaned_data.get("staff_member")
        full_name = cleaned_data.get("full_name")
        
        # Must provide either staff_member OR full_name
        if not staff_member and not full_name:
            raise ValidationError("Please either select an existing staff member or provide a full name.")
        
        if staff_member and full_name:
            raise ValidationError("Please choose either existing staff member OR type a new name, not both.")
        
        if User.objects.filter(username=username).exists():
            self.add_error('username', "This username is already taken.")
        
        if User.objects.filter(email=email).exists():
            self.add_error('email', "This email is already registered.")
        
        if password and confirm and password != confirm:
            self.add_error("confirm_password", "Passwords do not match")
        
        return cleaned_data


class AdminUserCreateForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,  # Not required when editing
        help_text="Leave blank to keep current password when editing"
    )
    division = forms.ModelChoiceField(queryset=Division.objects.all())
    
    # Option 1: Select from existing staff
    staff_member = forms.ModelChoiceField(
        queryset=Staff.objects.all(),
        required=False,
        empty_label="-- Select existing staff member --",
        widget=forms.Select(attrs={'class': 'form-select select2'})
    )
    
    # Option 2: Type new full name
    full_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Or type full name'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'division']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If editing existing user, populate current staff info
        if self.instance.pk:
            try:
                profile = self.instance.profile
                # Check if user is linked to a staff member
                staff_member = Staff.objects.filter(user=self.instance).first()
                if staff_member:
                    self.fields['staff_member'].initial = staff_member
                else:
                    # If no staff link, show current first_name + last_name as full_name
                    current_name = f"{self.instance.first_name} {self.instance.last_name}".strip()
                    if current_name:
                        self.fields['full_name'].initial = current_name
            except:
                pass
    
    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        email = cleaned_data.get("email")
        staff_member = cleaned_data.get("staff_member")
        full_name = cleaned_data.get("full_name")
        
        # Must provide either staff_member OR full_name
        if not staff_member and not full_name:
            raise ValidationError("Please either select an existing staff member or provide a full name.")
        
        if staff_member and full_name:
            raise ValidationError("Please choose either existing staff member OR type a new name, not both.")
        
        if self.instance.pk:  # If editing existing user
            if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
                self.add_error('username', "This username is already taken.")
            
            if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
                self.add_error('email', "This email is already registered.")
        else:  # If creating new user
            if User.objects.filter(username=username).exists():
                self.add_error('username', "This username is already taken.")
            
            if User.objects.filter(email=email).exists():
                self.add_error('email', "This email is already registered.")
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Handle password
        password = self.cleaned_data.get("password")
        if password:  # Only update password if provided
            user.set_password(password)
        elif not self.instance.pk:  # New user must have password
            raise ValidationError("Password is required for new users")
        
        user.is_active = True
        
        # Handle staff member or full name
        staff_member = self.cleaned_data.get("staff_member")
        full_name = self.cleaned_data.get("full_name")
        
        if staff_member:
            # Split staff name into first and last name
            name_parts = staff_member.name.split(' ', 1)
            user.first_name = name_parts[0]
            user.last_name = name_parts[1] if len(name_parts) > 1 else ''
        elif full_name:
            # Split full name into first and last name
            name_parts = full_name.split(' ', 1)
            user.first_name = name_parts[0]
            user.last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        if commit:
            user.save()
            
            # If staff_member was selected, link them
            if staff_member:
                # Remove any existing link to this staff member
                Staff.objects.filter(user=user).update(user=None)
                staff_member.user = user
                staff_member.save()
        
        return user


# NEW FORM: For status-only changes
class DocumentStatusForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'})
        }