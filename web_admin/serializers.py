from rest_framework import serializers

from accounts.models import Profile, BankDetails, UserPersonalDocument
from agency.models import Investment, SuperAgency, Agency, FieldAgent
from p2pmb.models import Package
from property.models import Property
from property.serializers import GetMediaDataSerializer, GetNearbyFacilitySerializer, GetPropertyFeatureSerializer
from web_admin.models import ManualFund, ContactUsEnquiry, PropertyInterestEnquiry


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
            'name': obj.company.name,
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
        fields = ('attachment', 'type', 'date_created', 'id')


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


class ContactUsEnquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactUsEnquiry
        fields = '__all__'


class PropertyInterestEnquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyInterestEnquiry
        fields = '__all__'


class GetPropertySerializer(serializers.ModelSerializer):
    media = GetMediaDataSerializer(many=True, read_only=True)
    country = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    property_type = serializers.SerializerMethodField()

    def get_country(self, obj):
        if obj.country:
            return {'id': obj.country.id, 'name': obj.country.name}

    def get_state(self, obj):
        if obj.state:
            return {'id': obj.state.id, 'name': obj.state.name}

    def get_city(self, obj):
        if obj.city:
            return {'id': obj.city.id, 'name': obj.city.name}

    def get_category(self, obj):
        if obj.category:
            return {'id': obj.category.id, 'name': obj.category.name}

    def get_property_type(self, obj):
        if obj.property_type:
            return {'id': obj.property_type.id, 'name': obj.property_type.name}

    class Meta:
        model = Property
        fields = ('id', 'category', 'title', 'price', 'area_size', 'area_size_postfix', 'property_type', 'country',
                  'state', 'city', 'postal_code', 'street_address', 'media', 'is_sold', 'is_featured')


class PropertyDetailSerializer(serializers.ModelSerializer):
    media = GetMediaDataSerializer(many=True, read_only=True)
    country = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    featured = serializers.SerializerMethodField()
    nearby_facility = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    property_type = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()

    def get_country(self, obj):
        if obj.country:
            return {'id': obj.country.id, 'name': obj.country.name}

    def get_state(self, obj):
        if obj.state:
            return {'id': obj.state.id, 'name': obj.state.name}

    def get_city(self, obj):
        if obj.city:
            return {'id': obj.city.id, 'name': obj.city.name}

    def get_user(self, obj):
        if obj.user:
            return {'id': obj.user.id, 'name': obj.user.get_full_name(), 'username': obj.user.username}

    def get_category(self, obj):
        if obj.category:
            return {'id': obj.category.id, 'name': obj.category.name}

    def get_featured(self, obj):
        """ Return property features or an empty list if none exist. """
        features = obj.features.all()
        return GetPropertyFeatureSerializer(features, many=True).data if features else []

    def get_nearby_facility(self, obj):
        """ Return nearby facilities or an empty list if none exist. """
        facilities = obj.nearby_facilities.all()
        return GetNearbyFacilitySerializer(facilities, many=True).data if facilities else []

    def get_property_type(self, obj):
        if obj.property_type:
            return {'id': obj.property_type.id, 'name': obj.property_type.name}

    class Meta:
        model = Property
        fields = '__all__'