from django.db import models
from datetime import timedelta

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
    receiver = models.CharField(max_length=100)
    division = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def is_overdue(self):
        from datetime import date
        return self.status != 'Resolved' and self.follow_up < date.today()

    def get_priority(self):
        """Compute priority based on days between doc_date and follow_up or status"""
        # First check if status is Resolved
        if self.status == 'Resolved':
            return "Treated"
            
        # Otherwise calculate based on days difference
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