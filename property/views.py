from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from property.models import Media, Property, PropertyEnquiry, PropertyBooking, PropertyBookmark, PropertyFeature, \
    NearbyFacility, Feature, PropertyCategory, PropertyType
from property.serializers import CreatePropertySerializer, PropertySerializer, PropertyListSerializer, MediaSerializer, \
    EditPropertySerializer, GetPropertyEnquirySerializer, CreatePropertyEnquirySerializer, GetPropertyBookingSerializer, \
    CreatePropertyBookingSerializer, PropertyBookmarkSerializer, GetPropertyBookmarkSerializer, \
    CreateNearbyFacilitySerializer, GetNearbyFacilitySerializer, GetPropertyFeatureSerializer, \
    CreatePropertyFeatureSerializer, FeatureSerializer, PropertyRetrieveSerializer, PropertyCategorySerializer, \
    PropertyBookmarkListSerializer, PropertyTypeSerializer, FeaturedPropertyListSerializer


# Create your views here.


class PropertyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['user', 'country', 'state', 'city', 'postal_code', 'is_sold', 'property_type']
    search_fields = ['title', 'postal_code']
    serializer_classes = {
        'list': PropertyListSerializer,
        'retrieve': PropertyRetrieveSerializer,
    }
    default_serializer_class = PropertySerializer

    def get_queryset(self):
        return Property.objects.filter(user=self.request.user, status='active').order_by('-id')

    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.default_serializer_class)

    @action(detail=False, methods=['get'], url_path='get-all-property')
    def get_all_property(self, request):
        queryset = Property.objects.filter(status='active').order_by('-id')

        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        country = request.query_params.get('country')
        state = request.query_params.get('state')
        city = request.query_params.get('city')
        category = request.query_params.get('category')
        property_type = request.query_params.get('property_type')
        is_featured = request.query_params.get('is_featured')
        features = request.query_params.getlist('features')

        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        if country:
            queryset = queryset.filter(country_id=country)
        if state:
            queryset = queryset.filter(state_id=state)
        if city:
            queryset = queryset.filter(city_id=city)
        if category:
            queryset = queryset.filter(category_id=category)
        if property_type:
            queryset = queryset.filter(property_type_id=property_type)
        if is_featured in ['true', 'false']:
            queryset = queryset.filter(is_featured=is_featured.lower() == 'true')

        if len(features) > 0:
            queryset = queryset.filter(features__in=features)

        queryset = queryset.distinct().order_by('-id')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = PropertyBookmarkListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = PropertyBookmarkListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='get-featured-property')
    def get_featured_property(self, request):
        queryset = Property.objects.filter(status='active', is_featured=True).order_by('-id')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = FeaturedPropertyListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = FeaturedPropertyListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='retrieve')
    def get_retrieve_property(self, request):
        property_id = request.query_params.get('property_id')
        if not property_id:
            return Response({"error": "property_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        properties = Property.objects.filter(status='active', id=property_id).last()
        if not properties:
            return Response({"error": "Property not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = PropertyRetrieveSerializer(properties)
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
                property_status=validated_data['property_status'],
                owner_contact_number=validated_data['owner_contact_number'],
                country=validated_data['country'],
                state=validated_data['state'],
                city=validated_data['city'],
                postal_code=validated_data['postal_code'],
                street_address=validated_data['street_address'],
                category=validated_data['category'],
                property_type=validated_data['property_type'],
            )

            media_files = validated_data.get('media_files', [])
            media_type = validated_data.get('media_type')
            for file in media_files:
                Media.objects.create(created_by=request.user, property=property_instance, file=file,
                                     media_type=media_type)

            features_data = validated_data.get('features', [])
            for feature in features_data:
                PropertyFeature.objects.create(
                    created_by=request.user,
                    property=property_instance,
                    feature_id=feature['feature'].id,
                    value=feature['value']
                )

            nearby_facilities_data = validated_data.get('nearby_facilities', [])
            if nearby_facilities_data:
                for facility in nearby_facilities_data:
                    NearbyFacility.objects.create(
                        created_by=request.user,
                        property=property_instance,
                        name=facility['name'],
                        distance=facility['distance']
                    )

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


class PropertyEnquiryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['is_response', ]
    serializer_classes = {
        'list': GetPropertyEnquirySerializer,
        'create': CreatePropertyEnquirySerializer,
        'retrieve': GetPropertyEnquirySerializer,
    }
    default_serializer_class = CreatePropertyEnquirySerializer

    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.default_serializer_class)

    def get_queryset(self):
        return PropertyEnquiry.objects.filter(request_by=self.request.user, status='active')


class PropertyBookingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['booked_by', 'customer_name']
    serializer_classes = {
        'list': GetPropertyBookingSerializer,
        'create': CreatePropertyBookingSerializer,
        'retrieve': GetPropertyBookingSerializer,
    }
    default_serializer_class = CreatePropertyBookingSerializer

    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.default_serializer_class)

    def get_queryset(self):
        return PropertyBooking.objects.filter(booked_by=self.request.user, status='active')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class PropertyBookmarkViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['user', 'property']
    serializer_classes = {
        'list': GetPropertyBookmarkSerializer,
        'create': PropertyBookmarkSerializer,
        'retrieve': GetPropertyBookmarkSerializer,
    }
    default_serializer_class = PropertyBookmarkSerializer

    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.default_serializer_class)

    def get_queryset(self):
        return PropertyBookmark.objects.filter(user=self.request.user, status='active')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, user=self.request.user)


class NearbyFacilityViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['created_by__username', 'created_by__first_name']
    serializer_classes = {
        'list': GetNearbyFacilitySerializer,
        'create': CreateNearbyFacilitySerializer,
        'retrieve': GetNearbyFacilitySerializer,
    }
    default_serializer_class = CreateNearbyFacilitySerializer

    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.default_serializer_class)

    def get_queryset(self):
        return NearbyFacility.objects.active()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class PropertyFeatureViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['created_by__username', 'created_by__first_name']
    serializer_classes = {
        'list': GetPropertyFeatureSerializer,
        'create': CreatePropertyFeatureSerializer,
        'retrieve': GetPropertyFeatureSerializer,
    }
    default_serializer_class = CreateNearbyFacilitySerializer
    serializer_class = GetPropertyFeatureSerializer

    def get_queryset(self):
        return PropertyFeature.objects.active()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class FeatureViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    queryset = Feature.objects.active()
    serializer_class = FeatureSerializer
    search_fields = ['name', ]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class PropertyCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    queryset = PropertyCategory.objects.active()
    serializer_class = PropertyCategorySerializer
    search_fields = ['name', ]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class PropertyTypeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    queryset = PropertyType.objects.active()
    serializer_class = PropertyTypeSerializer
    search_fields = ['name', ]
    filterset_fields = ['id', 'name']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)