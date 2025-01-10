from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from accounts.admin import CustomModelAdminMixin
from payment_app.resources import *


# Register your models here.


@admin.register(UserWallet)
class ProfileAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = WalletResource
    search_fields = ['user__email']
    raw_id_fields = ('created_by', 'updated_by', 'user')
    list_filter = ('status', )


@admin.register(Transaction)
class TransactionAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = TransactionResource
    raw_id_fields = ('created_by', 'updated_by', 'sender', 'receiver', 'verified_by')