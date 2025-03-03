from rest_framework import serializers

from accounts.models import Profile
from agency.models import Investment
from p2pmb.models import Package
from web_admin.models import ManualFund


class ProfileSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()

    def get_user(self, obj):
        return {
            'id': obj.user.id,
            'first_name': obj.user.first_name,
            'last_name': obj.user.last_name,
            'email': obj.user.email,
            'username': obj.user.username,
        }

    def get_city(self, obj):
        return obj.city.name if obj.city else None

    def get_state(self, obj):
        return obj.state.name if obj.state else None

    class Meta:
        model = Profile
        fields = '__all__'


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


