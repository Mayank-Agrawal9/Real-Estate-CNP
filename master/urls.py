from django.urls import path, include
from rest_framework.routers import DefaultRouter

from master.views import *

router = DefaultRouter()
router.register(r'country', CountryViewSet)
router.register(r'state', StateViewSet)
router.register(r'city', CityViewSet)
router.register(r'banner-image', BannerImageViewSet)
router.register(r'gst', GstViewSet)
router.register(r'rewards', RewardMasterViewSet)

urlpatterns = [
    path('', include(router.urls)),
]