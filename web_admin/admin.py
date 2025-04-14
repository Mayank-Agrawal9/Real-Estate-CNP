from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from accounts.admin import CustomModelAdminMixin
from web_admin.models import ManualFund, FunctionalityAccessPermissions, UserFunctionalityAccessPermission, \
    CompanyInvestment, ContactUsEnquiry, PropertyInterestEnquiry
from web_admin.resources import ManualFundResource, FunctionalityAccessPermissionsResource, \
    UserFunctionalityAccessPermissionResource, CompanyInvestmentResource, ContactUsEnquiryResource, \
    PropertyInterestEnquiryResource


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


@admin.register(CompanyInvestment)
class CompanyInvestmentAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = CompanyInvestmentResource
    raw_id_fields = ('created_by', 'updated_by')
    list_filter = ('applicable_for', 'investment_type')


@admin.register(ContactUsEnquiry)
class ContactUsEnquiryAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = ContactUsEnquiryResource
    search_fields = ('first_name', 'last_name', 'email')


@admin.register(PropertyInterestEnquiry)
class PropertyInterestEnquiryAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = PropertyInterestEnquiryResource
    raw_id_fields = ('property', )
    search_fields = ('name', 'phone')