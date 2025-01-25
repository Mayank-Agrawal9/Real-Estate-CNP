from django.urls import path, include
from rest_framework.routers import DefaultRouter

from p2pmb.views import MLMTreeCreateView, MLMTreeView, PackageViewSet

router = DefaultRouter()
router.register(r'package', PackageViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('create/', MLMTreeCreateView.as_view()),
    path('get/', MLMTreeView.as_view()),
]