from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from master.serializers import *


# Create your views here.

class CountryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['name', 'code']
    search_fields = ['name', 'code']


class StateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = State.objects.all()
    serializer_class = StateSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['name', 'country']
    search_fields = ['name', 'country']


class CityViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = City.objects.all()
    serializer_class = CitySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['name', 'state']
    search_fields = ['name', 'state']


class BannerImageViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = BannerImage.objects.filter(status='active')
    serializer_class = BannerImageSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['page_name',]
    search_fields = ['page_name',]


class GstViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = GST.objects.filter(status='active')
    serializer_class = GSTSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['method',]
    search_fields = ['method',]


class RewardMasterViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = RewardMaster.objects.filter(status='active')
    serializer_class = RewardMasterSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['applicable_for',]
    search_fields = ['name', ]

    def get_queryset(self):
        return RewardMaster.objects.filter(applicable_for=self.request.user.profile.role, status='active')