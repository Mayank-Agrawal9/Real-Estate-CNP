from django.contrib.auth.models import User
from django.db import models

from real_estate.model_mixin import ModelMixin


# Create your models here.


class MLMTree(ModelMixin):
    parent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='children', null=True, blank=True)
    child = models.ForeignKey(User, on_delete=models.CASCADE, related_name='parent_relation')
    position = models.IntegerField()
    level = models.IntegerField()
    referral_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='parent_referral', null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['parent', 'position'], name='unique_child_position'),
            models.CheckConstraint(check=models.Q(position__gte=0) & models.Q(position__lte=5), name='valid_position')
        ]
