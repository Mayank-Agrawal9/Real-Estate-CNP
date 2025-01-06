from rest_framework import serializers

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