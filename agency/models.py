from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models

from accounts.choices import COMPANY_TYPE
from accounts.models import Profile
from agency.choices import REWARD_CHOICES, REFUND_CHOICES, INVESTMENT_TYPE_CHOICES
from real_estate.model_mixin import ModelMixin


# Create your models here.

class SuperAgency(ModelMixin):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, null=True, related_name="user_company")
    name = models.CharField(max_length=250)
    type = models.CharField(max_length=250, choices=COMPANY_TYPE, default='enterprise')
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    pan_number = models.CharField(max_length=10, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    office_address = models.TextField(null=True, blank=True)
    office_area = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    income = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    turnover = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    max_agencies = models.PositiveIntegerField(default=100)
    max_field_agents = models.PositiveIntegerField(default=10000)

    def __str__(self):
        return f"Created by {self.profile.user.username}"


class Agency(ModelMixin):
    company = models.ForeignKey(SuperAgency, on_delete=models.CASCADE, related_name="agencies")
    name = models.CharField(max_length=250)
    turnover = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    def __str__(self):
        return f"Agency Name {self.name}"


class FieldAgent(ModelMixin):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name="field_agent")
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="field_agents")
    turnover = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.id}"


class Investment(ModelMixin):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    investment_type = models.CharField(max_length=20, choices=INVESTMENT_TYPE_CHOICES)
    gst = models.DecimalField(max_digits=10, decimal_places=2)

    def total_investment(self):
        return self.amount + self.gst

    def __str__(self):
        return f"Investment by {self.user.username} of {self.amount} ({self.investment_type})"


class Commission(ModelMixin):
    commission_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='commission_by')
    commission_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='commission_to')
    commission_amount = models.DecimalField(max_digits=15, decimal_places=2)
    commission_type = models.CharField(max_length=255)
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"Commission for {self.user.username} - {self.commission_amount}"


class RefundPolicy(ModelMixin):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='refund_user')
    refund_type = models.CharField(max_length=20, choices=REFUND_CHOICES)
    amount_refunded = models.DecimalField(max_digits=15, decimal_places=2)
    deduction_percentage = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f"Refund for {self.user.username} - {self.refund_type}"


class PPDModel(ModelMixin):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ppd_user')
    deposit_amount = models.DecimalField(max_digits=15, decimal_places=2)
    monthly_rental = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"PPD Model for {self.user.username} - Deposit: {self.deposit_amount}"


class FundWithdrawal(ModelMixin):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='withdrawal_user')
    withdrawal_amount = models.DecimalField(max_digits=15, decimal_places=2)
    withdrawal_date = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"Withdrawal by {self.user.username} - Amount: {self.withdrawal_amount}"


class Reward(ModelMixin):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reward_user')
    reward_type = models.CharField(max_length=50, choices=REWARD_CHOICES)
    reward_value = models.DecimalField(max_digits=15, decimal_places=2)
    turnover_threshold = models.DecimalField(max_digits=15, decimal_places=2)
    achieved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reward for {self.user.username} - {self.reward_type}"


class RewardEarned(ModelMixin):
    company = models.ForeignKey(SuperAgency, on_delete=models.CASCADE, related_name="rewards_earned")
    reward = models.ForeignKey(Reward, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)
    turnover_at_earning = models.DecimalField(max_digits=15, decimal_places=2)