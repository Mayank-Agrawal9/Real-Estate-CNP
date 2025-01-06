from rest_framework import serializers
from .models import User, Investment, Commission, Reward, RefundPolicy, FundWithdrawal, PPDModel, SuperAgency, Agency, \
    FieldAgent, RewardEarned


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
        model = PPDModel
        fields = '__all__'


class RewardEarnedSerializer(serializers.ModelSerializer):
    class Meta:
        model = RewardEarned
        fields = '__all__'
