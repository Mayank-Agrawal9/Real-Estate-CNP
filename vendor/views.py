from django.db.models import Avg, Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, filters, status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from vendor.serializers import *


# Create your views here.

class CategoryListCreateAPIView(generics.ListCreateAPIView):
    queryset = Category.objects.filter(status='active')
    serializer_class = CategorySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']


class CategoryDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.filter(status='active')
    serializer_class = CategorySerializer


class CityByStateAPIView(generics.ListAPIView):
    serializer_class = CitySerializer

    def get_queryset(self):
        state_id = self.kwargs.get('state_id')
        return City.objects.filter(state_id=state_id, status='active')


class VendorListCreateAPIView(generics.ListCreateAPIView):
    queryset = Vendor.objects.filter(status='active')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    filterset_fields = ['offering_type', 'category', 'city', 'is_verified', 'is_featured']
    search_fields = ['business_name', 'owner_name', 'category__name', 'address']
    ordering_fields = ['date_created', 'business_name', 'views_count']
    ordering = ['-is_featured', '-date_created']

    def get_serializer_class(self):
        if self.request.method == "POST":
            return VendorDetailSerializer
        return VendorListSerializer

    def create(self, request, *args, **kwargs):
        if Vendor.objects.filter(user=self.request.user).exists():
            raise ValidationError({"error": "Vendor already exists for this user."})

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Vendor created successfully"}, status=status.HTTP_201_CREATED)


class VendorDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Vendor.objects.filter(status='active').select_related(
        'category', 'city'
    ).prefetch_related('images', 'products', 'ratings', 'certifications', 'awards')
    serializer_class = VendorDetailSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Increment view count
        instance.views_count += 1
        instance.save(update_fields=['views_count'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.status = 'inactive'
        instance.save()
        return Response(
            {'message': 'Vendor deactivated successfully'},
            status=status.HTTP_204_NO_CONTENT
        )


class RequestVendorDetailAPIView(generics.RetrieveAPIView):
    serializer_class = VendorDetailSerializer

    def get_object(self):
        vendor = Vendor.objects.select_related(
            'category', 'city'
        ).prefetch_related(
            'images', 'products', 'ratings', 'certifications', 'awards'
        ).get(user=self.request.user, status='active')
        return vendor


# ===== Vendor Image Views =====
class VendorImageUploadAPIView(generics.CreateAPIView):
    serializer_class = VendorImageSerializer
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        vendor_id = self.kwargs.get('vendor_id')
        serializer.save(vendor_id=vendor_id)


class VendorImageListAPIView(generics.ListAPIView):
    serializer_class = VendorImageSerializer

    def get_queryset(self):
        vendor_id = self.kwargs.get('vendor_id')
        return VendorImage.objects.filter(vendor_id=vendor_id)


class VendorImageDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = VendorImage.objects.all()
    serializer_class = VendorImageSerializer


class VendorProductListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer

    def get_queryset(self):
        vendor_id = self.kwargs.get('vendor_id')
        return Product.objects.filter(vendor_id=vendor_id, is_available=True)

    def perform_create(self, serializer):
        vendor_id = self.kwargs.get('vendor_id')
        serializer.save(vendor_id=vendor_id)


class ProductDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class VendorRatingListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = RatingSerializer

    def get_queryset(self):
        vendor_id = self.kwargs.get('vendor_id')
        return Rating.objects.filter(vendor_id=vendor_id, is_approved=True)

    def perform_create(self, serializer):
        vendor_id = self.kwargs.get('vendor_id')
        serializer.save(vendor_id=vendor_id, created_by=self.request.user, rating_by=self.request.user)


class RatingDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer


class VendorEnquiryCreateAPIView(generics.CreateAPIView):
    serializer_class = EnquirySerializer

    def perform_create(self, serializer):
        vendor_id = self.kwargs.get('vendor_id')
        vendor = Vendor.objects.get(id=vendor_id)
        vendor.enquiry_count += 1
        vendor.save(update_fields=['enquiry_count'])
        serializer.save(vendor_id=vendor_id, enquiry_by=self.request.user)


class EnquiryListAPIView(generics.ListAPIView):
    serializer_class = EnquirySerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'vendor']
    ordering = ['-created_at']

    def get_queryset(self):
        vendor_id = self.request.query_params.get('vendor_id')
        if vendor_id:
            return Enquiry.objects.filter(vendor_id=vendor_id)
        return Enquiry.objects.all()


class EnquiryDetailAPIView(generics.RetrieveUpdateAPIView):
    queryset = Enquiry.objects.filter(status='active')
    serializer_class = EnquirySerializer


class VendorCertificationListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = VendorCertificationSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        vendor_id = self.kwargs.get('vendor_id')
        return VendorCertification.objects.filter(vendor_id=vendor_id)

    def perform_create(self, serializer):
        vendor_id = self.kwargs.get('vendor_id')
        serializer.save(vendor_id=vendor_id)


class VendorAwardListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = VendorAwardSerializer

    def get_queryset(self):
        vendor_id = self.kwargs.get('vendor_id')
        return VendorAward.objects.filter(vendor_id=vendor_id)

    def perform_create(self, serializer):
        vendor_id = self.kwargs.get('vendor_id')
        serializer.save(vendor_id=vendor_id)


class VendorSearchAPIView(APIView):
    def get(self, request):
        query = request.query_params.get('q', '')
        city_id = request.query_params.get('city')
        category_id = request.query_params.get('category')

        vendors = Vendor.objects.filter(status='active')

        if query:
            vendors = vendors.filter(
                Q(business_name__icontains=query) |
                Q(category__name__icontains=query) |
                Q(service_description__icontains=query)
            )

        if city_id:
            vendors = vendors.filter(city_id=city_id)

        if category_id:
            vendors = vendors.filter(category_id=category_id)

        serializer = VendorListSerializer(vendors[:20], many=True, context={'request': request})
        return Response(serializer.data)


class VendorStatsAPIView(APIView):
    def get(self, request):
        total_vendors = Vendor.objects.filter(status='active').count()
        verified_vendors = Vendor.objects.filter(status='active', is_verified=True).count()

        category_stats = Vendor.objects.filter(status='active').values(
            'category__name'
        ).annotate(count=Count('id')).order_by('-count')[:10]

        city_stats = Vendor.objects.filter(status='active').values(
            'city__name'
        ).annotate(count=Count('id')).order_by('-count')[:10]

        top_rated = Vendor.objects.filter(status='active').annotate(
            avg_rating=Avg('ratings__rating'),
            rating_count=Count('ratings')
        ).filter(rating_count__gte=5).order_by('-avg_rating')[:10]

        return Response({
            'total_vendors': total_vendors,
            'verified_vendors': verified_vendors,
            'category_distribution': list(category_stats),
            'city_distribution': list(city_stats),
            'top_rated_vendors': VendorListSerializer(
                top_rated, many=True, context={'request': request}
            ).data
        })