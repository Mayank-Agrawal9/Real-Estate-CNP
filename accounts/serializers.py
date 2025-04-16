import base64
import uuid

from django.core.files.base import ContentFile
from rest_framework import serializers

from accounts.models import Profile, FAQ, ChangeRequest, UserPersonalDocument, BankDetails
from master.models import City


class RequestOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)


class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", required=False)
    full_name = serializers.CharField(required=False)

    class Meta:
        model = Profile
        fields = '__all__'

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        full_name = validated_data.pop("full_name", "").strip()
        if full_name:
            name_parts = full_name.split(" ", 1)
            instance.user.first_name = name_parts[0] if name_parts else ""
            instance.user.last_name = name_parts[1] if len(name_parts) > 1 else ""
            instance.user.save()
        if "username" in user_data:
            instance.user.username = user_data["username"]
            instance.user.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["full_name"] = f"{instance.user.first_name} {instance.user.last_name}".strip()
        return data


class BasicDetailsSerializer(serializers.Serializer):
    full_name = serializers.SerializerMethodField()
    father_name = serializers.CharField(required=True)
    mobile_number1 = serializers.CharField(required=False)
    mobile_number2 = serializers.CharField(required=False)
    email = serializers.SerializerMethodField()
    other_email = serializers.CharField(required=False)
    pan_remarks = serializers.CharField(required=False)
    voter_number = serializers.CharField(required=False)
    mobile_number = serializers.CharField(required=False)
    kyc_video = serializers.FileField(required=False)
    pan_number = serializers.CharField(required=False)
    aadhar_number = serializers.CharField(required=False)
    referral_code = serializers.CharField(required=False)
    city = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    country = serializers.SerializerMethodField()
    pin_code = serializers.CharField(required=False)
    role = serializers.ChoiceField(choices=["super_agency", "agency", "field_agent"], required=True)

    def get_full_name(self, obj):
        """Dynamically generate full_name from first_name and last_name."""
        return f"{obj.user.first_name} {obj.user.last_name}".strip()

    def get_email(self, obj):
        return obj.user.email if obj.user else None

    def get_city(self, obj):
        if obj.city:
            return {'id':  obj.city.id, 'name': obj.city.name}
        return None

    def get_state(self, obj):
        if obj.city and obj.city.state:
            return {'id':  obj.city.state.id, 'name': obj.city.state.name}
        return None

    def get_country(self, obj):
        if obj.city and obj.city.state and obj.city.state.country:
            return {'id':  obj.city.state.country.id, 'name': obj.city.state.country.name}
        return None


class CreateBasicDetailsSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=True)
    father_name = serializers.CharField(required=True)
    mobile_number1 = serializers.CharField(required=False)
    mobile_number2 = serializers.CharField(required=False)
    other_email = serializers.EmailField(allow_null=True, allow_blank=True, required=False)
    pan_remarks = serializers.CharField(required=False)
    voter_number = serializers.CharField(required=False)
    mobile_number = serializers.CharField(required=True)
    kyc_video = serializers.FileField(required=False)
    pan_number = serializers.CharField(required=False)
    aadhar_number = serializers.CharField(required=False)
    referral_code = serializers.CharField(required=False)
    pin_code = serializers.CharField(required=False)
    role = serializers.ChoiceField(choices=["super_agency", "agency", "field_agent", "p2pmb"], required=True)


class UpdateUserProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    father_name = serializers.CharField(required=True)
    mobile_number1 = serializers.CharField(required=False)
    mobile_number2 = serializers.CharField(required=False)
    other_email = serializers.EmailField(allow_null=True, allow_blank=True, required=False)
    pan_remarks = serializers.CharField(required=False)
    voter_number = serializers.CharField(required=False)
    mobile_number = serializers.CharField(required=True)
    kyc_video = serializers.FileField(required=True)
    pan_number = serializers.CharField(required=False)
    aadhar_number = serializers.CharField(required=False)
    referral_code = serializers.CharField(required=False)
    pin_code = serializers.CharField(required=False)
    role = serializers.ChoiceField(choices=["super_agency", "agency", "field_agent", "p2pmb", "customer"], required=True)

    def get_full_name(self, obj):
        user = obj.user
        return f"{user.first_name} {user.last_name}".strip()

    class Meta:
        model = Profile
        fields = ('father_name', 'mobile_number1', 'other_email', 'mobile_number2', 'pan_remarks',
                  'voter_number', 'mobile_number', 'kyc_video', 'pan_number', 'aadhar_number', 'referral_code',
                  'pin_code', 'role', 'full_name')


class CompanyDetailsSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    type = serializers.CharField(required=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    pan_number = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=True)
    office_address = serializers.CharField(required=False, allow_blank=True)
    # city = serializers.PrimaryKeyRelatedField(
    #     queryset=City.objects.filter(status='active'), many=False, required=True
    # )
    office_area = serializers.DecimalField(required=False, max_digits=10, decimal_places=2, default=0.0)


class BankDetailsSerializer(serializers.Serializer):
    account_number = serializers.CharField(required=True)
    account_holder_name = serializers.CharField(required=True)
    ifsc_code = serializers.CharField(required=True)
    bank_name = serializers.CharField(required=True)
    bank_address = serializers.CharField(required=False, allow_blank=True)


class DocumentSerializer(serializers.Serializer):
    attachment = serializers.CharField(required=True)
    type = serializers.CharField(required=True)

    def validate_attachment(self, value):
        """
        Decode Base64 string into an image file.
        """
        try:
            format, img_str = value.split(';base64,')
            ext = format.split('/')[-1]
            file_name = f"{uuid.uuid4()}.{ext}"
            return ContentFile(base64.b64decode(img_str), name=file_name)
        except Exception as e:
            return None
            # raise serializers.ValidationError("Invalid Base64 encoded image.") from e


class SuperAgencyKycSerializer(serializers.Serializer):
    basic_details = CreateBasicDetailsSerializer(required=True)
    company_details = CompanyDetailsSerializer(required=False)
    bank_details = BankDetailsSerializer(required=True)
    documents_for_kyc = DocumentSerializer(many=True, required=False)

    def validate(self, attrs):
        """
        Custom validation to make company_details optional
        when the role in basic_details is 'field_agent'.
        """
        basic_details = attrs.get("basic_details", {})
        role = basic_details.get("role")

        if role == "field_agent" or role == "p2pmb":
            attrs.pop("company_details", None)
        elif not attrs.get("company_details"):
            raise serializers.ValidationError(
                {"company_details": "This field is required for roles other than 'field_agent' or 'p2pmb."}
            )
        return attrs


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ['id', 'question', 'answer', 'created_at', 'updated_at']


class ChangeRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChangeRequest
        fields = '__all__'


class BankDetailsSerializerV2(serializers.ModelSerializer):
    class Meta:
        model = BankDetails
        fields = '__all__'


class UserPersonalDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPersonalDocument
        fields = '__all__'