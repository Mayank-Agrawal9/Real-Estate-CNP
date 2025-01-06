from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from accounts.admin import CustomModelAdminMixin
from property.models import Property, Media
from property.resources import PropertyResource, MediaResource


# Register your models here.

@admin.register(Property)
class PropertyAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = PropertyResource
    search_fields = ['user__username', 'user__email']
    raw_id_fields = ('created_by', 'updated_by', 'user')
    list_filter = ('status', )


@admin.register(Media)
class MediaAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = MediaResource
    raw_id_fields = ('created_by', 'updated_by', 'property')
    list_filter = ('status', )