from import_export import resources

from notification.models import InAppNotification


class InAppNotificationResource(resources.ModelResource):
    class Meta:
        model = InAppNotification
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')