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


class ScheduledCommission(ModelMixin):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="scheduled_commissions")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    scheduled_date = models.DateTimeField()
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"Commission for {self.user} on {self.scheduled_date}"


class Package(ModelMixin):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)

    def __str__(self):
        return str(self.id)


class RoyaltyClub(models.Model):
    CLUB_CHOICES = [
        ('star', 'Star Club'),
        ('2_star', '2-Star Club'),
        ('3_star', '3-Star Club'),
        ('5_star', '5-Star Club'),
    ]
    person = models.ForeignKey(MLMTree, on_delete=models.CASCADE, related_name='royalty_clubs')
    club_type = models.CharField(max_length=10, choices=CLUB_CHOICES)
    turnover_limit = models.DecimalField(max_digits=15, decimal_places=2)
    # You might want to track when they joined the club, benefits received, etc.
    joined_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.person.user.username} - {self.get_club_type_display()}"


class Reward(models.Model):
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

    def __str__(self):
         return f"{self.person.user.username} - {self.get_reward_type_display()}"


class Commission(models.Model):
    COMMISSION_TYPE_CHOICES = [
        ('direct', 'Direct Income'),
        ('level', 'Level Income'),
        ('reward', 'Life Time Reward Income'),
        ('royalty', 'Royalty Company Turnover'),
    ]
    person = models.ForeignKey(MLMTree, on_delete=models.CASCADE, related_name='commissions')
    commission_type = models.CharField(max_length=20, choices=COMMISSION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    date_earned = models.DateField(auto_now_add=True)
    description = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.person.user.username} - {self.get_commission_type_display()} - {self.amount}"