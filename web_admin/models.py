from django.contrib.auth.models import User
from django.db import models
from multiselectfield import MultiSelectField

from property.models import Property
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
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_permission')
    permission = models.ForeignKey(FunctionalityAccessPermissions, on_delete=models.SET_NULL,
                                   blank=True, null=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'User Permission'
        verbose_name_plural = 'Functionality access permission of User'


class CompanyInvestment(ModelMixin):
    applicable_for = models.CharField(max_length=20, choices=USER_TYPE, default='p2pmb')
    investment_type = models.CharField(max_length=20, choices=INVESTMENT_TYPE, null=True, blank=True)
    amount = models.DecimalField(default=0, decimal_places=2, max_digits=25)
    initiated_date = models.DateField()

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'Company Investment'
        verbose_name_plural = 'Company Investment Distribution'


class ContactUsEnquiry(ModelMixin):
    created_by = None
    updated_by = None
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField(max_length=150)
    phone = models.CharField(max_length=15)
    subject = models.CharField(max_length=30, choices=CONTACT_US_ENQUIRY, default='general_enquiry')
    message = models.TextField(null=True, blank=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'Contact Us Enquiry'
        verbose_name_plural = 'Contact Us Enquiries'


class PropertyInterestEnquiry(ModelMixin):
    created_by = None
    updated_by = None
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    email = models.EmailField(max_length=150)
    phone = models.CharField(max_length=15)
    message = models.TextField(null=True, blank=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'Property Enquiry'
        verbose_name_plural = 'Property Interested Enquiries'