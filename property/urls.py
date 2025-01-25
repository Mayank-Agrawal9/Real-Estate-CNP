from django.urls import path, include
from rest_framework.routers import DefaultRouter

from property.views import PropertyViewSet, MediaViewSet, PropertyEnquiryViewSet, PropertyBookingViewSet

router = DefaultRouter()
router.register(r'property', PropertyViewSet, basename='property')
router.register(r'media', MediaViewSet, basename='media')
router.register(r'enquiry', PropertyEnquiryViewSet, basename='property_enquire')
router.register(r'property-booking', PropertyBookingViewSet, basename='property_booking')

urlpatterns = [
    path('', include(router.urls))
]