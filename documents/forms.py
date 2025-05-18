from django import forms
from django.contrib.auth.models import User
from .models import Division, Document

from django import forms
from .models import Document, Division, Staff

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


from django.core.exceptions import ValidationError

class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    division = forms.ModelChoiceField(
        queryset=Division.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select select2'})
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

        if User.objects.filter(username=username).exists():
            self.add_error('username', "This username is already taken.")

        if User.objects.filter(email=email).exists():
            self.add_error('email', "This email is already registered.")

        if password and confirm and password != confirm:
            self.add_error("confirm_password", "Passwords do not match")


class AdminUserCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    division = forms.ModelChoiceField(queryset=Division.objects.all())

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'division']

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        email = cleaned_data.get("email")

        if User.objects.filter(username=username).exists():
            self.add_error('username', "This username is already taken.")

        if User.objects.filter(email=email).exists():
            self.add_error('email', "This email is already registered.")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.is_active = True 
        if commit:
            user.save()
        return user
