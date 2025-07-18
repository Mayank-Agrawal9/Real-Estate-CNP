import datetime
import uuid

from django.contrib.auth.models import User
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field

from accounts.choices import GENDER_CHOICE, USER_ROLE, DOCUMENT_TYPE, COMPANY_TYPE, OTP_TYPE, ADMIN_ROLE, \
    CHANGE_REQUEST_CHOICE
from master.models import State, City
from real_estate.model_mixin import ModelMixin


# Create your models here.

class OTP(models.Model):
    email = models.EmailField(unique=True)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateTimeField()
    last_resend = models.DateTimeField(null=True, blank=True)
    type = models.CharField(max_length=20, choices=OTP_TYPE, default='register', null=True, blank=True)
    is_verify = models.BooleanField(default=False)

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
    qr_code = models.ImageField(upload_to='profile', blank=True, null=True)
    mobile_number = models.CharField(max_length=15, null=True, blank=True)
    mobile_number1 = models.CharField(max_length=15, null=True, blank=True)
    mobile_number2 = models.CharField(max_length=15, null=True, blank=True)
    other_email = models.EmailField(null=True, blank=True)
    pan_number = models.CharField(max_length=10, null=True, blank=True)
    voter_number = models.CharField(max_length=10, null=True, blank=True)
    pan_remarks = models.TextField(max_length=250, null=True, blank=True)
    aadhar_number = models.CharField(max_length=12, null=True, blank=True)
    role = models.CharField(max_length=25, choices=USER_ROLE, null=True, blank=True, default='customer')
    admin_role = models.CharField(max_length=25, choices=ADMIN_ROLE, null=True, blank=True)
    is_kyc = models.BooleanField(default=False)
    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True, blank=True)
    state = models.ForeignKey(State, on_delete=models.CASCADE, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    is_kyc_verified = models.BooleanField(default=False)
    is_super_agency = models.BooleanField(default=False)
    is_agency = models.BooleanField(default=False)
    is_field_agent = models.BooleanField(default=False)
    is_p2pmb = models.BooleanField(default=False)
    is_vendor = models.BooleanField(default=False)
    verified_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="kyc_verified_by")
    verified_on = models.DateTimeField(null=True, blank=True)
    referral_code = models.CharField(max_length=50, null=True, blank=True)
    image_code = models.CharField(max_length=10, null=True, blank=True, unique=True)
    pin_code = models.CharField(max_length=7, null=True, blank=True)
    referral_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="referral_by")
    parent_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="parent_user")
    kyc_video = models.FileField(null=True, blank=True)
    payment_password = models.CharField(max_length=128, blank=True, null=True)
    remarks = models.TextField(null=True, blank=True)
    is_kyc_reprocess = models.BooleanField(default=False)
    is_roi_send = models.BooleanField(default=True)


class BankDetails(ModelMixin):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, related_name="user_bank")
    account_number = models.CharField(max_length=20)
    account_holder_name = models.CharField(max_length=200)
    ifsc_code = models.CharField(max_length=12)
    bank_name = models.CharField(max_length=200)
    bank_address = models.TextField(null=True, blank=True)
    beneficiary_id = models.TextField(null=True, blank=True)
    upi_id = models.CharField(max_length=200, null=True, blank=True)


class UserPersonalDocument(ModelMixin):
    attachment = models.ImageField(upload_to='document', blank=True, null=True)
    type = models.CharField(max_length=25, choices=DOCUMENT_TYPE, null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)
    approval_status = models.CharField(
        max_length=10,
        choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='pending'
    )
    rejection_reason = models.TextField(null=True, blank=True)


class SoftwarePolicy(models.Model):
    privacy_policy = CKEditor5Field()
    terms_and_conditions = CKEditor5Field()
    software_version = models.CharField(max_length=20, null=True, blank=True)
    is_enabled = models.BooleanField(default=False)

    def __str__(self):
        return f"Software Policy: {self.id}"

    class Meta:
        verbose_name = "Software Policy"
        verbose_name_plural = "Software Policies"


class FAQ(models.Model):
    question = models.TextField()
    answer = models.TextField()
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.question

    class Meta:
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
        ordering = ['created_at']


class ChangeRequest(ModelMixin):
    reference_number = models.CharField(max_length=30, unique=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    new_phone_number = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    account_number = models.CharField(max_length=20, null=True, blank=True)
    ifsc_code = models.CharField(max_length=20, default='')
    account_holder_name = models.CharField(max_length=100, default='')
    bank_name = models.CharField(max_length=100, default='')
    new_account_number = models.CharField(max_length=20, null=True, blank=True)
    new_ifsc_code = models.CharField(max_length=20, default='')
    new_account_holder_name = models.CharField(max_length=100, default='')
    new_bank_name = models.CharField(max_length=100, default='')
    new_bank_address = models.CharField(max_length=250, default='')
    full_name = models.CharField(max_length=200, null=True, blank=True)
    verified_by = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name="request_accept")
    request_status = models.CharField(max_length=20, choices=CHANGE_REQUEST_CHOICE, default='pending')
    verified_on = models.DateTimeField(null=True, blank=True)
    admin_remark = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.reference_number:
            now = datetime.datetime.now()
            timestamp = now.strftime('%Y%m%d%H%M%S%f')
            suffix = uuid.uuid4().hex[:6].upper()
            self.reference_number = f"REQ-{timestamp}{suffix}"
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Change Request"
        verbose_name_plural = "Change Requests"