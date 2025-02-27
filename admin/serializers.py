from rest_framework import serializers

from accounts.models import Profile
from agency.models import Investment
from p2pmb.models import Package


class ProfileSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    def get_user(self, obj):
        return {
            'first_name': obj.user.first_name,
            'last_name': obj.user.last_name,
            'email': obj.user.email,
            'username': obj.user.username,
        }

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