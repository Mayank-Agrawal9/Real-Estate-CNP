from decimal import Decimal

from rest_framework import serializers

from master.models import Country, State, City
from payment_app.models import UserWallet
from property.choices import MEDIA_TYPE_CHOICES, PROPERTY_TYPE, PROPERTY_STATUS
from property.models import Property, Media, PropertyEnquiry, PropertyBooking, PropertyBookmark, NearbyFacility, \
    PropertyFeature, Feature, PropertyCategory


class CreateNearbyFacilitySerializer(serializers.ModelSerializer):

    class Meta:
        model = NearbyFacility
        fields = '__all__'


class NearbyFacilitySerializer(serializers.ModelSerializer):

    class Meta:
        model = NearbyFacility
        exclude = ('property', )


class FeatureSerializer(serializers.ModelSerializer):

    class Meta:
        model = Feature
        fields = ('id', 'name')


class PropertyCategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = PropertyCategory
        fields = ('name', 'id')


class CreatePropertyFeatureSerializer(serializers.ModelSerializer):

    class Meta:
        model = PropertyFeature
        fields = '__all__'


class PropertyFeatureSerializer(serializers.ModelSerializer):

    class Meta:
        model = PropertyFeature
        exclude = ('property', )


class CreatePropertySerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    area_size = serializers.FloatField()
    area_size_postfix = serializers.CharField(max_length=50, allow_blank=True, required=False)
    # property_type = serializers.ChoiceField(PROPERTY_TYPE)
    property_status = serializers.CharField(max_length=100)
    owner_contact_number = serializers.CharField(max_length=15)
    country = serializers.PrimaryKeyRelatedField(queryset=Country.objects.all())
    state = serializers.PrimaryKeyRelatedField(queryset=State.objects.all())
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all())
    postal_code = serializers.CharField(max_length=20)
    street_address = serializers.CharField()
    media_files = serializers.ListField(
        child=serializers.FileField(),
        required=False
    )
    features = PropertyFeatureSerializer(many=True, required=False)
    nearby_facilities = NearbyFacilitySerializer(many=True, required=False)
    media_type = serializers.ChoiceField(choices=['photo', 'video'], required=False)

    def validate(self, data):
        """
        Custom validation logic.
        """
        media_files = data.get('media_files', [])
        media_type = data.get('media_type', '')

        if media_files and not media_type:
            raise serializers.ValidationError("You must specify a media type when uploading files.")

        return data


class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = '__all__'


class MediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Media
        fields = '__all__'


class GetMediaDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = Media
        fields = ('id', 'date_created', 'file', 'media_type')


class GetNearbyFacilitySerializer(serializers.ModelSerializer):

    class Meta:
        model = NearbyFacility
        fields = ('name', 'distance')


class GetPropertyFeatureSerializer(serializers.ModelSerializer):
    feature = serializers.SerializerMethodField()

    def get_feature(self, obj):
        return {
            'id': obj.feature.id,
            'name': obj.feature.name
        }

    class Meta:
        model = PropertyFeature
        fields = ('value', 'feature')


class PropertyListSerializer(serializers.ModelSerializer):
    media = GetMediaDataSerializer(many=True, read_only=True)
    country = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()

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

    class Meta:
        model = Property
        fields = ('id', 'date_created', 'status', 'title', 'description', 'price', 'area_size',
                  'area_size_postfix', 'property_type', 'property_status', 'owner_contact_number',
                  'postal_code', 'street_address', 'is_sold', 'created_by', 'user', 'country', 'state', 'city',
                  'media', 'category')


class PropertyBookmarkListSerializer(serializers.ModelSerializer):
    media = GetMediaDataSerializer(many=True, read_only=True)
    country = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()

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

    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        return PropertyBookmark.objects.filter(user=request.user, property=obj).exists()

    class Meta:
        model = Property
        fields = ('id', 'date_created', 'status', 'title', 'description', 'price', 'area_size',
                  'area_size_postfix', 'property_type', 'property_status', 'owner_contact_number',
                  'postal_code', 'street_address', 'is_sold', 'created_by', 'user', 'country', 'state', 'city',
                  'media', 'category', 'is_bookmarked')


class PropertyRetrieveSerializer(serializers.ModelSerializer):
    media = GetMediaDataSerializer(many=True, read_only=True)
    country = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    featured = serializers.SerializerMethodField()
    nearby_facility = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()

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

    def get_featured(self, obj):
        """ Return property features or an empty list if none exist. """
        features = obj.features.all()
        return GetPropertyFeatureSerializer(features, many=True).data if features else []

    def get_nearby_facility(self, obj):
        """ Return nearby facilities or an empty list if none exist. """
        facilities = obj.nearby_facilities.all()
        return GetNearbyFacilitySerializer(facilities, many=True).data if facilities else []

    class Meta:
        model = Property
        fields = ('id', 'date_created', 'status', 'title', 'description', 'price', 'area_size',
                  'area_size_postfix', 'property_type', 'property_status', 'owner_contact_number',
                  'postal_code', 'street_address', 'is_sold', 'created_by', 'user', 'country', 'state', 'city',
                  'media', 'featured', 'nearby_facility', 'category')


class EditPropertySerializer(serializers.Serializer):
    title = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    area_size = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    area_size_postfix = serializers.CharField(required=False)
    property_type = serializers.ChoiceField(choices=PROPERTY_TYPE, required=False)
    property_status = serializers.ChoiceField(choices=PROPERTY_STATUS, required=False)
    user_property_id = serializers.CharField(required=False)
    owner_contact_number = serializers.CharField(required=False)
    country = serializers.CharField(required=False)
    state = serializers.CharField(required=False)
    city = serializers.CharField(required=False)
    postal_code = serializers.CharField(required=False)
    street_address = serializers.CharField(required=False)
    video_url = serializers.URLField(required=False)
    country_code = serializers.CharField(required=False)
    media_files = serializers.ListField(child=serializers.FileField(), required=False)
    features = serializers.ListField(child=serializers.FileField(), required=False)
    nearby_facilities = serializers.ListField(child=serializers.FileField(), required=False)
    media_type = serializers.ChoiceField(choices=MEDIA_TYPE_CHOICES, required=False)


class CreatePropertyEnquirySerializer(serializers.ModelSerializer):
    request_by = serializers.CharField(required=False)
    property_id = serializers.PrimaryKeyRelatedField(queryset=Property.objects.filter(status='active'), required=True)

    class Meta:
        model = PropertyEnquiry
        fields = '__all__'

    def validate(self, data):
        request_user = self.context['request'].user
        data['created_by'] = request_user
        data['request_by'] = request_user
        return data


class GetPropertyEnquirySerializer(serializers.ModelSerializer):
    request_by = serializers.SerializerMethodField()
    property_id = PropertySerializer(read_only=True)

    def get_request_by(self, obj):
        if obj.request_by:
            return {'id': obj.request_by.id, 'name': obj.request_by.get_full_name()}

    class Meta:
        model = PropertyEnquiry
        fields = '__all__'


class GetPropertyBookingSerializer(serializers.ModelSerializer):
    booked_by = serializers.SerializerMethodField()
    property_id = PropertySerializer(read_only=True)

    def get_booked_by(self, obj):
        if obj.booked_by:
            return {'id': obj.booked_by.id, 'name': obj.booked_by.get_full_name()}

    class Meta:
        model = PropertyBooking
        fields = '__all__'


class CreatePropertyBookingSerializer(serializers.ModelSerializer):
    booked_by = serializers.CharField(required=False)
    customer_name = serializers.CharField(required=True)
    customer_email = serializers.EmailField(required=True)
    customer_phone = serializers.RegexField(regex=r'^\d{10}$', required=True,
                                            error_messages={'invalid': 'Enter a valid 10 digit phone number.'})

    class Meta:
        model = PropertyBooking
        fields = '__all__'

    def validate(self, data):
        request_user = self.context['request'].user
        data['booked_by'] = request_user
        payment_mode = self.context['request'].data.get('payment_status')
        property_price = data.get('property_id').price
        property_created_user = data.get('property_id').user

        if not (request_user.profile.is_kyc_verified and request_user.profile.is_kyc):
            raise serializers.ValidationError("You are not verified your KYC, Please verify first.")

        if payment_mode == 'in_app':
            try:
                wallet = UserWallet.objects.get(user=request_user)
                receiver_wallet = UserWallet.objects.get(user=property_created_user)
            except Exception as e:
                raise serializers.ValidationError("User Wallet does not exist for the booked_by user.")

            if wallet.app_wallet_balance < property_price:
                raise serializers.ValidationError("Insufficient balance in you app Wallet.")
            wallet.app_wallet_balance -= property_price
            wallet.save()
            taxable_amount = property_price * Decimal(0.05)
            receiver_wallet.app_wallet_balance += property_price - taxable_amount
            wallet.save()

        elif payment_mode == 'main_wallet':
            try:
                wallet = UserWallet.objects.get(user=request_user)
                receiver_wallet = UserWallet.objects.get(user=property_created_user)
            except Exception as e:
                raise serializers.ValidationError("User Wallet does not exist for the booked_by user.")

            if wallet.main_wallet_balance < property_price:
                raise serializers.ValidationError("Insufficient balance in you main wallet.")
            wallet.main_wallet_balance -= property_price
            wallet.save()
            taxable_amount = property_price * Decimal(0.10)
            receiver_wallet.app_wallet_balance += property_price - taxable_amount
            wallet.save()
        else:
            raise serializers.ValidationError("Currently we are accepting two types of payment only.")
        return data

    # def create(self, validated_data):
    #     booking = super().create(validated_data)
    #     self.distribute_commission(
    #         user=validated_data['booked_by'],
    #         property_price=validated_data['property_id'].price
    #     )
    #     return booking
    #
    # def distribute_commission(self, user, property_price):
    #     commission_field_agent = 0.0025
    #     commission_agency = 0.005
    #     commission_super_agency = 0.0025
    #
    #     if user.profile.role == 'field_agent':
    #         super_agent = user.profile.parent
    #         if super_agent:
    #             self.add_commission(super_agent, property_price * commission_field_agent)
    #
    #         agency = super_agent.profile.parent if super_agent else None
    #         if agency:
    #             self.add_commission(agency, property_price * commission_agency)
    #
    #     elif user.profile.role == 'agency':
    #         super_agency = user.profile.parent
    #         if super_agency and super_agency.profile.years_active > 10:
    #             self.add_commission(super_agency, property_price * commission_super_agency)
    #
    # def add_commission(self, user, commission_amount):
    #     """Adds commission to a user's wallet."""
    #     try:
    #         wallet = UserWallet.objects.get(user=user)
    #         wallet.commission_balance += commission_amount
    #         wallet.save()
    #     except UserWallet.DoesNotExist:
    #         pass


class PropertyBookmarkHelperSerializer(serializers.ModelSerializer):
    media = GetMediaDataSerializer(many=True, read_only=True)
    state = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()

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

    class Meta:
        model = Property
        fields = '__all__'


class GetPropertyBookmarkSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    property = PropertyBookmarkHelperSerializer(read_only=True)

    def get_user(self, obj):
        if obj.user:
            return {'id': obj.user.id, 'name': obj.user.get_full_name(), 'username': obj.user.username}

    class Meta:
        model = PropertyBookmark
        fields = '__all__'


class PropertyBookmarkSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = PropertyBookmark
        fields = '__all__'

