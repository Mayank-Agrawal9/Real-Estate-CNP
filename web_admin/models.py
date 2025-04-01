from django.contrib.auth.models import User
from django.db import models
from multiselectfield import MultiSelectField

from real_estate.model_mixin import ModelMixin
from .choices import *


# Create your models here.

class ManualFund(ModelMixin):
    added_to = models.ForeignKey(User, on_delete=models.CASCADE, null=True, related_name="manual_user")
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    fund_type = models.CharField(max_length=50, choices=PAYMENT_METHOD, default='deposit')

    def __str__(self):
        return f"Amount added to {self.added_to.username} of {self.amount}"


class FunctionalityAccessPermissions(ModelMixin):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    main_dashboard = MultiSelectField(choices=main_dashboard, max_choices=50, max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Permission'
        verbose_name_plural = 'Functionality Access Permission'


class UserFunctionalityAccessPermission(ModelMixin):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    permission = models.ForeignKey(FunctionalityAccessPermissions, on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'User Permission'
        verbose_name_plural = 'Functionality access permission of User'