from django.urls import path, include
from rest_framework.routers import DefaultRouter

from p2pmb.views import MLMTreeCreateView, MLMTreeView, PackageViewSet, LifeTimeRewardIncomeAPIView, \
    RoyaltyIncome, DistributeDirectIncome, DistributeLevelIncomeAPIView, CommissionViewSet, PackageBuyView, \
    GetUserDetailsView, GetParentLevelsView, MyApplying, MLMTreeViewV2, CommissionMessageAPIView

router = DefaultRouter()
router.register(r'package', PackageViewSet)
router.register(r'commission', CommissionViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('create/', MLMTreeCreateView.as_view()),
    path('get/', MLMTreeView.as_view()),
    path('get-v2/', MLMTreeViewV2.as_view()),
    path('get-level/', GetParentLevelsView.as_view()),
    path('package-status/', PackageBuyView.as_view()),
    path('user-detail/', GetUserDetailsView.as_view()),
    path('my-applying/', MyApplying.as_view()),
    path('direct-income/', DistributeDirectIncome.as_view()),
    path('distribute-level-income/', DistributeLevelIncomeAPIView.as_view()),
    path('commission-message/', CommissionMessageAPIView.as_view()),
    path('life-time-reward/', LifeTimeRewardIncomeAPIView.as_view()),
    path('royalty-income/', RoyaltyIncome.as_view()),
]