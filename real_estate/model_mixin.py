from django.contrib.auth import get_user_model
from django.db import models

from accounts.choices import STATUS_CHOICES
from real_estate.manager import ModelMixinManager

User = get_user_model()


class ModelMixin(models.Model):
    """
    This mixins provide the default field in the models project wise
    """
    date_created = models.DateTimeField(auto_now_add=True, auto_now=False, verbose_name='Date of creation')
    date_updated = models.DateTimeField(auto_now=True, verbose_name='Date of update')
    created_by = models.ForeignKey(User, related_name="%(app_label)s_%(class)s_created",
                                   on_delete=models.CASCADE, blank=True, null=True, verbose_name='Created by')
    updated_by = models.ForeignKey(User, related_name="%(app_label)s_%(class)s_updated",
                                   on_delete=models.CASCADE, blank=True, null=True, verbose_name='Updated by')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    objects = ModelMixinManager()

    class Meta:
        abstract = True
