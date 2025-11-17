import uuid

from django.db import transaction
from rest_framework import serializers

from accounts.models import Profile, UserPersonalDocument
from master.models import RewardMaster, City
from p2pmb.models import Package
from payment_app.choices import PAYMENT_METHOD
from payment_app.models import Transaction, UserWallet
from .calculation import calculate_and_send_super_agency_commission, calculate_and_send_agency_commission
from .choices import INVESTMENT_GUARANTEED_TYPE
from .models import User, Investment, Commission, RefundPolicy, FundWithdrawal, SuperAgency, Agency, \
    FieldAgent, RewardEarned, PPDAccount, InvestmentInterest, AgencyPackagePurchase


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
                'receiver': user,
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
    commission_by = serializers.SerializerMethodField()

    def get_commission_by(self, obj):
        if not obj.commission_by:
            return None
        return {
            'id': obj.commission_by.id,
            'name': obj.commission_by.get_full_name(),
            'referral_code': obj.commission_by.profile.referral_code,
        }

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


class UserPersonalDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPersonalDocument
        fields = ['id', 'attachment', 'type']


class BuyPackageSerializer(serializers.Serializer):
    """Main serializer for package purchase with FormData support"""
    package_id = serializers.IntegerField()
    applicable_for = serializers.ChoiceField(choices=['super_agency', 'agency', 'field_agent'])
    documents = UserPersonalDocumentSerializer(many=True, required=False)

    # Super Agency fields (optional based on role)
    super_agency_name = serializers.CharField(max_length=250, required=False)
    super_agency_type = serializers.CharField(max_length=250, required=False)
    super_agency_phone_number = serializers.CharField(max_length=15, required=False, allow_blank=True)
    super_agency_pan_number = serializers.CharField(max_length=10, required=False, allow_blank=True)
    super_agency_gst_number = serializers.CharField(max_length=15, required=False, allow_blank=True)
    super_agency_email = serializers.EmailField(required=False, allow_blank=True)
    super_agency_office_address = serializers.CharField(required=False, allow_blank=True)
    super_agency_office_area = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    super_agency_city_id = serializers.IntegerField(required=False)

    # Agency fields (optional based on role)
    agency_name = serializers.CharField(max_length=250, required=False)
    agency_type = serializers.CharField(max_length=250, required=False)
    agency_phone_number = serializers.CharField(max_length=15, required=False, allow_blank=True)
    agency_pan_number = serializers.CharField(max_length=10, required=False, allow_blank=True)
    agency_gst_number = serializers.CharField(max_length=15, required=False, allow_blank=True)
    agency_email = serializers.EmailField(required=False, allow_blank=True)
    agency_office_address = serializers.CharField(required=False, allow_blank=True)
    agency_office_area = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    agency_turnover = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    agency_city_id = serializers.IntegerField(required=False)

    # Field Agent fields (optional based on role)
    field_agent_turnover = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    field_agent_city_id = serializers.IntegerField(required=False)

    def validate_package_id(self, value):
        try:
            package = Package.objects.get(id=value, status='active')
        except Package.DoesNotExist:
            raise serializers.ValidationError("Package not found or inactive.")
        return value

    def validate(self, data):
        user = self.context['request'].user
        package = Package.objects.get(id=data['package_id'])
        role = data['applicable_for']

        if package.applicable_for != role:
            raise serializers.ValidationError({
                'applicable_for': f"This package is only available for {package.get_applicable_for_display()}."
            })

        # Validate role-specific required fields
        if role == 'super_agency':
            self._validate_super_agency_data(data)
        elif role == 'agency':
            self._validate_agency_data(data)
        elif role == 'field_agent':
            self._validate_field_agent_data(data)

        # Check wallet balance
        wallet = UserWallet.objects.filter(status='active', user=user).last()
        if not wallet:
            raise serializers.ValidationError("Wallet not found. Please contact support.")

        if not wallet.has_sufficient_balance(package.amount, 'main_wallet'):
            raise serializers.ValidationError(
                f"Insufficient balance. Required: {package.amount}"
            )

        data['package'] = package
        data['wallet'] = wallet
        data['user'] = user
        return data

    def _validate_super_agency_data(self, data):
        """Validate Super Agency specific data"""
        # Check if user already has a super agency
        super_agency = self.context['request'].user.profile.is_super_agency if self.context['request'].user.profile \
            else False
        if super_agency:
            raise serializers.ValidationError({"applicable_for": "You are already enrolled as a Super Agency."})

        required_fields = ['super_agency_name', 'super_agency_type', 'super_agency_city_id',
                           'super_agency_phone_number', 'super_agency_pan_number', 'super_agency_gst_number',
                           'agency_office_address', 'agency_office_area']
        for field in required_fields:
            if not data.get(field):
                raise serializers.ValidationError({field: f"This field is required for Super Agency enrollment."})

        # Validate city
        try:
            city = City.objects.get(id=data['super_agency_city_id'], status='active')
        except City.DoesNotExist:
            raise serializers.ValidationError({"super_agency_city_id": "Invalid city selected."})

        # Check if super agency already exists in this city
        if SuperAgency.objects.filter(city=city, status='active').exists():
            raise serializers.ValidationError({
                "super_agency_city_id": "A Super Agency already exists in this city. Only one Super Agency is "
                                        "allowed per city."
            })

        data['super_agency_city'] = city

    def _validate_agency_data(self, data):
        """Validate Agency specific data"""
        is_default = False

        # Check if user already has a super agency
        agency = self.context['request'].user.profile.is_agency if self.context['request'].user.profile \
            else False
        if agency:
            raise serializers.ValidationError({"applicable_for": "You are already enrolled as a Agency."})

        required_fields = ['agency_name', 'agency_type', 'agency_city_id', 'agency_phone_number',
                           'agency_pan_number', 'agency_gst_number', 'agency_email', 'agency_office_address']
        for field in required_fields:
            if not data.get(field):
                raise serializers.ValidationError({field: f"This field is required for Agency enrollment."})

        # Validate city
        try:
            city = City.objects.get(id=data['agency_city_id'], status='active')
        except City.DoesNotExist:
            raise serializers.ValidationError({"agency_city_id": "Invalid city selected."})

        # Validate super agency
        try:
            super_agency = SuperAgency.objects.filter(city=city, status='active').last()
            if not super_agency:
                super_agency = SuperAgency.objects.filter(is_default=True, status='active').last()
                is_default = True
                if not super_agency:
                    raise serializers.ValidationError({"agency_super_agency_id": "Super Agency does not exist."})
        except SuperAgency.DoesNotExist:
            raise serializers.ValidationError({"agency_super_agency_id": "Invalid Super Agency selected."})

        # Check if agency city matches super agency city
        if super_agency.city != city and not is_default:
            raise serializers.ValidationError({
                "agency_city_id": "Agency must be in the same city as the Super Agency."
            })

        # Check agency limit
        current_agencies = Agency.objects.filter(company=super_agency, city=city, status='active').count()

        if current_agencies >= super_agency.max_agencies:
            raise serializers.ValidationError({
                "agency_super_agency_id": f"This Super Agency has reached its maximum limit of "
                                          f"{super_agency.max_agencies} agencies."
            })
        data['agency_super_agency'] = super_agency
        data['agency_city'] = city

    def _validate_field_agent_data(self, data):
        """Validate Field Agent specific data"""
        # Check if user already has a super agency
        field_agent = self.context['request'].user.profile.is_field_agent if self.context['request'].user.profile \
            else False
        if field_agent:
            raise serializers.ValidationError({"applicable_for": "You are already enrolled as a Field Agent."})
        required_fields = ['field_agent_city_id']
        for field in required_fields:
            if not data.get(field):
                raise serializers.ValidationError({field: f"This field is required for Field Agent enrollment."})

        # Validate city
        try:
            city = City.objects.get(id=data['field_agent_city_id'], status='active')
        except City.DoesNotExist:
            raise serializers.ValidationError({"field_agent_city_id": "Invalid city selected."})

        # Validate agency
        try:
            agency = Agency.objects.filter(city=city, status='active').last()
            if not agency:
                agency = Agency.objects.filter(is_default=True, status='active').last()
                if not agency:
                    raise serializers.ValidationError({"field_agent_agency_id": "Not Found any agency."})
        except Agency.DoesNotExist:
            raise serializers.ValidationError({"field_agent_agency_id": "Invalid Agency selected."})

        # Check if field agent city matches agency city
        if agency.city != city:
            raise serializers.ValidationError({
                "field_agent_city_id": "Field Agent must be in the same city as the Agency."
            })

        current_field_agents = FieldAgent.objects.filter(agency=agency, status='active').count()

        if current_field_agents >= 1000:
            raise serializers.ValidationError({
                "field_agent_agency_id": "This Agency has reached its maximum limit of 1000 field agents."
            })

        data['field_agent_agency'] = agency
        data['field_agent_city'] = city

    def create(self, validated_data):
        user = self.context['request'].user
        package = validated_data['package']
        wallet = validated_data['wallet']
        role = validated_data['applicable_for']
        document_data = validated_data.pop('documents', [])

        with transaction.atomic():
            transaction_id = f"PKG-{uuid.uuid4().hex[:12].upper()}"

            # Deduct from wallet
            if not wallet.deduct_balance(package.amount, "main_wallet"):
                raise serializers.ValidationError("Failed to process payment.")

            # Create package purchase record
            purchase = AgencyPackagePurchase.objects.create(
                user=user, package=package,
                amount_paid=package.amount, buy_for=role,
                transaction_id=transaction_id
            )
            # try:
            created_entity = None
            if role == 'super_agency':
                created_entity = self._create_super_agency(validated_data, user, purchase)
            elif role == 'agency':
                created_entity = self._create_agency(validated_data, user, purchase)
            elif role == 'field_agent':
                created_entity = self._create_field_agent(validated_data, user, purchase)

            for doc in document_data:
                UserPersonalDocument.objects.create(
                    user=user,
                    attachment=doc['attachment'], type=doc['type']
                )

            # except Exception as e:
            #     raise serializers.ValidationError(f"Failed to create enrollment: {str(e)}")

            Transaction.objects.create(
                receiver=user, created_by=user,
                transaction_status='approved',
                amount=package.amount,
                transaction_type='investment',
                payment_method='wallet',
                remarks=f"Package purchase: {package.name} - {role}",
                deposit_transaction_id=transaction_id
            )

            return purchase

    def _create_super_agency(self, data, user, purchase):
        """Create Super Agency entity"""
        super_agency = SuperAgency.objects.create(
            created_by=user,
            profile=user.profile,
            name=data['super_agency_name'],
            type=data['super_agency_type'],
            phone_number=data.get('super_agency_phone_number', ''),
            pan_number=data.get('super_agency_pan_number', ''),
            gst_number=data.get('super_agency_gst_number', ''),
            email=data.get('super_agency_email', ''),
            office_address=data.get('super_agency_office_address', ''),
            office_area=data.get('super_agency_office_area', 650),
            income=0,
            turnover=0,
            city=data['super_agency_city']
        )
        purchase.super_agency = super_agency
        purchase.status = 'completed'
        purchase.save()
        user.profile.is_super_agency = True
        user.profile.save()
        return super_agency

    def _create_agency(self, data, user, purchase):
        """Create Agency entity"""
        agency = Agency.objects.create(
            created_by=user,
            company=data['agency_super_agency'],
            name=data['agency_name'],
            type=data['agency_type'],
            phone_number=data.get('agency_phone_number', ''),
            pan_number=data.get('agency_pan_number', ''),
            gst_number=data.get('agency_gst_number', ''),
            email=data.get('agency_email', ''),
            office_address=data.get('agency_office_address', ''),
            office_area=data.get('agency_office_area', 0),
            turnover=0,
            city=data['agency_city']
        )
        purchase.agency = agency
        purchase.status = 'completed'
        purchase.save()
        user.profile.is_agency = True
        user.profile.save()
        calculate_and_send_super_agency_commission(data['agency_super_agency'].id, purchase, data['agency_name'])
        return agency

    def _create_field_agent(self, data, user, purchase):
        """Create Field Agent entity"""
        field_agent = FieldAgent.objects.create(
            created_by=user,
            profile=user.profile,
            agency=data['field_agent_agency'],
            turnover=0,
            city=data['field_agent_city']
        )
        purchase.field_agent = field_agent
        purchase.status = 'completed'
        purchase.save()
        user.profile.is_field_agent = True
        user.profile.save()
        calculate_and_send_agency_commission(data['field_agent_agency'].id, purchase)
        return field_agent

    def _save_documents(self, document_files, documents_metadata, user, entity):
        """Save uploaded documents"""
        metadata_map = {item.get('index', idx): item for idx, item in enumerate(documents_metadata)}
        for idx, file in enumerate(document_files):
            metadata = metadata_map.get(idx, {})
            UserPersonalDocument.objects.create(
                profile=user.profile,
                attachment=file,
                type=metadata.get('type', 'kyc_photo'),
                remarks=metadata.get('remarks', ''),
                approval_status='pending'
            )
