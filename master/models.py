from decimal import Decimal

from django.db import models

from accounts.choices import USER_ROLE
from master.choices import GST_METHOD, BANNER_PAGE_CHOICE, CAROUSEL_NUMBER, ROYALTY_CLUB_TYPE, CORE_GROUP_TYPE
from real_estate.model_mixin import ModelMixin


# Create your models here.
class Country(ModelMixin):
    name = models.CharField(max_length=250)
    code = models.CharField(max_length=10)

    def __str__(self):
        return self.name


class State(ModelMixin):
    name = models.CharField(max_length=250)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='country')

    def __str__(self):
        return self.name


class City(ModelMixin):
    name = models.CharField(max_length=250)
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='district_state')

    def __str__(self):
        return self.name


class BannerImage(ModelMixin):
    image = models.ImageField(upload_to='banner', blank=True, null=True)
    document = models.FileField(upload_to='banner', blank=True, null=True)
    page_name = models.CharField(max_length=50, choices=BANNER_PAGE_CHOICE, null=True, blank=True)
    carousel_type = models.CharField(max_length=3, choices=CAROUSEL_NUMBER, null=True, blank=True)
    is_carousel = models.BooleanField(default=False)

    def __str__(self):
        return str(self.id)


class GST(ModelMixin):
    percentage = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=50, choices=GST_METHOD, null=True, blank=True)

    def __str__(self):
        return f"Gst Percentage {self.percentage}% for {self.method}"


class RewardMaster(ModelMixin):
    name = models.CharField(max_length=255)
    turnover_threshold = models.DecimalField(max_digits=15, decimal_places=2)
    reward_description = models.TextField()
    applicable_for = models.CharField(max_length=100, choices=USER_ROLE, default='super_agency')
    gift_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    total_paid_month = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} - ₹{self.turnover_threshold}"

    class Meta:
        ordering = ['applicable_for']


class CompanyBankDetailsMaster(ModelMixin):
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=100)
    bank_address = models.CharField(max_length=250, null=True, blank=True)
    ifsc_code = models.CharField(max_length=100)
    is_applicable_for_super_agency = models.BooleanField(default=False)
    is_applicable_for_agency = models.BooleanField(default=False)
    is_applicable_for_field_agent = models.BooleanField(default=False)
    is_applicable_for_customer = models.BooleanField(default=False)
    is_applicable_for_p2pmb = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.id}"


class RoyaltyMaster(ModelMixin):
    club_type = models.CharField(max_length=20, choices=ROYALTY_CLUB_TYPE)
    direct_ids_required = models.PositiveIntegerField()
    level_one_required = models.PositiveIntegerField()
    level_two_required = models.PositiveIntegerField()
    turnover_limit = models.PositiveBigIntegerField()
    gift_amount = models.PositiveBigIntegerField()

    def __str__(self):
        return f"{self.club_type} (Gift: {self.gift_amount})"


class CoreGroupPhase(ModelMixin):
    name = models.CharField(max_length=250, null=True, blank=True)
    validity = models.DateField()

    def __str__(self):
        return f"{self.id}"


class CoreGroupIncome(ModelMixin):
    phase = models.ForeignKey(CoreGroupPhase, on_delete=models.CASCADE, related_name='group_phase')
    company_turnover = models.DecimalField(max_digits=25, decimal_places=2, default=0.0)
    monthly_turnover = models.DecimalField(max_digits=25, decimal_places=2, default=0.0)
    tour_income = models.DecimalField(max_digits=25, decimal_places=2, default=0.0)
    core_income = models.DecimalField(max_digits=25, decimal_places=2, default=0.0)
    month = models.IntegerField()
    year = models.IntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['month', 'year'], name='unique_month_year')
        ]

    def save(self, *args, **kwargs):
        if self.company_turnover:
            self.calculated_amount_turnover = self.company_turnover * Decimal("0.01")
            self.monthly_turnover = self.calculated_amount_turnover
            distributed_amount = self.calculated_amount_turnover / Decimal("2")
            self.tour_income = distributed_amount
            self.core_income = distributed_amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.id}"
