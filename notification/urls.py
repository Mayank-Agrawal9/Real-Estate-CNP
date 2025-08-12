from django.urls import path, include
from rest_framework.routers import DefaultRouter

from notification.views import AppNotificationViewSet

router = DefaultRouter()
router.register(r'app-notification', AppNotificationViewSet, basename='app-notification')


urlpatterns = [
    path('', include(router.urls)),

]