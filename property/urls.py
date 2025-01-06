from django.urls import path, include
from rest_framework.routers import DefaultRouter

from property.views import PropertyViewSet, MediaViewSet

router = DefaultRouter()
router.register(r'property', PropertyViewSet, basename='property')
router.register(r'media', MediaViewSet, basename='media')

urlpatterns = [
    path('', include(router.urls))
]