from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models

from master.choices import ROYALTY_CLUB_TYPE
from master.models import CoreGroupIncome, State
from p2pmb.choices import EXTRA_REWARD_CHOICES, INCOME_EARNED_CHOICES
from real_estate.model_mixin import ModelMixin


# Create your models here.


class MLMTree(ModelMixin):
    parent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='children', null=True, blank=True)
    child = models.ForeignKey(User, on_delete=models.CASCADE, related_name='parent_relation')
    position = models.IntegerField()
    level = models.IntegerField()
    show_level = models.IntegerField(null=True, blank=True)
    referral_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='parent_referral', null=True, blank=True)
    turnover = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    commission_earned = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    send_direct_income = models.BooleanField(default=False)
    send_level_income = models.BooleanField(default=False)
    is_working_id = models.BooleanField(default=False)
    is_show = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['parent', 'position'], name='unique_child_position'),
            models.CheckConstraint(check=models.Q(position__gte=0) & models.Q(position__lte=5), name='valid_position')
        ]


class ScheduledCommission(ModelMixin):
    send_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="commissions_sender", null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="scheduled_commissions")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    scheduled_date = models.DateTimeField()
    remarks = models.TextField(null=True, blank=True)
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"Commission for {self.user} on {self.scheduled_date}"


class Package(ModelMixin):
    APPLICABLE_FOR_CHOICES = [
        ('super_agency', 'Star Agency'),
        ('agency', 'Agency'),
        ('field_agent', 'field_agent'),
        ('p2pmb', 'p2pmb')
    ]
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    applicable_for = models.CharField(max_length=15, choices=APPLICABLE_FOR_CHOICES, default='p2pmb')

    def __str__(self):
        return str(self.id)


class RoyaltyClub(ModelMixin):
    CLUB_CHOICES = [
        ('star', 'Star Club'),
        ('2_star', '2-Star Club'),
        ('3_star', '3-Star Club'),
        ('5_star', '5-Star Club'),
    ]
    person = models.ForeignKey(MLMTree, on_delete=models.CASCADE, related_name='royalty_clubs')
    club_type = models.CharField(max_length=10, choices=CLUB_CHOICES)
    turnover_limit = models.DecimalField(max_digits=15, decimal_places=2)
    joined_date = models.DateField(auto_now_add=True)
    direct_ids_required = models.IntegerField(default=0)
    level_one_required = models.IntegerField(default=0)
    level_two_required = models.IntegerField(default=0)
    gifts_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return f"{self.id} - {self.get_club_type_display()}"


class Reward(ModelMixin):
    REWARD_CHOICES = [
        ('star', 'Star Reward'),
        ('silver', 'Silver Reward'),
        ('gold', 'Gold Reward'),
        ('diamond', 'Diamond Reward'),
        ('titan', 'Titan Reward'),
        ('conqueron', 'Conqueron Reward'),
        ('almighty', 'Almighty Reward'),
        ('relic', 'Relic Reward'),
        ('commander', 'Commander Reward'),
        ('immortal', 'Immortal Reward'),
        ('blue_sapphire', 'The Blue Sapphire Reward'),
    ]
    person = models.ForeignKey(MLMTree, on_delete=models.CASCADE, related_name='rewards')
    reward_type = models.CharField(max_length=20, choices=REWARD_CHOICES)
    turnover_required = models.DecimalField(max_digits=15, decimal_places=2)
    monthly_payment = models.DecimalField(max_digits=15, decimal_places=2)
    months_duration = models.IntegerField()
    achieved_date = models.DateField(auto_now_add=True)
    last_payment_send = models.DateField(null=True, blank=True)

    def __str__(self):
         return f"{self.id} - {self.get_reward_type_display()}"


class Commission(ModelMixin):
    COMMISSION_TYPE_CHOICES = [
        ('direct', 'Direct Income'),
        ('level', 'Level Income'),
        ('reward', 'Life Time Reward Income'),
        ('royalty', 'Royalty Company Turnover'),
    ]
    LEVEL_CHOICES = [
        ('up', 'Up'),
        ('down', 'Down')
    ]
    commission_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="commissions_by", null=True,
                                      blank=True)
    commission_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='p2pmb_commission_to', null=True,
                                      blank=True)
    commission_type = models.CharField(max_length=20, choices=COMMISSION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    description = models.CharField(max_length=255, blank=True, null=True)
    level_type = models.CharField(max_length=8, choices=LEVEL_CHOICES, null=True, blank=True)

    def __str__(self):
        return f"{self.commission_by.username} - {self.get_commission_type_display()} - {self.amount}"


class P2PMBRoyaltyMaster(ModelMixin):
    total_turnover = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    calculated_amount_turnover = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    star_income = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    two_star_income = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    three_star_income = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    lifetime_income = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    eligible_user = models.ManyToManyField(User, blank=True, related_name='royalty_user')
    month = models.DateField()
    is_distributed = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.total_turnover:
            self.calculated_amount_turnover = self.total_turnover * Decimal("0.01")
            distributed_amount = self.calculated_amount_turnover / Decimal("4")
            self.star_income = distributed_amount
            self.two_star_income = distributed_amount
            self.three_star_income = distributed_amount
            self.lifetime_income = distributed_amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Total company turnover {self.total_turnover} - Calculated Amount {self.calculated_amount_turnover}"


class RoyaltyEarned(ModelMixin):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='royalty_earned_user')
    club_type = models.CharField(max_length=30, choices=ROYALTY_CLUB_TYPE)
    earned_date = models.DateField()
    royalty = models.ForeignKey(P2PMBRoyaltyMaster, on_delete=models.CASCADE, null=True, blank=True,
                                related_name='royalty_earned')
    earned_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"User {self.user.username} - Earned Date {self.earned_date}"


class ExtraReward(ModelMixin):
    start_date = models.DateField()
    end_date = models.DateField()
    reward_type = models.CharField(max_length=20, default='leader', choices=EXTRA_REWARD_CHOICES)
    turnover_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    description = models.TextField()

    def __str__(self):
        return str(self.id)


class CoreIncomeEarned(ModelMixin):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='core_income_earned_user')
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='core_income_earned_state')
    income_type = models.CharField(max_length=20, default='income', choices=INCOME_EARNED_CHOICES)
    core_income = models.ForeignKey(CoreGroupIncome, on_delete=models.CASCADE, related_name='core_income_master')
    income_earned = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return str(self.id)