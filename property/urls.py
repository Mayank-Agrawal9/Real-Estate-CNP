from django.urls import path, include
from rest_framework.routers import DefaultRouter

from property.views import PropertyViewSet, MediaViewSet, PropertyEnquiryViewSet, PropertyBookingViewSet, \
    PropertyBookmarkViewSet, NearbyFacilityViewSet, PropertyFeatureViewSet, FeatureViewSet, PropertyCategoryViewSet, \
    PropertyTypeViewSet

router = DefaultRouter()
router.register(r'property', PropertyViewSet, basename='property')
router.register(r'media', MediaViewSet, basename='media')
router.register(r'enquiry', PropertyEnquiryViewSet, basename='property_enquire')
router.register(r'property-booking', PropertyBookingViewSet, basename='property_booking')
router.register(r'property-bookmark', PropertyBookmarkViewSet, basename='property_bookmark')
router.register(r'nearby-facility', NearbyFacilityViewSet, basename='property_nearby_facility')
router.register(r'property-feature', PropertyFeatureViewSet, basename='property_features')
router.register(r'feature', FeatureViewSet, basename='features')
router.register(r'property-category', PropertyCategoryViewSet, basename='property-category')
router.register(r'property-type', PropertyTypeViewSet, basename='property-type')

urlpatterns = [
    path('', include(router.urls))
]