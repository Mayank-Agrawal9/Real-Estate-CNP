from rest_framework import serializers
from .models import User, Investment, Commission, Reward, RefundPolicy, FundWithdrawal, PPDModel, SuperAgency, Agency, \
    FieldAgent, RewardEarned, PPDAccount


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


class CommissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commission
        fields = '__all__'


class RewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reward
        fields = '__all__'


class RefundPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = RefundPolicy
        fields = '__all__'


class FundWithdrawalSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundWithdrawal
        fields = '__all__'


class PPDModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = PPDAccount
        fields = '__all__'


class RewardEarnedSerializer(serializers.ModelSerializer):
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
        amount_paid = validated_data.get('amount_refunded')  # Assuming this is the total paid amount.
        amount_refunded, deduction_percentage = self.calculate_refund(refund_type, amount_paid)

        validated_data['amount_refunded'] = amount_refunded
        validated_data['deduction_percentage'] = deduction_percentage
        validated_data['refund_status'] = 'processed'
        validated_data['refund_process_date'] = serializers.DateField().to_representation(serializers.DateField().to_internal_value('today'))

        return super().create(validated_data)