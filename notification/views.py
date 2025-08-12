from django.shortcuts import render
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from notification.models import InAppNotification
from notification.serializers import GetNotificationSerializer, NotificationSerializer


# Create your views here.


class AppNotificationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['message',]
    filterset_fields = ['date_created', ]

    def get_queryset(self):
        return InAppNotification.objects.filter(user=self.request.user, status='active')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        queryset.filter(is_read=False).update(is_read=True)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = GetNotificationSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = InAppNotification.objects.filter(user=request.user, is_read=False).count()
        return Response({"unread_count": count})