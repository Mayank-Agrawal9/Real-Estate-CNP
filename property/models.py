from django.contrib.auth.models import User
from django.db import models

from master.models import State, Country, City
from property.choices import PROPERTY_TYPE, MEDIA_TYPE_CHOICES
from real_estate.model_mixin import ModelMixin


# Create your models here.
class Property(ModelMixin):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='property_user')
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    area_size = models.FloatField()
    area_size_postfix = models.CharField(max_length=50, null=True, blank=True)
    property_type = models.CharField(max_length=100, choices=PROPERTY_TYPE)
    property_status = models.CharField(max_length=100)
    owner_contact_number = models.CharField(max_length=15)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='property_country')
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='property_state')
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='property_city')
    postal_code = models.CharField(max_length=20)
    street_address = models.TextField()
    is_sold = models.BooleanField(default=False)

    def __str__(self):
        return str(self.id)


class Media(ModelMixin):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='media')
    file = models.FileField(upload_to='property_media/')
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES)

    def __str__(self):
        return str(self.id)