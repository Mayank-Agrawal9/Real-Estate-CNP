from rest_framework import serializers

from accounts.models import Profile
from master.models import RewardMaster
from p2pmb.models import Package
from payment_app.choices import PAYMENT_METHOD
from payment_app.models import Transaction, UserWallet
from .choices import INVESTMENT_GUARANTEED_TYPE
from .models import User, Investment, Commission, RefundPolicy, FundWithdrawal, SuperAgency, Agency, \
    FieldAgent, RewardEarned, PPDAccount, InvestmentInterest


class SuperAgencySerializer(serializers.ModelSerializer):
    class Meta:
        model = SuperAgency
        fields = '__all__'


class AgencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Agency
        fields = '__all__'


class FieldAgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldAgent
        fields = '__all__'


class InvestmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Investment
        fields = '__all__'


class CreateInvestmentSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(max_digits=12, required=True, decimal_places=2)
    gst = serializers.DecimalField(max_digits=12, required=True, decimal_places=2)
    payment_slip = serializers.ImageField(required=True)
    payment_method = serializers.ChoiceField(choices=PAYMENT_METHOD, required=True)
    remarks = serializers.CharField(required=True)
    deposit_transaction_id = serializers.CharField(max_length=200, required=True)
    investment_guaranteed_type = serializers.ChoiceField(choices=INVESTMENT_GUARANTEED_TYPE, required=False)
    package = serializers.PrimaryKeyRelatedField(
        queryset=Package.objects.filter(status='active'), many=True, required=False, allow_empty=True
    )
    referral_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True), required=False, allow_empty=True
    )
    pay_method = serializers.ChoiceField(choices=['main_wallet', 'app_wallet', 'new'], default='new')

    class Meta:
        model = Investment
        fields = '__all__'

    def validate(self, attrs):
        user = self.context['request'].user
        amount = attrs.get('amount')
        pay_method = attrs.get('pay_method')
        # if not user.profile.is_kyc:
        #     raise serializers.ValidationError("User has not completed their KYC. Please complete KYC first.")
        if pay_method == 'main_wallet':
            user_wallet = UserWallet.objects.filter(user=user, status='active').first()

            if not user_wallet:
                raise serializers.ValidationError("User wallet not found.")

            if user_wallet.main_wallet_balance < amount:
                raise serializers.ValidationError("Insufficient balance in main wallet.")
            user_wallet.main_wallet_balance -= amount
            user_wallet.save()

        if pay_method == 'app_wallet':
            user_wallet = UserWallet.objects.filter(user=user, status='active').first()

            if not user_wallet:
                raise serializers.ValidationError("User wallet not found.")

            if user_wallet.app_wallet_balance < amount:
                raise serializers.ValidationError("Insufficient balance in app wallet.")
            user_wallet.app_wallet_balance -= amount
            user_wallet.save()
        attrs['user'] = user
        return attrs

    def create(self, validated_data):
        from django.db import transaction
        with transaction.atomic():
            user = self.context['request'].user
            packages = validated_data.pop('package', None) or []
            transaction_data = {
                'created_by': user,
                'sender': user,
                'amount': validated_data.pop('amount'),
                'taxable_amount': validated_data.pop('gst'),
                'deposit_transaction_id': validated_data.pop('deposit_transaction_id'),
                'transaction_type': "investment",
                'transaction_status': "pending",
                'payment_slip': validated_data.pop('payment_slip'),
                'payment_method': validated_data.pop('payment_method'),
                'remarks': validated_data.pop('remarks'),
            }

            transaction = Transaction.objects.create(**transaction_data)
            validated_data['created_by'] = user
            validated_data['amount'] = transaction_data.get('amount')
            validated_data['gst'] = transaction_data.get('taxable_amount')
            validated_data['transaction_id'] = transaction
            investment = Investment.objects.create(**validated_data)
            if packages:
                investment.package.set(packages)
            return investment


class CommissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commission
        fields = '__all__'


class RefundPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = RefundPolicy
        fields = '__all__'


class FundWithdrawalSerializer(serializers.ModelSerializer):
    tds_amount = serializers.SerializerMethodField()

    class Meta:
        model = FundWithdrawal
        fields = '__all__'

    def get_tds_amount(self, obj):
        return round(obj.withdrawal_amount * 0.05, 2) if obj.withdrawal_amount else 0


class InvestmentInterestSerializer(serializers.ModelSerializer):
    investment = serializers.SerializerMethodField()

    def get_investment(self, obj):
        return {
            'id': obj.investment.id,
            'amount': obj.investment.amount,
            'user': {'id': obj.investment.user.id, 'username': obj.investment.user.username,
                     'full_name': obj.investment.user.get_full_name()},
            'investment_type': obj.investment.investment_guaranteed_type
        }

    class Meta:
        model = InvestmentInterest
        fields = '__all__'


class PPDModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = PPDAccount
        fields = '__all__'


class RewardEarnedSerializer(serializers.ModelSerializer):
    class Meta:
        model = RewardEarned
        fields = '__all__'


class GetAllEarnedReward(serializers.ModelSerializer):
    reward = serializers.SerializerMethodField()

    def get_reward(self, obj):
        if obj.reward:
            return {'id': obj.reward.id, 'name': obj.reward.name, 'turnover_threshold': obj.reward.turnover_threshold}

    class Meta:
        model = RewardEarned
        fields = '__all__'


class RefundPolicyInitiateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefundPolicy
        fields = '__all__'
        read_only_fields = ('refund_initiate_date', 'refund_process_date', 'amount_refunded', 'deduction_percentage')

    def calculate_refund(self, refund_type, amount_paid):
        """Calculate the refund amount and deduction percentage."""
        deduction_percentage = 0
        refund_percentage = 0

        if refund_type == 'within_1_month':
            deduction_percentage = 50
        elif refund_type == 'within_3_months':
            deduction_percentage = 60
        elif refund_type == 'within_6_months':
            deduction_percentage = 75
        elif refund_type == 'within_1_year':
            deduction_percentage = 90
        else:  # No refund
            deduction_percentage = 100

        refund_percentage = 100 - deduction_percentage
        amount_refunded = (amount_paid * refund_percentage) / 100
        return amount_refunded, deduction_percentage

    def create(self, validated_data):
        refund_type = validated_data.get('refund_type')
        amount_paid = validated_data.get('amount_refunded')
        amount_refunded, deduction_percentage = self.calculate_refund(refund_type, amount_paid)

        validated_data['amount_refunded'] = amount_refunded
        validated_data['deduction_percentage'] = deduction_percentage
        validated_data['refund_status'] = 'processed'
        validated_data['refund_process_date'] = serializers.DateField().to_representation(serializers.DateField().to_internal_value('today'))

        return super().create(validated_data)


class GetSuperAgencySerializer(serializers.ModelSerializer):
    referral_by = serializers.SerializerMethodField()

    def get_referral_by(self, obj):
        profile = Profile.objects.filter(id=42).last()
        if not profile:
            return None
        return {'name': profile.user.get_full_name(), 'code': profile.referral_code,
                'state': profile.state.name if profile.state else None,
                'city': profile.city.name if profile.city else None}

    class Meta:
        model = SuperAgency
        fields = '__all__'


class GetAgencySerializer(serializers.ModelSerializer):
    company = serializers.SerializerMethodField()

    def get_company(self, obj):
        if not obj.company:
            return None
        return {'id': obj.company.id, 'name': obj.company.name,
                'code': obj.company.profile.referral_code,
                'address': obj.company.office_address,
                'contact_no': obj.company.phone_number}

    class Meta:
        model = Agency
        fields = '__all__'


class GetFieldAgentSerializer(serializers.ModelSerializer):
    agency = serializers.SerializerMethodField()
    profile = serializers.SerializerMethodField()

    def get_agency(self, obj):
        if not obj.agency:
            return None

        return {'id': obj.agency.id,
                'name': obj.agency.name,
                'code': obj.agency.created_by.profile.referral_code,
                'address': obj.agency.office_address,
                'contact_no': obj.agency.phone_number, 'email': obj.agency.email}

    def get_profile(self, obj):
        if not obj.profile:
            return None
        return {
            'name': obj.profile.user.get_full_name(),
            'state': obj.profile.state.name if obj.profile.state else None,
            'city': obj.profile.city.name if obj.profile.city else None,
        }

    class Meta:
        model = FieldAgent
        fields = '__all__'


class GetRewardSerializer(serializers.ModelSerializer):

    class Meta:
        model = RewardMaster
        fields = '__all__'


class IncomeCommissionSerializer(serializers.ModelSerializer):
    commission_by = serializers.SerializerMethodField()

    def get_commission_by(self, obj):
        if not obj.commission_by:
            return None
        return {
            'id': obj.commission_by.id,
            'name': obj.commission_by.get_full_name(),
            'username': obj.commission_by.username
        }

    class Meta:
        model = Commission
        fields = '__all__'