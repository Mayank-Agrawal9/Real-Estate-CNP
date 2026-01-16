from django.contrib import admin

# Register your models here.


from .models import (
    Category, Vendor, VendorImage, Product, Rating, Enquiry,
    VendorCertification, VendorAward
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'status')
    search_fields = ('name', 'description')
    list_filter = ('status',)
    raw_id_fields = ('created_by', 'updated_by')


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'owner_name', 'category', 'city', 'status', 'is_verified')
    search_fields = ('business_name', 'owner_name', 'phone', 'email')
    list_filter = ('status', 'is_verified', 'is_featured', 'offering_type', 'city')
    readonly_fields = ('views_count', 'enquiry_count')
    raw_id_fields = ('created_by', 'updated_by', 'user', 'category', 'city')


@admin.register(VendorImage)
class VendorImageAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'image_type', 'is_primary')
    list_filter = ('image_type', 'is_primary')
    raw_id_fields = ('created_by', 'updated_by', 'product')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'vendor', 'price', 'is_available', 'stock_quantity')
    search_fields = ('name', 'vendor__business_name', 'sku')
    list_filter = ('is_available',)
    raw_id_fields = ('created_by', 'updated_by', 'vendor')


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'rating_by', 'rating', 'is_approved', 'date_created')
    list_filter = ('is_approved', 'rating')
    search_fields = ('vendor__business_name', 'rating_by__username')
    raw_id_fields = ('created_by', 'updated_by', 'vendor')


@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ('name', 'vendor', 'phone', 'enquiry_status', 'date_created')
    list_filter = ('enquiry_status',)
    search_fields = ('name', 'phone', 'vendor__business_name')
    raw_id_fields = ('created_by', 'updated_by', 'vendor', 'enquiry_by')


@admin.register(VendorCertification)
class VendorCertificationAdmin(admin.ModelAdmin):
    list_display = ('name', 'vendor', 'issuing_organization', 'issue_date')
    search_fields = ('name', 'vendor__business_name')
    raw_id_fields = ('created_by', 'updated_by', 'vendor')


@admin.register(VendorAward)
class VendorAwardAdmin(admin.ModelAdmin):
    list_display = ('title', 'vendor', 'awarded_by', 'award_date')
    search_fields = ('title', 'vendor__business_name')
    raw_id_fields = ('created_by', 'updated_by', 'vendor')