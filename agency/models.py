import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models

from accounts.choices import COMPANY_TYPE
from accounts.models import Profile
from agency.choices import REFUND_CHOICES, INVESTMENT_TYPE_CHOICES, REFUND_STATUS_CHOICES, INVESTMENT_GUARANTEED_TYPE, \
    PAYMENT_CHOICES, FUND_WITHDRAW_TYPE
from master.models import RewardMaster, City
from p2pmb.models import Package
from payment_app.models import Transaction
from real_estate.model_mixin import ModelMixin


# Create your models here.

class SuperAgency(ModelMixin):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, null=True, related_name="user_company")
    name = models.CharField(max_length=250)
    type = models.CharField(max_length=250, choices=COMPANY_TYPE, default='enterprise')
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    pan_number = models.CharField(max_length=10, null=True, blank=True)
    gst_number = models.CharField(max_length=15, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    office_address = models.TextField(null=True, blank=True)
    office_area = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    income = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    turnover = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    max_agencies = models.PositiveIntegerField(default=100)
    max_field_agents = models.PositiveIntegerField(default=10000)
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="super_agency_city", null=True, blank=True)

    def __str__(self):
        return f"Created by {self.profile.user.username}"


class Agency(ModelMixin):
    # user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name="user_company")
    company = models.ForeignKey(SuperAgency, on_delete=models.CASCADE, related_name="agencies")
    name = models.CharField(max_length=250)
    type = models.CharField(max_length=250, choices=COMPANY_TYPE, default='enterprise')
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    pan_number = models.CharField(max_length=10, null=True, blank=True)
    gst_number = models.CharField(max_length=15, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    office_address = models.TextField(null=True, blank=True)
    turnover = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    office_area = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="agency_city", null=True, blank=True)

    def __str__(self):
        return f"Agency Name {self.name}"


class FieldAgent(ModelMixin):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name="field_agent")
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="field_agents")
    turnover = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="field_agent_city", null=True, blank=True)

    def __str__(self):
        return f"{self.id}"


class Investment(ModelMixin):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    investment_type = models.CharField(max_length=20, choices=INVESTMENT_TYPE_CHOICES)
    pay_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='new')
    investment_guaranteed_type = models.CharField(max_length=30, choices=INVESTMENT_GUARANTEED_TYPE,
                                                  null=True, blank=True)
    transaction_id = models.ForeignKey(Transaction, on_delete=models.CASCADE, null=True, blank=True)
    package = models.ManyToManyField(Package, blank=True)
    gst = models.DecimalField(max_digits=10, decimal_places=2)
    guaranteed_agreement = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True,
                                    related_name='investment_approval')
    approved_on = models.DateTimeField(null=True, blank=True)
    referral_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="referral_code")
    send_direct_income = models.BooleanField(default=False)
    send_level_income = models.BooleanField(default=False)
    is_interest_send = models.BooleanField(default=False)
    is_royalty_calculate = models.BooleanField(default=False)

    def total_investment(self):
        return self.amount + self.gst

    def __str__(self):
        return f"Investment by {self.user.username} of {self.amount} ({self.investment_type})"


class InvestmentInterest(ModelMixin):
    investment = models.ForeignKey(Investment, on_delete=models.CASCADE, related_name="investment_interest")
    interest_amount = models.DecimalField(max_digits=15, decimal_places=2)
    interest_send_date = models.DateField()
    is_sent = models.BooleanField(default=False)
    end_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Interest for {self.investment.user.username} on {self.interest_send_date}: {self.interest_amount}"


class Commission(ModelMixin):
    COMMISSION_TYPE_CHOICES = [
        ('direct', 'Direct Income'),
        ('level', 'Level Income'),
        ('reward', 'Reward Income'),
        ('royalty', 'Royalty Company Turnover'),
        ('rent', 'Rent'),
        ('revenue_by_agency', 'Revenue By Agency'),
        ('revenue_by_field_agent', 'Revenue By Field Agent'),
        ('turnover_commission', 'Turnover Commission'),
        ('sale_commission', 'Sale Commission'),
        ('ppd_interest', 'PPD Interest'),
    ]
    APPLICABLE_FOR_CHOICES = [
        ('super_agency', 'Super Agency'),
        ('agency', 'Agency'),
        ('field_agent', 'field_agent')
    ]
    commission_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='commission_by')
    commission_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='commission_to')
    commission_amount = models.DecimalField(max_digits=15, decimal_places=2)
    commission_type = models.CharField(max_length=30, choices=COMMISSION_TYPE_CHOICES)
    description = models.TextField(blank=True, null=True)
    applicable_for = models.CharField(max_length=15, choices=APPLICABLE_FOR_CHOICES, default='super_agency')
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"Commission for {self.commission_to.username} - {self.commission_amount}"

    class Meta:
        verbose_name = "Agency Commission"
        verbose_name_plural = "Agency Commission"


class RefundPolicy(ModelMixin):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='refund_user')
    refund_type = models.CharField(max_length=20, choices=REFUND_CHOICES, default='no_refund')
    refund_status = models.CharField(max_length=20, choices=REFUND_STATUS_CHOICES, default='pending')
    refund_initiate_on = models.DateTimeField(default=datetime.datetime.today)
    refund_process_date = models.DateField(null=True, blank=True)
    refund_process_by = models.ForeignKey(User, on_delete=models.CASCADE,
                                          related_name='refund_process_user', null=True, blank=True)
    amount_refunded = models.DecimalField(max_digits=15, decimal_places=2)
    deduction_percentage = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f"Refund for {self.user.username} - {self.refund_type}"


class PPDAccount(ModelMixin):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ppd_accounts")
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2)
    deposit_date = models.DateField(auto_now_add=True)
    monthly_rental = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    has_purchased_property = models.BooleanField(default=False)
    withdrawal_date = models.DateField(null=True, blank=True)
    withdrawal_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)
    last_interest_pay = models.DateField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.monthly_rental:
            self.monthly_rental = Decimal(self.deposit_amount) * Decimal('0.02')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"PPD Model for {self.user.username} - Deposit: {self.deposit_amount}"

    def deposit_duration(self):
        if self.withdrawal_date:
            return (self.withdrawal_date - self.deposit_date).days / 365
        return (datetime.datetime.now().date() - self.deposit_date).days / 365

    def calculate_deduction(self):
        years = self.deposit_duration()
        if self.has_purchased_property or years >= 6:
            return Decimal(0)
        elif years < 1:
            return Decimal('0.40')  # 40% deduction
        elif years < 3:
            return Decimal('0.35')  # 35% deduction
        elif years < 6:
            return Decimal('0.25')  # 25% deduction
        return Decimal(0)  # Fallback

    def calculate_withdrawal_amount(self):
        deduction = self.calculate_deduction()
        return self.deposit_amount * (Decimal(1) - deduction)


class FundWithdrawal(ModelMixin):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='withdrawal_user')
    withdrawal_amount = models.DecimalField(max_digits=15, decimal_places=2)
    taxable_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    withdrawal_date = models.DateTimeField(auto_now_add=True)
    withdrawal_status = models.CharField(max_length=30, choices=FUND_WITHDRAW_TYPE, default='pending')
    action_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"Withdrawal by {self.user.username} - Amount: {self.withdrawal_amount}"


class RewardEarned(ModelMixin):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rewards_earned', null=True, default=None)
    reward = models.ForeignKey(RewardMaster, on_delete=models.CASCADE, null=True, default=None)
    earned_at = models.DateTimeField(auto_now_add=True)
    turnover_at_earning = models.DecimalField(max_digits=15, decimal_places=2)
    is_paid = models.BooleanField(default=False)
    is_p2p = models.BooleanField(default=False)
    total_month = models.IntegerField(default=0)
    last_payment_send = models.DateTimeField(null=True, blank=True)
    total_installment_paid = models.IntegerField(default=0)

    def __str__(self):
        return f"Reward for {self.user.username} Earned at {self.earned_at}"


class InterestEarnings(models.Model):
    investment = models.ForeignKey(Investment, on_delete=models.CASCADE)
    earned_amount = models.DecimalField(max_digits=15, decimal_places=2)
    earned_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Interest of {self.earned_amount} earned on {self.earned_date} for Investment ID: {self.investment.id}"

    @classmethod
    def calculate_interest(cls, investment):
        if (investment.is_approved and investment.investment_type == 'p2pmb' and
                investment.investment_guaranteed_type == 'guaranteed_investment'):
            interest_rate = 0.01  # 1% interest rate
            current_date = datetime.datetime.now()

            # Check if it's time to calculate new interest
            if investment.last_interest_received_date is None:
                investment.last_interest_received_date = current_date

            # Calculate the time since the last interest was received
            time_since_last_interest = current_date - investment.last_interest_received_date

            # If more than a year has passed since the last interest calculation
            if time_since_last_interest >= datetime.timedelta(days=365):
                years_passed = time_since_last_interest.days // 365
                interest_to_add = investment.amount * interest_rate * years_passed

                # Create a new entry in InterestEarnings
                cls.objects.create(investment=investment, earned_amount=interest_to_add)

                # Update the last interest received date
                investment.last_interest_received_date = current_date

                # Save changes to the Investment model
                investment.save()

                return interest_to_add

        return 0