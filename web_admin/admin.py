from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from accounts.admin import CustomModelAdminMixin
from web_admin.models import ManualFund, FunctionalityAccessPermissions, UserFunctionalityAccessPermission
from web_admin.resources import ManualFundResource, FunctionalityAccessPermissionsResource, \
    UserFunctionalityAccessPermissionResource


# Register your models here.

@admin.register(ManualFund)
class ManualFundAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = ManualFundResource
    raw_id_fields = ('created_by', 'updated_by', 'added_to')


@admin.register(FunctionalityAccessPermissions)
class ManualFundAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = FunctionalityAccessPermissionsResource
    raw_id_fields = ('created_by', 'updated_by')


@admin.register(UserFunctionalityAccessPermission)
class ManualFundAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = UserFunctionalityAccessPermissionResource
    raw_id_fields = ('created_by', 'updated_by', 'user', 'permission')