from django.contrib.auth.models import User
from django.db import models

from master.models import State, Country, City
from property.choices import PROPERTY_TYPE, MEDIA_TYPE_CHOICES, PROPERTY_PAYMENT
from real_estate.model_mixin import ModelMixin


# Create your models here.

class PropertyCategory(ModelMixin):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name


class PropertyType(ModelMixin):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Property(ModelMixin):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='property_user')
    category = models.ForeignKey(PropertyCategory, on_delete=models.SET_NULL, null=True, related_name='properties')
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    area_size = models.FloatField()
    area_size_postfix = models.CharField(max_length=50, null=True, blank=True)
    property_type = models.ForeignKey(PropertyType, on_delete=models.CASCADE, null=True, blank=True)
    property_status = models.CharField(max_length=100)
    owner_contact_number = models.CharField(max_length=15)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='property_country')
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='property_state')
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='property_city')
    postal_code = models.CharField(max_length=20)
    street_address = models.TextField()
    is_sold = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)

    def __str__(self):
        return str(self.id)


class PropertyEnquiry(ModelMixin):
    request_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enquiry_user')
    property_id = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='enquiry_property')
    remarks = models.TextField(null=True, blank=True)
    is_response = models.BooleanField(default=False)

    def __str__(self):
        return str(self.id)


class PropertyBooking(ModelMixin):
    booked_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='book_by_user')
    customer_name = models.CharField(max_length=200, null=True, blank=True)
    customer_email = models.EmailField(null=True, blank=True)
    customer_phone = models.CharField(max_length=12, null=True, blank=True)
    property_id = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='booking_property')
    payment_status = models.CharField(max_length=30, choices=PROPERTY_PAYMENT)

    def __str__(self):
        return str(self.id)


class Media(ModelMixin):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='media')
    file = models.FileField(upload_to='property_media/')
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES)

    def __str__(self):
        return str(self.id)


class PropertyBookmark(ModelMixin):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarked_properties')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='bookmarks')

    def __str__(self):
        return f'Bookmark by {self.user} for {self.property}'


class Feature(ModelMixin):
    name = models.CharField(max_length=250, unique=True)

    def __str__(self):
        return self.name


class PropertyFeature(ModelMixin):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='features')
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE)
    value = models.CharField(max_length=255)

    def __str__(self):
        return f'{self.property.title} - {self.feature.name}: {self.value}'


class NearbyFacility(ModelMixin):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='nearby_facilities')
    name = models.CharField(max_length=150)
    distance = models.CharField(max_length=150)

    def __str__(self):
        return f'{self.name} ({self.distance} km)'


class PropertyReview(ModelMixin):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='property_reviews')
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Review by {self.user} for {self.property}'