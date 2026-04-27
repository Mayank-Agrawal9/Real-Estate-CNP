from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from master.models import City
from real_estate.model_mixin import ModelMixin
from vendor.choices import OFFERING_CHOICES, IMAGE_TYPE_CHOICES, ENQUIRY_STATUS_CHOICES
from vendor.helpers import PHONE_REGEX


# Create your models here.


class Category(ModelMixin):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to='category_icons/', blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


class Vendor(ModelMixin):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    business_name = models.CharField(max_length=200)
    owner_name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='vendors')

    # Contact Details
    phone = models.CharField(validators=[PHONE_REGEX], max_length=17)
    alternate_phone = models.CharField(validators=[PHONE_REGEX], max_length=17, blank=True, null=True)
    email = models.EmailField()
    website = models.URLField(blank=True, null=True)

    # Address Details
    address = models.TextField()
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name='vendors')
    pincode = models.CharField(max_length=10, null=True, blank=True)
    landmark = models.CharField(max_length=200, blank=True)

    # Location Coordinates
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Business Details
    offering_type = models.CharField(max_length=10, choices=OFFERING_CHOICES)
    service_description = models.TextField(blank=True, null=True)
    product_description = models.TextField(blank=True, null=True)
    year_established = models.IntegerField(null=True, blank=True)
    number_of_employees = models.IntegerField(null=True, blank=True)

    # Business Hours
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    working_days = models.CharField(max_length=100, blank=True, help_text="e.g., Mon-Sat")

    # Social Media
    facebook_url = models.URLField(blank=True, null=True)
    instagram_url = models.URLField(blank=True, null=True)
    twitter_url = models.URLField(blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)

    # Verification & Status
    is_verified = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)

    # Metadata
    views_count = models.IntegerField(default=0)
    enquiry_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-date_created']
        indexes = [
            models.Index(fields=['category', 'city']),
            models.Index(fields=['is_verified', 'status']),
        ]

    def __str__(self):
        return self.business_name

    def average_rating(self):
        ratings = self.ratings.all()
        if ratings.exists():
            return ratings.aggregate(models.Avg('rating'))['rating__avg']
        return 0

    def total_ratings(self):
        return self.ratings.count()


class Product(ModelMixin):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=20, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sku = models.CharField(max_length=100, blank=True)
    is_available = models.BooleanField(default=True)
    stock_quantity = models.IntegerField(default=0)

    class Meta:
        ordering = ['-date_created']

    def __str__(self):
        return f"{self.name} - {self.vendor.business_name}"


class VendorImage(ModelMixin):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='images')
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, null=True, blank=True, related_name='product_image'
    )
    image = models.ImageField(upload_to='vendor_images/')
    image_type = models.CharField(max_length=20, choices=IMAGE_TYPE_CHOICES, default='gallery')
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_primary', '-date_created']

    def __str__(self):
        return f"{self.vendor.business_name} - {self.image_type}"


class Rating(ModelMixin):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='ratings')
    rating_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rating_user')
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5"
    )
    review = models.TextField()

    # Rating Categories
    quality_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True, blank=True
    )
    service_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True, blank=True
    )
    value_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True, blank=True
    )

    is_verified_purchase = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=True)

    class Meta:
        ordering = ['-date_created']
        unique_together = ['vendor']

    def __str__(self):
        return f"{self.id}"


class Enquiry(ModelMixin):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='enquiries')
    enquiry_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enquiries_user', null=True)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=17)
    message = models.TextField()

    # Additional Details
    preferred_contact_time = models.CharField(max_length=100, blank=True)
    budget = models.CharField(max_length=100, blank=True)

    enquiry_status = models.CharField(max_length=20, choices=ENQUIRY_STATUS_CHOICES, default='pending')
    vendor_response = models.TextField(blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-date_created']
        verbose_name_plural = 'Enquiries'

    def __str__(self):
        return f"{self.name} - {self.vendor.business_name}"


class VendorCertification(ModelMixin):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='certifications')
    name = models.CharField(max_length=200)
    issuing_organization = models.CharField(max_length=200)
    issue_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    certificate_image = models.ImageField(upload_to='certifications/', blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.vendor.business_name}"


class VendorAward(ModelMixin):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='awards')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    awarded_by = models.CharField(max_length=200)
    award_date = models.DateField()

    def __str__(self):
        return f"{self.title} - {self.vendor.business_name}"