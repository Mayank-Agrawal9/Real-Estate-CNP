from decimal import Decimal

from django.contrib.auth.models import User
from django.db.models import Q, Sum
from rest_framework import serializers, exceptions

from accounts.models import Profile, BankDetails, UserPersonalDocument, ChangeRequest
from agency.models import Investment, SuperAgency, Agency, FieldAgent, FundWithdrawal, RewardEarned, InvestmentInterest
from master.models import City, State
from p2pmb.models import Package, MLMTree, Commission, RoyaltyEarned, ExtraRewardEarned
from payment_app.models import Transaction, UserWallet
from property.models import Property
from property.serializers import GetMediaDataSerializer, GetNearbyFacilitySerializer, GetPropertyFeatureSerializer
from web_admin.models import ManualFund, ContactUsEnquiry, PropertyInterestEnquiry, FunctionalityAccessPermissions, \
    UserFunctionalityAccessPermission, CompanyInvestment, TDSPercentage


class ProfileSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    verified_by = serializers.SerializerMethodField()

    def get_user(self, obj):
        return {
            'id': obj.user.id,
            'first_name': obj.user.first_name,
            'last_name': obj.user.last_name,
            'email': obj.user.email,
            'username': obj.user.username,
        }

    def get_verified_by(self, obj):
        if not obj.verified_by:
            return None
        return {
            'id': obj.verified_by.id,
            'first_name': obj.verified_by.first_name,
            'last_name': obj.verified_by.last_name,
            'email': obj.verified_by.email,
            'username': obj.verified_by.username,
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
        fields = ('attachment', 'type', 'date_created', 'id', 'approval_status', 'rejection_reason')


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


class TDSPercentageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TDSPercentage
        fields = '__all__'


class TDSPercentageListSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()
    updated_by = serializers.SerializerMethodField()

    def get_created_by(self, obj):
        if not obj.created_by:
            return None
        return {'id': obj.created_by.id,
                'name': obj.created_by.get_full_name(), 'email': obj.created_by.email}

    def get_updated_by(self, obj):
        if not obj.updated_by:
            return None
        return {'id': obj.updated_by.id,
                'name': obj.updated_by.get_full_name(), 'email': obj.updated_by.email}

    class Meta:
        model = TDSPercentage
        fields = '__all__'


class CompanyInvestmentSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()

    def get_created_by(self, obj):
        if not obj.created_by:
            return None
        return {
            'id': obj.created_by.id,
            'name': obj.created_by.get_full_name(),
            'email': obj.created_by.email,
            'username': obj.created_by.username,
        }

    class Meta:
        model = CompanyInvestment
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


class UserCreateSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    permission = serializers.PrimaryKeyRelatedField(
        queryset=FunctionalityAccessPermissions.objects.active(), required=True
    )
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    mobile_number = serializers.CharField(required=True)
    city = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.active(), required=True
    )
    state = serializers.PrimaryKeyRelatedField(
        queryset=State.objects.active(), required=True
    )
    pin_code = serializers.CharField(required=True)
    gender = serializers.ChoiceField(choices=[("Male", "Male"), ("Female", "Female")], required=True)
    date_of_birth = serializers.DateField(required=True)
    picture = serializers.ImageField(required=False)

    def validate_username(self, value):
        """Ensure the username is unique."""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_email(self, value):
        """Ensure the email is unique."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        username = attrs.get('email')

        user = User.objects.filter(Q(username__exact=username) | Q(email__exact=username), is_active=True,
                                   is_staff=True).last()
        if not user:
            raise exceptions.AuthenticationFailed({'detail': 'No user registered with this credentials.'})

        password = attrs.get('password')
        if not user.check_password(password):
            raise exceptions.AuthenticationFailed({'detail': 'Incorrect password.'}, code='invalid')

        attrs['user'] = user
        return attrs


class UserPermissionProfileSerializer(serializers.ModelSerializer):
    permission = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()

    def get_permission(self, obj):
        permission = UserFunctionalityAccessPermission.objects.filter(user=obj.user).select_related('permission').last()
        if permission:
            return {'id': permission.id, 'permission_id': permission.permission.id, 'name': permission.permission.name}
        return None

    def get_city(self, obj):
        if obj.city:
            return {'id': obj.city.id, 'name': obj.city.name}

    def get_user(self, obj):
        return {'id': obj.user.id, 'name': obj.user.get_full_name(), 'email': obj.user.email}

    class Meta:
        model = Profile
        fields = ('id', 'permission', 'city', 'user', 'date_of_birth', 'gender', 'mobile_number')


class ListWithDrawRequest(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    send_amount = serializers.SerializerMethodField()
    action_taken_by = serializers.SerializerMethodField()

    def get_user(self, obj):
        return {'id': obj.user.id, 'name': obj.user.get_full_name(), 'email': obj.user.email,
                'username': obj.user.username}

    def get_action_taken_by(self, obj):
        if not obj.action_taken_by:
            return None
        return {'id': obj.action_taken_by.id, 'name': obj.action_taken_by.get_full_name(),
                'email': obj.action_taken_by.email, 'username': obj.action_taken_by.username}

    def get_send_amount(self, obj):
        return (obj.withdrawal_amount - obj.taxable_amount) or 0

    class Meta:
        model = FundWithdrawal
        fields = ('id', 'user', 'withdrawal_amount', 'withdrawal_date', 'is_paid', 'date_created',
                  'withdrawal_status', 'rejection_reason', 'taxable_amount', 'send_amount',
                  'action_taken_by', 'action_date')


class UserWithWorkingIDSerializer(serializers.ModelSerializer):
    parent = serializers.SerializerMethodField()
    child = serializers.SerializerMethodField()
    referral_by = serializers.SerializerMethodField()
    is_working_id = serializers.SerializerMethodField()

    class Meta:
        model = MLMTree
        fields = ['id', 'parent', 'child', 'is_working_id', 'referral_by']

    def get_parent(self, obj):
        if not obj.parent:
            return None
        return {
            'id': obj.parent.id,
            'name': obj.parent.get_full_name(),
            'username': obj.parent.username
        }

    def get_child(self, obj):
        if not obj.child:
            return None
        return {
            'id': obj.child.id,
            'name': obj.child.get_full_name(),
            'username': obj.child.username
        }

    def get_referral_by(self, obj):
        if not obj.referral_by:
            return None
        return {
            'id': obj.referral_by.id,
            'name': obj.referral_by.get_full_name(),
            'username': obj.referral_by.username
        }

    def get_is_working_id(self, obj):
        user = obj.child
        if not user:
            return False

        if not hasattr(self, '_investment_map'):
            self._load_investment_and_referral_data()

        user_investment = self._investment_map.get(user.id, Decimal('0'))

        if user_investment == 0:
            return False

        referrals = self._referral_map.get(user.id, [])
        return len(referrals) >= 2

    def _load_investment_and_referral_data(self):
        investments = Investment.objects.filter(
            status='active', investment_type='p2pmb', is_approved=True,
            package__isnull=False, pay_method='main_wallet'
        ).values('user_id').annotate(total_amount=Sum('amount'))

        self._investment_map = {item['user_id']: item['total_amount'] for item in investments}
        referrals = MLMTree.objects.values_list('referral_by_id', 'child_id')
        self._referral_map = {}
        for referral_by_id, child_id in referrals:
            self._referral_map.setdefault(referral_by_id, []).append(child_id)


class GetAllCommissionSerializer(serializers.ModelSerializer):
    commission_by = serializers.SerializerMethodField()

    def get_commission_by(self, obj):
        if not obj.commission_by:
            return None
        return {
            'first_name': obj.commission_by.first_name,
            'last_name': obj.commission_by.last_name,
            'email': obj.commission_by.email,
            'username': obj.commission_by.username
        }

    class Meta:
        model = Commission
        fields = '__all__'


class TransactionDetailSerializer(serializers.ModelSerializer):
    sender = serializers.SerializerMethodField()
    receiver = serializers.SerializerMethodField()

    def get_sender(self, obj):
        if not obj.sender:
            return None
        return {
            'id': obj.sender.id,
            'username': obj.sender.username,
            'name': obj.sender.get_full_name(),
        }

    def get_receiver(self, obj):
        if not obj.receiver:
            return None
        return {
            'id': obj.receiver.id,
            'username': obj.receiver.username,
            'name': obj.receiver.get_full_name(),
        }

    class Meta:
        model = Transaction
        fields = '__all__'


class AdminChangeRequestSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()

    def get_created_by(self, obj):
        if not obj.created_by:
            return None
        return {
            'id': obj.created_by.id,
            'username': obj.created_by.username,
            'name': obj.created_by.get_full_name(),
        }

    class Meta:
        model = ChangeRequest
        fields = '__all__'


class RewardEarnedAdminSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    reward = serializers.SerializerMethodField()

    def get_user(self, obj):
        if obj.user:
            return {
                'id': obj.user.id,
                'name': obj.user.get_full_name(),
                'email': obj.user.email
            }
        return None

    def get_reward(self, obj):
        if obj.reward:
            return {
                'id': obj.reward.id,
                'name': obj.reward.name,
                'email': obj.reward.turnover_threshold
            }
        return None

    class Meta:
        model = RewardEarned
        fields = '__all__'


class RoyaltyEarnedAdminSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    royalty = serializers.SerializerMethodField()

    def get_user(self, obj):
        if obj.user:
            return {
                'id': obj.user.id,
                'name': obj.user.get_full_name(),
                'email': obj.user.email
            }
        return None

    def get_royalty(self, obj):
        if obj.royalty:
            return {
                'id': obj.royalty.id,
                'total_turnover': obj.royalty.total_turnover,
                'star_income': obj.royalty.star_income,
                'two_star_income': obj.royalty.two_star_income,
                'three_star_income': obj.royalty.three_star_income,
                'lifetime_income': obj.royalty.lifetime_income,
            }
        return None

    class Meta:
        model = RoyaltyEarned
        fields = '__all__'


class ExtraRewardEarnedAdminSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    extra_reward = serializers.SerializerMethodField()

    def get_user(self, obj):
        if obj.user:
            return {
                'id': obj.user.id,
                'name': obj.user.get_full_name(),
                'email': obj.user.email
            }
        return None

    def get_extra_reward(self, obj):
        if obj.extra_reward:
            return {
                'id': obj.extra_reward.id,
                'start_date': obj.extra_reward.start_date,
                'star_income': obj.extra_reward.end_date,
                'two_star_income': obj.extra_reward.reward_type,
                'three_star_income': obj.extra_reward.description,
            }
        return None

    class Meta:
        model = ExtraRewardEarned
        fields = '__all__'


class ROIEarnedAdminSerializer(serializers.ModelSerializer):
    investment = serializers.SerializerMethodField()

    def get_investment(self, obj):
        if obj.investment and obj.investment.user:
            return {
                'id': obj.investment.user.id,
                'name': obj.investment.user.get_full_name(),
                'email': obj.investment.user.email
            }
        return None

    class Meta:
        model = InvestmentInterest
        fields = '__all__'


class GetAllMLMChildSerializer(serializers.ModelSerializer):
    child = serializers.SerializerMethodField()

    def get_child(self, obj):
        if not obj.child:
            return None
        return {
            'id': obj.child.id,
            'name': obj.child.get_full_name(),
            'referral_code': obj.child.profile.referral_code,
            'email': obj.child.email,
        }

    class Meta:
        model = MLMTree
        fields = ('child', )


class UserWalletSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    investment = serializers.SerializerMethodField()

    def get_user(self, obj):
        return {
            'id': obj.user.id,
            'name': obj.user.get_full_name(),
            'email': obj.user.email,
            'mobile_number': obj.user.profile.mobile_number if obj.user.profile else None,
            'pan_number': obj.user.profile.pan_number  if obj.user.profile else None
        }

    def get_investment(self, obj):
        investments = Investment.objects.filter(
            status='active', package__isnull=False, investment_type='p2pmb', user=obj.user
        )
        if not investments:
            return {
                'last_top_up_value': 0,
                'total_top_up_value': 0,
            }
        last_investment = investments.order_by('-date_created').first()
        last_invested = last_investment.amount if last_investment else Decimal(0)
        total_invested = investments.aggregate(
            total=Sum('amount'))['total'] or Decimal(0)
        return {
            'last_top_up_value': last_invested,
            'total_top_up_value': total_invested,
        }

    class Meta:
        model = UserWallet
        fields = ('date_created', 'user', 'investment', 'main_wallet_balance', 'tds_amount', 'admin_amount')