from django.db import models
from django.contrib.auth.models import User
import uuid

from payment_app.choices import TRANSACTION_TYPE_CHOICES, TRANSACTION_STATUS_CHOICES, PAYMENT_METHOD
from real_estate.model_mixin import ModelMixin


class UserWallet(ModelMixin):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    main_wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    app_wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Wallet for {self.user.username}"

    # Method to deposit amount into the wallet
    def deposit(self, amount):
        self.balance += amount
        self.save()

    # Method to withdraw amount from the wallet
    def withdraw(self, amount):
        if self.balance >= amount:
            self.balance -= amount
            self.save()
            return True
        return False

    # Method to transfer amount (for commissions, investments)
    def transfer(self, amount, receiver_wallet):
        if self.balance >= amount:
            self.balance -= amount
            receiver_wallet.deposit(amount)
            self.save()
            return True
        return False


class Transaction(ModelMixin):
    transaction_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='sent_transactions')
    receiver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='received_transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    taxable_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    transaction_status = models.CharField(max_length=10, choices=TRANSACTION_STATUS_CHOICES, default='pending')
    payment_slip = models.ImageField(upload_to='payment_slips/', null=True, blank=True)
    payment_method = models.CharField(max_length=50, null=True, blank=True, choices=PAYMENT_METHOD)
    deposit_transaction_id = models.CharField(max_length=200, null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='verified_transactions')
    verified_on = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.transaction_type} for {self.amount}"