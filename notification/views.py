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

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
        else:
            serializer = GetNotificationSerializer(queryset, many=True)
            response = Response(serializer.data)

        def mark_as_read_callback(response):
            queryset.filter(is_read=False).update(is_read=True)

        response.add_post_render_callback(mark_as_read_callback)
        return response

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = InAppNotification.objects.filter(user=request.user, is_read=False).count()
        return Response({"unread_count": count})