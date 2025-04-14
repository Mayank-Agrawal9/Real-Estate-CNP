from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from accounts.admin import CustomModelAdminMixin
from property.models import Property, Media, PropertyEnquiry, PropertyBooking, PropertyBookmark, PropertyFeature, \
    NearbyFacility, PropertyReview, Feature, PropertyCategory, PropertyType
from property.resources import PropertyResource, MediaResource, PropertyEnquiryResource, BookingResource, \
    PropertyBookmarkResource, PropertyFeatureResource, NearbyFacilityResource, PropertyReviewResource, FeatureResource, \
    PropertyCategoryResource, PropertyTypeResource


# Register your models here.

@admin.register(Property)
class PropertyAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = PropertyResource
    search_fields = ['user__username', 'user__email']
    raw_id_fields = ('created_by', 'updated_by', 'user')
    list_filter = ('status', )


@admin.register(Media)
class MediaAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = MediaResource
    raw_id_fields = ('created_by', 'updated_by', 'property')
    list_filter = ('status', )


@admin.register(PropertyEnquiry)
class PropertyEnquiryAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = PropertyEnquiryResource
    raw_id_fields = ('created_by', 'updated_by', 'property_id', 'request_by')
    list_filter = ('status', )


@admin.register(PropertyBooking)
class BookingAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = BookingResource
    raw_id_fields = ('created_by', 'updated_by', 'booked_by', 'property_id')
    list_filter = ('status', )


@admin.register(PropertyBookmark)
class BookingAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = PropertyBookmarkResource
    raw_id_fields = ('created_by', 'updated_by', 'user', 'property')
    list_filter = ('status', )


@admin.register(PropertyFeature)
class PropertyFeatureAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = PropertyFeatureResource
    raw_id_fields = ('created_by', 'updated_by', 'feature', 'property')
    list_filter = ('status', )


@admin.register(PropertyCategory)
class PropertyCategoryAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = PropertyCategoryResource
    raw_id_fields = ('created_by', 'updated_by')
    list_filter = ('status', )


@admin.register(NearbyFacility)
class NearbyFacilityAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = NearbyFacilityResource
    raw_id_fields = ('created_by', 'updated_by', 'property')
    list_filter = ('status', )


@admin.register(PropertyReview)
class PropertyReviewAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = PropertyReviewResource
    raw_id_fields = ('created_by', 'updated_by', 'user', 'property')
    list_filter = ('status', )


@admin.register(Feature)
class FeatureAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = FeatureResource
    raw_id_fields = ('created_by', 'updated_by')
    list_filter = ('status', )


@admin.register(PropertyType)
class PropertyTypeAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = PropertyTypeResource
    raw_id_fields = ('created_by', 'updated_by')
    list_filter = ('status', )