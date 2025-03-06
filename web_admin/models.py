from django.contrib.auth.models import User
from django.db import models

from real_estate.model_mixin import ModelMixin
from web_admin.choices import PAYMENT_METHOD


# Create your models here.

class ManualFund(ModelMixin):
    added_to = models.ForeignKey(User, on_delete=models.CASCADE, null=True, related_name="manual_user")
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    fund_type = models.CharField(max_length=50, choices=PAYMENT_METHOD, default='deposit')

    def __str__(self):
        return f"Amount added to {self.added_to.username} of {self.amount}"