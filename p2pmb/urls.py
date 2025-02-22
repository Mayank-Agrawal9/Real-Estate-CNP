from django.urls import path, include
from rest_framework.routers import DefaultRouter

from p2pmb.views import MLMTreeCreateView, MLMTreeView, PackageViewSet, LifeTimeRewardIncomeAPIView, \
    RoyaltyIncome, DistributeDirectIncome, DistributeLevelIncomeAPIView

router = DefaultRouter()
router.register(r'package', PackageViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('create/', MLMTreeCreateView.as_view()),
    path('get/', MLMTreeView.as_view()),
    path('direct-income/', DistributeDirectIncome.as_view()),
    path('distribute-level-income/', DistributeLevelIncomeAPIView.as_view()),
    path('life-time-reward/', LifeTimeRewardIncomeAPIView.as_view()),
    path('royalty-income/', RoyaltyIncome.as_view()),
]