from django import forms
from .models import Document

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = '__all__'
        widgets = {
            'doc_date': forms.DateInput(attrs={'type': 'date'}),
            'follow_up': forms.DateInput(attrs={'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
        exclude = ['status']