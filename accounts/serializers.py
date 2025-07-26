import base64
import datetime
import random
import re
import uuid

from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.db.models import Q
from rest_framework import serializers, exceptions

from accounts.helpers import normalize_gmail
from accounts.models import Profile, FAQ, ChangeRequest, UserPersonalDocument, BankDetails, OTP, AppVersion
from master.models import City
from real_estate import settings
from real_estate.model_mixin import User


class RequestOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        original_email = value.strip().lower()
        # normalized_email = normalize_gmail(original_email)

        if '+' in original_email.split('@')[0]:
            raise serializers.ValidationError("Email addresses with '+' are not allowed.")

        blocked_domains = ['tempmail.com', 'mailinator.com', 'yopmail.com']
        # domain = normalized_email.split('@')[-1]
        if original_email in blocked_domains:
            raise serializers.ValidationError("Disposable email addresses are not allowed.")
        return original_email


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=250, required=True)
    password = serializers.CharField(required=True)

    def validate(self, attrs):
        username = attrs.get('username')
        if not username:
            raise exceptions.ValidationError({'username': ['This field is required and may not be null or blank.']})

        email = username.strip().lower()

        email_regex = r'^[A-Za-z0-9._%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
        if not re.match(email_regex, email):
            raise exceptions.ValidationError({'username': ['Enter a valid email address.']})

        if '+' in username:
            raise exceptions.ValidationError({'username': ['Email addresses with "+" are not allowed.']})

        blocked_domains = ['tempmail.com', 'mailinator.com', 'yopmail.com']
        domain = email.split('@')[-1]
        if domain in blocked_domains:
            raise exceptions.ValidationError({'username': ['Disposable email addresses are not allowed.']})
        # normalized_email = normalize_gmail(email)

        user = User.objects.filter(
            Q(username__iexact=email) | Q(email__iexact=email), is_active=True
        ).last()
        if not user:
            raise exceptions.ValidationError({'detail': 'No user registered with these credentials.'})

        password = attrs.get('password')
        if not user.check_password(password):
            raise exceptions.AuthenticationFailed({'detail': 'Incorrect password.'})

        attrs['user'] = user
        return attrs


class UserRegistrationSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    confirm_password = serializers.CharField(write_only=True)
    date_of_birth = serializers.DateField(required=False)
    is_vendor = serializers.BooleanField(required=False)
    picture = serializers.ImageField(required=False)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password', 'confirm_password', 'date_of_birth', 'picture',
                  'is_vendor']
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
        date_of_birth = validated_data.pop('date_of_birth', None)
        is_vendor = validated_data.pop('is_vendor', False)
        picture = validated_data.pop('picture', None)
        validated_data.pop('confirm_password')

        user = User.objects.create_user(
            username=validated_data['email'], email=validated_data['email'],
            first_name=validated_data['first_name'], last_name=validated_data['last_name'],
            password=validated_data['password'],
        )

        Profile.objects.create(
            user=user, date_of_birth=date_of_birth, picture=picture, is_vendor=is_vendor
        )
        otp_code = random.randint(100000, 999999)

        OTP.objects.update_or_create(
            email=validated_data['email'],
            defaults={
                "otp": otp_code,
                "valid_until": datetime.datetime.now() + datetime.timedelta(minutes=20),
            },
        )
        send_mail(
            "Your OTP Code",
            f"Your OTP code is {otp_code}. It is valid for 10 minutes.",
            settings.DEFAULT_FROM_EMAIL,
            [validated_data['email']],
            fail_silently=False,
        )
        user.profile.save()
        return user

    def send_otp_email(self, email, otp):
        from django.core.mail import send_mail
        send_mail(
            subject='Your OTP Code',
            message=f'Your OTP code is {otp}',
            from_email='no-reply@yourdomain.com',
            recipient_list=[email],
            fail_silently=False,
        )


class OTPSerializer(serializers.ModelSerializer):

    class Meta:
        model = OTP
        fields = '__all__'


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


class KycProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return obj.user.get_full_name() if obj.user else None

    def get_email(self, obj):
        return obj.user.email if obj.user else None

    class Meta:
        model = Profile
        fields = ['full_name', 'mobile_number', 'email']


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
    mobile_number1 = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    mobile_number2 = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    other_email = serializers.EmailField(allow_null=True, allow_blank=True, required=False)
    pan_remarks = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    voter_number = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    mobile_number = serializers.CharField(required=True)
    kyc_video = serializers.FileField(required=False)
    pan_number = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    aadhar_number = serializers.CharField(required=False)
    referral_code = serializers.CharField(required=False)
    pin_code = serializers.CharField(required=False)
    city = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.filter(status='active'), many=False, required=False, allow_null=True
    )
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
    gst_number = serializers.CharField(required=False, allow_blank=True)
    city = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.filter(status='active'), many=False, required=False, allow_null=True
    )
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


class CreateKycRequestSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    account_number = serializers.CharField(required=True)
    ifsc_code = serializers.CharField(required=True)
    new_account_number = serializers.CharField(max_length=20, required=True)
    new_ifsc_code = serializers.CharField(max_length=20, required=True)
    new_account_holder_name = serializers.CharField(max_length=100, required=True)
    new_bank_name = serializers.CharField(max_length=100, required=True)
    full_name = serializers.CharField(max_length=200, required=False)

    class Meta:
        model = ChangeRequest
        fields = '__all__'

    def validate(self, attrs):
        user = self.context['request'].user
        new_account_number = attrs.get('new_account_number').strip()
        account_number = attrs.get('account_number').strip()

        if new_account_number == account_number:
            raise serializers.ValidationError("New account number cannot be the same as the current account number.")

        return attrs


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


class AppVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppVersion
        fields = '__all__'


class UserDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    is_primary_account = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_is_primary_account(self, obj):
        return obj.email == obj.username

    class Meta:
        model = User
        fields = ('id', 'username', 'full_name', 'is_primary_account')


class UserKycRequestSerializer(serializers.ModelSerializer):

    class Meta:
        model = BankDetails
        fields = ('id', 'account_number', 'account_holder_name', 'ifsc_code', 'bank_name')
