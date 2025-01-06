import datetime

from django.contrib.auth.models import User
from django.db import models

from accounts.choices import GENDER_CHOICE, USER_ROLE, DOCUMENT_TYPE, COMPANY_TYPE
from master.models import State, City
from real_estate.model_mixin import ModelMixin


# Create your models here.

class OTP(models.Model):
    email = models.EmailField(unique=True)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateTimeField()
    last_resend = models.DateTimeField(null=True, blank=True)

    def is_valid(self):
        return datetime.datetime.now() < self.valid_until

    def can_resend(self):
        if self.last_resend:
            return (datetime.datetime.now() - self.last_resend).seconds >= 60
        return True


class Profile(ModelMixin):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, related_name="profile")
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=25, choices=GENDER_CHOICE, null=True, blank=True)
    father_name = models.CharField(max_length=200, null=True, blank=True)
    picture = models.ImageField(upload_to='profile', blank=True, null=True)
    mobile_number = models.CharField(max_length=15, null=True, blank=True)
    pan_number = models.CharField(max_length=10, null=True, blank=True)
    aadhar_number = models.CharField(max_length=12, null=True, blank=True)
    role = models.CharField(max_length=25, choices=USER_ROLE, null=True, blank=True, default='customer')
    is_kyc = models.BooleanField(default=False)
    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True, blank=True)
    state = models.ForeignKey(State, on_delete=models.CASCADE, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    is_kyc_verified = models.BooleanField(default=False)
    verified_by = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name="kyc_verified_by")
    verified_on = models.DateTimeField(null=True, blank=True)
    referral_code = models.CharField(max_length=50, null=True, blank=True)
    referral_by = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name="referral_by")


class BankDetails(ModelMixin):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, related_name="user_bank")
    account_number = models.CharField(max_length=20)
    account_holder_name = models.CharField(max_length=200)
    ifsc_code = models.CharField(max_length=12)
    bank_name = models.CharField(max_length=200)
    bank_address = models.TextField(null=True, blank=True)


class UserPersonalDocument(ModelMixin):
    attachment = models.ImageField(upload_to='document', blank=True, null=True)
    type = models.CharField(max_length=25, choices=DOCUMENT_TYPE, null=True, blank=True)

