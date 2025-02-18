from django.urls import path, include
from rest_framework.routers import DefaultRouter

from p2pmb.views import MLMTreeCreateView, MLMTreeView, PackageViewSet, DistributeLevelIncome, LiveTimeRewardIncome, \
    RoyaltyIncome

router = DefaultRouter()
router.register(r'package', PackageViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('create/', MLMTreeCreateView.as_view()),
    path('get/', MLMTreeView.as_view()),
    path('distribute-level-income/', DistributeLevelIncome.as_view()),
    path('life-time-reward/', LiveTimeRewardIncome.as_view()),
    path('royalty-income/', RoyaltyIncome.as_view()),
]