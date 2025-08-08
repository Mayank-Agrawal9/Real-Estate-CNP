from django.contrib.auth.models import User
from django.db import models

from notification.choices import NOTIFICATION_TYPES
from real_estate.model_mixin import ModelMixin


# Create your models here.


class InAppNotification(ModelMixin):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_notifications')
    message = models.TextField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    read_at_timestamp = models.DateTimeField(null=True, blank=True)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    action_url = models.URLField(null=True, blank=True)

    def __str__(self):
        return f"{self.id} - {self.notification_type}"