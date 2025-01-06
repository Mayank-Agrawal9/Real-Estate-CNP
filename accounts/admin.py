from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from accounts.models import *
from accounts.resources import ProfileResource, OTPResource, EXCLUDE_FOR_API, BankDetailsResource, \
    UserPersonalDocumentResource


# Register your models here.

class CustomModelAdminMixin(object):
    def __init__(self, model, admin_site):
        self.list_display = [field.name for field in model._meta.fields if field.name not in EXCLUDE_FOR_API]
        super(CustomModelAdminMixin, self).__init__(model, admin_site)


@admin.register(Profile)
class ProfileAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = ProfileResource
    search_fields = ['name', 'user__email']
    raw_id_fields = ('created_by', 'updated_by', 'user')
    list_filter = ('status', )


@admin.register(OTP)
class OTPAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = OTPResource


@admin.register(BankDetails)
class BankDetailsAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = BankDetailsResource
    search_fields = ['user__username', 'user__email', 'account_number']
    raw_id_fields = ('created_by', 'updated_by', 'user')
    list_filter = ('status', )


@admin.register(UserPersonalDocument)
class UserPersonalDocumentAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = UserPersonalDocumentResource
    search_fields = ['created_by__username', ]
    raw_id_fields = ('created_by', 'updated_by')
    list_filter = ('status', )