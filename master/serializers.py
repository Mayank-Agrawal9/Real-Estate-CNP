from rest_framework import serializers

from agency.models import RewardEarned
from master.models import *


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = '__all__'


class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = '__all__'


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = '__all__'


class BannerImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = BannerImage
        fields = '__all__'


class GSTSerializer(serializers.ModelSerializer):
    class Meta:
        model = GST
        fields = '__all__'


class RewardMasterSerializer(serializers.ModelSerializer):
    is_buy = serializers.SerializerMethodField()

    class Meta:
        model = RewardMaster
        fields = '__all__'

    def get_is_buy(self, obj):
        user = self.context.get('user')
        if user:
            return RewardEarned.objects.filter(user=user, reward=obj).exists()
        return False


class CompanyBankDetailsMasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyBankDetailsMaster
        fields = '__all__'


class RoyaltyMasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoyaltyMaster
        fields = '__all__'


class CoreGroupIncomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoreGroupIncome
        fields = '__all__'


class CoreGroupPhaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoreGroupPhase
        fields = '__all__'