from rest_framework import serializers

from master.models import Country, State, City
from property.choices import MEDIA_TYPE_CHOICES, PROPERTY_TYPE, PROPERTY_STATUS
from property.models import Property, Media


class CreatePropertySerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    area_size = serializers.FloatField()
    area_size_postfix = serializers.CharField(max_length=50, allow_blank=True, required=False)
    property_type = serializers.ChoiceField(PROPERTY_TYPE)
    property_status = serializers.CharField(max_length=100)
    owner_contact_number = serializers.CharField(max_length=15)
    country = serializers.PrimaryKeyRelatedField(queryset=Country.objects.all())
    state = serializers.PrimaryKeyRelatedField(queryset=State.objects.all())
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all())
    postal_code = serializers.CharField(max_length=20)
    street_address = serializers.CharField()
    media_files = serializers.ListField(
        child=serializers.FileField(),
        required=False
    )
    media_type = serializers.ChoiceField(choices=['photo', 'video'], required=False)

    def validate(self, data):
        """
        Custom validation logic.
        """
        media_files = data.get('media_files', [])
        media_type = data.get('media_type', '')

        if media_files and not media_type:
            raise serializers.ValidationError("You must specify a media type when uploading files.")

        return data


class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = '__all__'


class MediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Media
        fields = '__all__'


class PropertyListSerializer(serializers.ModelSerializer):
    media = MediaSerializer(many=True, read_only=True, source='media_set')

    class Meta:
        model = Property
        fields = '__all__'


class EditPropertySerializer(serializers.Serializer):
    title = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    area_size = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    area_size_postfix = serializers.CharField(required=False)
    property_type = serializers.ChoiceField(choices=PROPERTY_TYPE, required=False)
    property_status = serializers.ChoiceField(choices=PROPERTY_STATUS, required=False)
    user_property_id = serializers.CharField(required=False)
    owner_contact_number = serializers.CharField(required=False)
    country = serializers.CharField(required=False)
    state = serializers.CharField(required=False)
    city = serializers.CharField(required=False)
    postal_code = serializers.CharField(required=False)
    street_address = serializers.CharField(required=False)
    video_url = serializers.URLField(required=False)
    country_code = serializers.CharField(required=False)
    media_files = serializers.ListField(
        child=serializers.FileField(), required=False
    )
    media_type = serializers.ChoiceField(choices=MEDIA_TYPE_CHOICES, required=False)
