from django.db import models

from master.choices import GST_METHOD, BANNER_PAGE_CHOICE
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

    def __str__(self):
        return self.id


class GST(ModelMixin):
    percentage = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=50, choices=GST_METHOD, null=True, blank=True)

    def __str__(self):
        return f"Gst Percentage {self.percentage}% for {self.method}"