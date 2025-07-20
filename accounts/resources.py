from import_export import resources

from accounts.models import *

EXCLUDE_FOR_API = ('updated_by', 'date_updated', 'created_by')


class ProfileResource(resources.ModelResource):
    class Meta:
        model = Profile
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by', 'picture', 'payment_password')


class OTPResource(resources.ModelResource):
    class Meta:
        model = OTP
        import_id_fields = ('id',)
        exclude = EXCLUDE_FOR_API


class BankDetailsResource(resources.ModelResource):
    class Meta:
        model = BankDetails
        import_id_fields = ('id',)
        exclude = EXCLUDE_FOR_API


class UserPersonalDocumentResource(resources.ModelResource):
    class Meta:
        model = UserPersonalDocument
        import_id_fields = ('id',)
        exclude = EXCLUDE_FOR_API


class SoftwarePolicyResource(resources.ModelResource):
    class Meta:
        model = SoftwarePolicy
        import_id_fields = ('id',)
        exclude = EXCLUDE_FOR_API


class FAQResource(resources.ModelResource):
    class Meta:
        model = FAQ
        import_id_fields = ('id',)
        exclude = EXCLUDE_FOR_API


class ChangeRequestResource(resources.ModelResource):
    class Meta:
        model = ChangeRequest
        import_id_fields = ('id',)
        exclude = EXCLUDE_FOR_API


class DeviceInfoResource(resources.ModelResource):
    class Meta:
        model = DeviceInfo
        import_id_fields = ('id',)
        exclude = EXCLUDE_FOR_API


class AppVersionResource(resources.ModelResource):
    class Meta:
        model = AppVersion
        import_id_fields = ('id',)
        exclude = EXCLUDE_FOR_API