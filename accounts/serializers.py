from rest_framework import serializers

from accounts.models import Profile


class RequestOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)


class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", required=False)

    class Meta:
        model = Profile
        fields = '__all__'

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        if "username" in user_data:
            instance.user.username = user_data["username"]
            instance.user.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance


class BasicDetailsSerializer(serializers.Serializer):
    father_name = serializers.CharField(required=True)
    mobile_number = serializers.CharField(required=True)
    pan_number = serializers.CharField(required=True)
    aadhar_number = serializers.CharField(required=True)
    referral_code = serializers.CharField(required=False)
    role = serializers.ChoiceField(choices=["super_agency", "agency", "field_agent"], required=True)


class CompanyDetailsSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    type = serializers.CharField(required=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    pan_number = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=True)
    office_address = serializers.CharField(required=False, allow_blank=True)
    office_area = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)


class BankDetailsSerializer(serializers.Serializer):
    account_number = serializers.CharField(required=True)
    account_holder_name = serializers.CharField(required=True)
    ifsc_code = serializers.CharField(required=True)
    bank_name = serializers.CharField(required=True)
    bank_address = serializers.CharField(required=False, allow_blank=True)


class DocumentSerializer(serializers.Serializer):
    attachment = serializers.URLField(required=True)
    type = serializers.CharField(required=True)


class SuperAgencyKycSerializer(serializers.Serializer):
    basic_details = BasicDetailsSerializer(required=True)
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

        if role == "field_agent":
            attrs.pop("company_details", None)
        elif not attrs.get("company_details"):
            raise serializers.ValidationError(
                {"company_details": "This field is required for roles other than 'field_agent'."}
            )

        return attrs