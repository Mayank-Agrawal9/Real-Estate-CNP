from django.db import models


class ModelMixinManager(models.Manager):
    '''
    this is the manager for ModelMixin. so it will apply on those models where ModelMixin will be inherited
    '''
    def publish(self):
        return super().get_queryset().filter(status='publish')

    def active(self):
        return super().get_queryset().filter(status='active')

    def inactive(self):
        return super().get_queryset().filter(status='inactive')

    def draft(self):
        return super().get_queryset().filter(status='draft')