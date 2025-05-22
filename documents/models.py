from django.db import models
from django.contrib.auth import get_user_model
from datetime import timedelta

User = get_user_model()

class Document(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Followed Up', 'Followed Up'),
        ('Resolved', 'Resolved'),
    ]

    title = models.CharField(max_length=200)
    purpose = models.TextField(blank=True)
    doc_date = models.DateField()
    follow_up = models.DateField()
    receiver = models.ForeignKey('Staff', on_delete=models.CASCADE)
    division = models.ForeignKey('Division', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')

    def is_overdue(self):
        from datetime import date
        return self.status != 'Resolved' and self.follow_up < date.today()

    def get_priority(self):
        """Compute priority based on days between doc_date and follow_up or status"""
        if self.status == 'Resolved':
            return "Treated"
        if self.doc_date and self.follow_up:
            days_diff = (self.follow_up - self.doc_date).days
            if days_diff <= 2:
                return "High"
            elif days_diff <= 5:
                return "Moderate"
            else:
                return "Low"
        return "Unknown"

    def __str__(self):
        return self.title


class Division(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Staff(models.Model):
    name = models.CharField(max_length=100)
    division = models.ForeignKey(Division, on_delete=models.CASCADE, related_name='staff_members')
    # NEW: Link to User account (optional)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_profile')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    division = models.ForeignKey(Division, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.division.name if self.division else 'No Division'}"