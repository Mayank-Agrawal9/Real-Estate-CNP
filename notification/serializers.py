from rest_framework import serializers

from notification.models import InAppNotification


class GetNotificationSerializer(serializers.ModelSerializer):
    child = serializers.SerializerMethodField()

    class Meta:
        model = InAppNotification
        fields = ['date_created', 'message']