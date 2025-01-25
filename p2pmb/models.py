from django.contrib.auth.models import User
from django.db import models

from real_estate.model_mixin import ModelMixin


# Create your models here.


class MLMTree(ModelMixin):
    parent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='children', null=True, blank=True)
    child = models.ForeignKey(User, on_delete=models.CASCADE, related_name='parent_relation')
    position = models.IntegerField()
    level = models.IntegerField()
    referral_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='parent_referral', null=True, blank=True)
    turnover = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    commission_earned = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['parent', 'position'], name='unique_child_position'),
            models.CheckConstraint(check=models.Q(position__gte=0) & models.Q(position__lte=5), name='valid_position')
        ]


class Package(ModelMixin):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)

    def __str__(self):
        return str(self.id)


# class RewardLevel(models.Model):
#     name = models.CharField(max_length=100)
#     turnover_required = models.DecimalField(max_digits=12, decimal_places=2)
#     monthly_payout = models.DecimalField(max_digits=10, decimal_places=2)
#     months_duration = models.IntegerField()
#     total_value = models.DecimalField(max_digits=12, decimal_places=2)
#
#     def __str__(self):
#         return self.name
#
#
# class RoyaltyClub(models.Model):
#     name = models.CharField(max_length=100)
#     turnover_limit = models.DecimalField(max_digits=12, decimal_places=2)
#     royalty_percentage = models.DecimalField(max_digits=5, decimal_places=2)
#
#     def __str__(self):
#         return self.name
#
#
# class Commission(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='commissions')
#     direct_income = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
#     level_income = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
#     lifetime_reward_income = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
#     royalty_income = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
#     date_earned = models.DateTimeField(auto_now_add=True)
#
#     def total_income(self):
#         return self.direct_income + self.level_income + self.lifetime_reward_income + self.royalty_income