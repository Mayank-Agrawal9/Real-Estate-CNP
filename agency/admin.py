from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from accounts.admin import CustomModelAdminMixin
from agency.resources import *


# Register your models here.

@admin.register(SuperAgency)
class SuperAgencyAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = SuperAgencyResource
    search_fields = ['name', 'email']
    raw_id_fields = ('created_by', 'updated_by', 'profile', 'city')
    list_filter = ('status', )


@admin.register(Agency)
class AgencyAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = AgencyResource
    search_fields = ['name', ]
    raw_id_fields = ('created_by', 'updated_by', 'company', 'city')
    list_filter = ('status', )


@admin.register(FieldAgent)
class FieldAgentAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = FieldAgentResource
    search_fields = ['profile__user__username', ]
    raw_id_fields = ('created_by', 'updated_by', 'profile', 'agency', 'city')
    list_filter = ('status', )


@admin.register(Investment)
class InvestmentAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = InvestmentResource
    search_fields = ['user__username', ]
    raw_id_fields = ('created_by', 'updated_by', 'user', 'approved_by', 'referral_by')
    list_filter = ('status', 'date_created')


@admin.register(InvestmentInterest)
class InvestmentInterestAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = InvestmentInterestResource
    raw_id_fields = ('created_by', 'updated_by', 'investment')
    list_filter = ('status', 'date_created')


@admin.register(Commission)
class CommissionAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = CommissionResource
    search_fields = ['commission_by__username', 'commission_to__username']
    raw_id_fields = ('created_by', 'updated_by', 'commission_by', 'commission_to')
    list_filter = ('status', )


@admin.register(RefundPolicy)
class RefundPolicyAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = RefundPolicyResource
    search_fields = ['user__email', ]
    raw_id_fields = ('created_by', 'updated_by', 'user')
    list_filter = ('status', )


@admin.register(PPDAccount)
class PPDAccountAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = PPDModelResource
    raw_id_fields = ('created_by', 'updated_by', 'user')
    list_display = ('user', 'deposit_amount', 'deposit_date', 'monthly_rental', 'is_active', 'has_purchased_property')
    list_filter = ('is_active', 'has_purchased_property', 'deposit_date')
    search_fields = ('user__username',)


@admin.register(FundWithdrawal)
class FundWithdrawalAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = FundWithdrawalResource
    search_fields = ['user__username', 'user__email']
    raw_id_fields = ('created_by', 'updated_by', 'user', 'transaction', 'action_taken_by')
    list_filter = ('status', )


@admin.register(RewardEarned)
class RewardEarnedAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = RewardEarnedResource
    raw_id_fields = ('created_by', 'updated_by', 'reward', 'user')
    list_filter = ('status', )


@admin.register(AgencyPackagePurchase)
class AgencyPackagePurchaseAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = AgencyPackagePurchaseResource
    raw_id_fields = ('created_by', 'updated_by', 'user', 'package', 'super_agency', 'agency', 'field_agent')
    list_filter = ('status', )