from django.db import transaction
from rest_framework import serializers

from master.serializers import CitySerializer
from vendor.models import *


class CategorySerializer(serializers.ModelSerializer):
    subcategories = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'icon', 'parent', 'subcategories']
        read_only_fields = ['id']

    def get_subcategories(self, obj):
        if obj.subcategories.exists():
            return CategorySerializer(obj.subcategories.filter(status='active'), many=True).data
        return []


class VendorImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorImage
        fields = ['id', 'image', 'image_type', 'caption', 'is_primary', 'date_created']
        read_only_fields = ['id', 'date_created']


class VendorImageViewSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorImage
        fields = '__all__'


class VendorMultipleImageUploadSerializer(serializers.Serializer):
    vendor = serializers.PrimaryKeyRelatedField(queryset=Vendor.objects.filter(status='active'))
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), required=False, allow_null=True)
    images = serializers.ListField(child=serializers.ImageField(), write_only=True)
    image_type = serializers.ChoiceField(choices=IMAGE_TYPE_CHOICES, default='product')
    caption = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def create(self, validated_data):
        images = validated_data.pop('images')
        vendor = validated_data.get('vendor')
        product = validated_data.get('product')
        image_type = validated_data.get('image_type', 'gallery')
        caption = validated_data.get('caption', '')
        is_primary = validated_data.get('is_primary', False)
        
        created_images = []
        for image in images:
            vendor_image = VendorImage.objects.create(
                vendor=vendor,
                product=product,
                image=image,
                image_type=image_type,
                caption=caption,
                is_primary=is_primary
            )
            created_images.append(vendor_image)
        return created_images


class ProductSerializer(serializers.ModelSerializer):
    images = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'discount_price',
            'sku', 'is_available', 'stock_quantity', 'date_created', 'date_updated'
        ]
        read_only_fields = ['id', 'date_created', 'date_updated']

    def get_images(self, obj):
        images = VendorImage.objects.filter(product=obj, image_type='product')
        return VendorImageSerializer(images, many=True).data


class ProductVendorDetailSerializer(serializers.ModelSerializer):
    images = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'discount_price',
            'sku', 'is_available', 'stock_quantity', 'date_created', 'date_updated', 'images'
        ]
        read_only_fields = ['id', 'date_created', 'date_updated']

    def get_images(self, obj):
        images = VendorImage.objects.filter(product=obj, image_type='product')
        return VendorImageSerializer(images, many=True).data


class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = [
            'id', 'vendor', 'rating', 'review',
            'quality_rating', 'service_rating', 'value_rating',
            'is_verified_purchase', 'is_approved', 'date_created'
        ]
        read_only_fields = ['id', 'date_created', 'is_approved']

    def validate(self, data):
        vendor = data.get('vendor')
        rating_by = data.get('rating_by')

        if self.instance is None:
            if Rating.objects.filter(vendor=vendor, rating_by=rating_by).exists():
                raise serializers.ValidationError("You have already rated this vendor.")

        return data


class EnquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = Enquiry
        fields = [
            'id', 'vendor', 'name', 'phone', 'message',
            'preferred_contact_time', 'budget', 'status',
            'vendor_response', 'responded_at', 'date_created'
        ]
        read_only_fields = ['id', 'date_created', 'status', 'vendor_response', 'responded_at']


class VendorCertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorCertification
        fields = ['id', 'name', 'issuing_organization', 'issue_date', 'expiry_date', 'certificate_image']
        read_only_fields = ['id']


class VendorAwardSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorAward
        fields = ['id', 'title', 'description', 'awarded_by', 'award_date']
        read_only_fields = ['id']


class VendorListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)
    state_name = serializers.CharField(source='city.state.name', read_only=True)
    average_rating = serializers.SerializerMethodField()
    total_ratings = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Vendor
        fields = [
            'id', 'business_name', 'category_name', 'city_name', 'state_name',
            'phone', 'offering_type', 'average_rating', 'total_ratings',
            'is_verified', 'is_featured', 'primary_image', 'date_created', 'opening_time',
            'closing_time', 'working_days'
        ]

    def get_average_rating(self, obj):
        return round(obj.average_rating(), 1)

    def get_total_ratings(self, obj):
        return obj.total_ratings()

    def get_primary_image(self, obj):
        image = obj.images.filter(image_type="logo").first()
        if image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(image.image.url)
        return None


class ProductCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'name', 'description', 'price', 'discount_price',
            'sku', 'is_available', 'stock_quantity'
        ]


class VendorDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.filter(status='active'),
        source='category',
        write_only=True
    )

    city = CitySerializer(read_only=True)
    city_id = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.filter(status='active'),
        source='city',
        write_only=True
    )

    images = serializers.SerializerMethodField()
    products = ProductVendorDetailSerializer(many=True, read_only=True)

    # WRITE (for creation)
    products_data = ProductCreateSerializer(many=True, write_only=True, required=False)

    ratings = RatingSerializer(many=True, read_only=True)
    certifications = VendorCertificationSerializer(many=True, read_only=True)
    awards = VendorAwardSerializer(many=True, read_only=True)

    average_rating = serializers.SerializerMethodField()
    total_ratings = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()

    class Meta:
        model = Vendor
        fields = '__all__'
        read_only_fields = [
            'id', 'views_count', 'enquiry_count',
            'date_created', 'date_updated', 'user'
        ]

    def get_average_rating(self, obj):
        return round(obj.average_rating(), 1)

    def get_total_ratings(self, obj):
        return obj.total_ratings()

    def get_user(self, obj):
        return {
            'id': obj.user.id,
            'name': obj.user.get_full_name(),
            'email': obj.user.username,
        }

    def get_images(self, obj):
        images = VendorImage.objects.filter(vendor=obj, product__isnull=True)
        return VendorImageSerializer(images, many=True).data

    def validate(self, data):
        offering_type = data.get('offering_type')
        service_description = data.get('service_description')

        products_sent = bool(self.initial_data.get('products_data'))

        # SERVICE VALIDATION
        if offering_type in ['service', 'both'] and not service_description:
            raise serializers.ValidationError({
                'service_description': 'Service description is required for service vendors.'
            })

        # PRODUCT VALIDATION
        if offering_type in ['product', 'both'] and not products_sent:
            raise serializers.ValidationError({
                'products_data': 'At least one products is required for product vendors.'
            })

        return data

    @transaction.atomic
    def create(self, validated_data):
        products_data = validated_data.pop('products_data', [])
        request = self.context.get('request')
        user = request.user

        vendor = Vendor.objects.create(**validated_data, user=user, created_by=user)
        for product in products_data:
            Product.objects.create(vendor=vendor, created_by=user, **product)

        return vendor
