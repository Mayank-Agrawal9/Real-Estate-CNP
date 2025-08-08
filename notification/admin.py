from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from accounts.admin import CustomModelAdminMixin
from notification.models import InAppNotification
from notification.resources import InAppNotificationResource


# Register your models here.


@admin.register(InAppNotification)
class InAppNotificationAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = InAppNotificationResource
    raw_id_fields = ('created_by', 'updated_by', 'user')
    list_filter = ('status', 'is_read')