from import_export import resources
from accounts.resources import EXCLUDE_FOR_API
from web_admin.models import ManualFund, FunctionalityAccessPermissions, UserFunctionalityAccessPermission, \
    CompanyInvestment, ContactUsEnquiry, PropertyInterestEnquiry, ROIUpdateLog


class ManualFundResource(resources.ModelResource):
    class Meta:
        model = ManualFund
        import_id_fields = ('id',)
        exclude = EXCLUDE_FOR_API


class FunctionalityAccessPermissionsResource(resources.ModelResource):
    class Meta:
        model = FunctionalityAccessPermissions
        import_id_fields = ('id',)
        exclude = EXCLUDE_FOR_API


class UserFunctionalityAccessPermissionResource(resources.ModelResource):
    class Meta:
        model = UserFunctionalityAccessPermission
        import_id_fields = ('id',)
        exclude = EXCLUDE_FOR_API


class CompanyInvestmentResource(resources.ModelResource):
    class Meta:
        model = CompanyInvestment
        import_id_fields = ('id',)
        exclude = EXCLUDE_FOR_API


class ContactUsEnquiryResource(resources.ModelResource):
    class Meta:
        model = ContactUsEnquiry
        import_id_fields = ('id',)
        exclude = EXCLUDE_FOR_API


class PropertyInterestEnquiryResource(resources.ModelResource):
    class Meta:
        model = PropertyInterestEnquiry
        import_id_fields = ('id',)
        exclude = EXCLUDE_FOR_API


class ROIUpdateLogResource(resources.ModelResource):
    class Meta:
        model = ROIUpdateLog
        import_id_fields = ('id',)
        exclude = EXCLUDE_FOR_API