from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from accounts.admin import CustomModelAdminMixin
from master.resources import *


# Register your models here.


@admin.register(Country)
class CountryAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = CountryResource
    raw_id_fields = ('created_by', 'updated_by')
    list_filter = ('status', )


@admin.register(State)
class StateAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = StateResource
    raw_id_fields = ('created_by', 'updated_by', 'country')
    list_filter = ('status', )


@admin.register(City)
class CityAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = CityResource
    raw_id_fields = ('created_by', 'updated_by', 'state')
    list_filter = ('status', )


@admin.register(BannerImage)
class BannerImageAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = BannerImageResource
    raw_id_fields = ('created_by', 'updated_by')
    list_filter = ('status', )


@admin.register(GST)
class GSTAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = GSTResource
    raw_id_fields = ('created_by', 'updated_by')
    list_filter = ('status', )


@admin.register(RewardMaster)
class RewardMasterAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = RewardMasterResource
    raw_id_fields = ('created_by', 'updated_by')
    list_filter = ('status', )


@admin.register(CompanyBankDetailsMaster)
class CompanyBankDetailsMasterAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = CompanyBankDetailsMasterResource
    raw_id_fields = ('created_by', 'updated_by')
    list_filter = ('status', )


@admin.register(RoyaltyMaster)
class RoyaltyMasterAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = RoyaltyMasterResource
    raw_id_fields = ('created_by', 'updated_by')
    list_filter = ('status', )


@admin.register(CoreGroupPhase)
class CoreGroupPhaseAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = CoreGroupPhaseResource
    raw_id_fields = ('created_by', 'updated_by')
    list_filter = ('status', )


@admin.register(CoreGroupIncome)
class CoreGroupIncomeAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = CoreGroupIncomeResource
    raw_id_fields = ('created_by', 'updated_by', 'phase')
    list_filter = ('status', )