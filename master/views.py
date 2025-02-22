from collections import defaultdict

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

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
    filterset_fields = ['page_name', 'carousel_type']
    search_fields = ['page_name', ]

    def list(self, request, *args, **kwargs):
        carousel_type = request.query_params.get('carousel_type', None)
        page_name = request.query_params.get('page_name', None)

        if not page_name:
            return Response({'error': 'page_name is required'}, status=status.HTTP_400_BAD_REQUEST)

        if carousel_type:
            carousel_images = BannerImage.objects.filter(status='active', is_carousel=True, carousel_type=carousel_type)
            serializer = self.get_serializer(carousel_images, many=True)
            return Response({carousel_type: serializer.data})

        all_images = BannerImage.objects.filter(status='active')
        grouped_images = defaultdict(list)
        for image in all_images:
            grouped_images[image.carousel_type].append(image)
        response_data = {}
        for carousel_type, images in grouped_images.items():
            serializer = self.get_serializer(images, many=True)
            response_data[carousel_type] = serializer.data
        return Response(response_data)


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


class CompanyBankDetailsMasterViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = CompanyBankDetailsMaster.objects.filter(status='active')
    serializer_class = CompanyBankDetailsMasterSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['is_applicable_for_super_agency', 'is_applicable_for_agency',
                        'is_applicable_for_field_agent', 'is_applicable_for_p2pmb']


class RoyaltyMasterViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = RoyaltyMaster.objects.filter(status='active')
    serializer_class = RoyaltyMasterSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['club_type',]