from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from accounts.admin import CustomModelAdminMixin
from p2pmb.models import MLMTree, Package, ScheduledCommission, RoyaltyClub, Reward, Commission, P2PMBRoyaltyMaster, \
    ExtraReward, CoreIncomeEarned, RoyaltyEarned
from p2pmb.resources import MLMTreeResource, PackageResource, RoyaltyClubResource, ScheduledCommissionResource, \
    RewardResource, CommissionResource, P2PMBRoyaltyMasterResource, ExtraRewardResource, CoreIncomeEarnedResource, \
    RoyaltyEarnedResource


# Register your models here.
@admin.register(MLMTree)
class MLMTreeAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = MLMTreeResource
    raw_id_fields = ('created_by', 'updated_by', 'parent', 'child', 'referral_by')
    list_filter = ('status', )


@admin.register(Package)
class PackageAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = PackageResource
    raw_id_fields = ('created_by', 'updated_by')
    list_filter = ('status', )


@admin.register(ScheduledCommission)
class ScheduledCommissionAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = ScheduledCommissionResource
    raw_id_fields = ('created_by', 'updated_by', 'send_by', 'user')
    list_filter = ('status', )


@admin.register(RoyaltyClub)
class RoyaltyClubResourceAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = RoyaltyClubResource
    raw_id_fields = ('created_by', 'updated_by', 'person')
    list_filter = ('status', )


@admin.register(Reward)
class RewardAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = RewardResource
    raw_id_fields = ('created_by', 'updated_by', 'person')
    list_filter = ('status', )


@admin.register(Commission)
class CommissionAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = CommissionResource
    raw_id_fields = ('created_by', 'updated_by', 'commission_by', 'commission_to')
    list_filter = ('status', )


@admin.register(P2PMBRoyaltyMaster)
class P2PMBRoyaltyMasterAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = P2PMBRoyaltyMasterResource
    raw_id_fields = ('created_by', 'updated_by')
    list_filter = ('status', )


@admin.register(RoyaltyEarned)
class RoyaltyEarnedAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = RoyaltyEarnedResource
    raw_id_fields = ('created_by', 'updated_by', 'user', 'royalty')
    list_filter = ('status', )


@admin.register(ExtraReward)
class ExtraRewardAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = ExtraRewardResource
    raw_id_fields = ('created_by', 'updated_by')
    list_filter = ('status', )


@admin.register(CoreIncomeEarned)
class CoreIncomeEarnedAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = CoreIncomeEarnedResource
    raw_id_fields = ('created_by', 'updated_by', 'user', 'state', 'core_income')
    list_filter = ('status', 'date_created')