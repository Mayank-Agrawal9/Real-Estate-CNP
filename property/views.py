from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from property.models import Media, Property
from property.serializers import CreatePropertySerializer, PropertySerializer, PropertyListSerializer, MediaSerializer, \
    EditPropertySerializer


# Create your views here.


class PropertyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PropertySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['user', 'country', 'state', 'city', 'postal_code', 'is_sold', 'property_type']
    search_fields = ['title', 'postal_code']

    def get_queryset(self):
        return Property.objects.filter(user=self.request.user, status='active')

    @action(detail=False, methods=['get'], url_path='get-all-property')
    def get_all_property(self, request):
        if not (request.user.profile.is_kyc and request.user.profile.is_kyc_verified):
            return Response(
                {"error": "KYC not completed or verified."},
                status=status.HTTP_403_FORBIDDEN,
            )
        properties = Property.objects.filter(user=request.user, status='active')
        page = self.paginate_queryset(properties)
        if page is not None:
            serializer = PropertyListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = PropertyListSerializer(properties, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='create-property')
    def create_property(self, request):
        if not (request.user.profile.is_kyc or not request.user.profile.is_kyc_verified):
            return Response(
                {"error": "KYC not completed or verified."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = CreatePropertySerializer(data=request.data)
        if serializer.is_valid():
            validated_data = serializer.validated_data

            property_instance = Property.objects.create(
                created_by=request.user,
                user=request.user,
                title=validated_data['title'],
                description=validated_data['description'],
                price=validated_data['price'],
                area_size=validated_data['area_size'],
                area_size_postfix=validated_data['area_size_postfix'],
                property_type=validated_data['property_type'],
                property_status=validated_data['property_status'],
                owner_contact_number=validated_data['owner_contact_number'],
                country=validated_data['country'],
                state=validated_data['state'],
                city=validated_data['city'],
                postal_code=validated_data['postal_code'],
                street_address=validated_data['street_address']
            )

            media_files = validated_data.get('media_files', [])
            media_type = validated_data.get('media_type')
            for file in media_files:
                Media.objects.create(created_by=request.user, property=property_instance, file=file, media_type=media_type)
            return Response({"message": "Property created successfully."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['put'], url_path='edit-property')
    def edit_property(self, request, pk=None):
        try:
            property_instance = Property.objects.get(pk=pk, user=request.user)
        except Exception as e:
            return Response(
                {"error": "Property not found or you do not have permission to edit this property."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = EditPropertySerializer(data=request.data, partial=True)
        if serializer.is_valid():
            validated_data = serializer.validated_data

            for field, value in validated_data.items():
                if field not in ['media_files', 'media_type']:
                    setattr(property_instance, field, value)
            property_instance.save()

            media_files = validated_data.get('media_files', [])
            media_type = validated_data.get('media_type')
            if media_files:
                Media.objects.filter(property=property_instance).delete()
                for file in media_files:
                    Media.objects.create(property=property_instance, file=file, media_type=media_type)

            return Response({"message": "Property updated successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MediaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = MediaSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['property', 'media_type']

    def get_queryset(self):
        return Media.objects.filter(created_by=self.request.user, status='active')