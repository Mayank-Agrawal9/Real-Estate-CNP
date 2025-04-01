from rest_framework import serializers

from accounts.models import Profile, BankDetails, UserPersonalDocument
from agency.models import Investment, SuperAgency, Agency, FieldAgent
from p2pmb.models import Package
from web_admin.models import ManualFund


class ProfileSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()

    def get_user(self, obj):
        return {
            'id': obj.user.id,
            'first_name': obj.user.first_name,
            'last_name': obj.user.last_name,
            'email': obj.user.email,
            'username': obj.user.username,
        }

    def get_city(self, obj):
        return obj.city.name if obj.city else None

    def get_state(self, obj):
        return obj.state.name if obj.state else None

    class Meta:
        model = Profile
        fields = '__all__'


class BankDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = BankDetails
        fields = ('id', 'date_created', 'account_number', 'account_holder_name', 'ifsc_code', 'bank_name', 'bank_address',
                  'date_created')


class SuperAgencyCompanyDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = SuperAgency
        fields = ('id', 'date_created', 'name', 'type', 'phone_number', 'pan_number', 'gst_number', 'email',
                  'office_address', 'office_area', 'city')


class AgencyCompanyDetailSerializer(serializers.ModelSerializer):
    company = serializers.SerializerMethodField()

    def get_company(self, obj):
        if not obj.company:
            return None
        return {
            'id': obj.company.id,
            'name': obj.company.id,
            'type': obj.company.type,
            'phone_number': obj.company.phone_number,
            'pan_number': obj.company.pan_number,
            'gst_number': obj.company.gst_number,
            'email': obj.company.email,
            'office_address': obj.company.office_address,
            'office_area': obj.company.office_area,
        }

    class Meta:
        model = Agency
        fields = ('id', 'date_created', 'name', 'type', 'phone_number', 'pan_number', 'gst_number', 'email',
                  'office_address', 'office_area', 'company')


class FieldAgentCompanyDetailSerializer(serializers.ModelSerializer):
    agency = serializers.SerializerMethodField()

    def get_agency(self, obj):
        if not obj.agency:
            return None
        return {
            'id': obj.agency.id,
            'name': obj.agency.name,
            'type': obj.agency.type,
            'phone_number': obj.agency.phone_number,
            'pan_number': obj.agency.pan_number,
            'gst_number': obj.agency.gst_number,
            'email': obj.agency.email,
            'office_address': obj.agency.office_address,
            'office_area': obj.agency.office_area
        }

    class Meta:
        model = FieldAgent
        fields = ('id', 'date_created', 'agency')


class UserDocumentSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserPersonalDocument
        fields = ('attachment', 'type', 'date_created')


class PackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Package
        fields = '__all__'


class InvestmentSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    package = PackageSerializer(many=True)

    def get_user(self, obj):
        return {
            'first_name': obj.user.first_name,
            'last_name': obj.user.last_name,
            'email': obj.user.email,
            'username': obj.user.username,
        }

    class Meta:
        model = Investment
        fields = '__all__'


class ManualFundSerializer(serializers.ModelSerializer):
    added_to = serializers.SerializerMethodField()

    def get_added_to(self, obj):
        return {
            'first_name': obj.added_to.first_name,
            'last_name': obj.added_to.last_name,
            'email': obj.added_to.email,
            'username': obj.added_to.username
        }

    class Meta:
        model = ManualFund
        fields = '__all__'


