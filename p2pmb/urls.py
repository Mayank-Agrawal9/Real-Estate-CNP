from django.urls import path, include
from rest_framework.routers import DefaultRouter

from p2pmb.views import MLMTreeCreateView, MLMTreeView, PackageViewSet, LifeTimeRewardIncomeAPIView, \
    RoyaltyIncome, DistributeDirectIncome, DistributeLevelIncomeAPIView, CommissionViewSet, PackageBuyView, \
    GetUserDetailsView, GetParentLevelsView, MyApplying, MLMTreeViewV2, CommissionMessageAPIView, \
    SendMonthlyInterestIncome, GetParentLevelCountView, ExtraRewardViewSet, CoreIncomeEarnedViewSet, \
    P2PMBRoyaltyMasterViewSet, RoyaltyEarnedViewSet, GetAllPayout, MonthlyDistributeDirectIncome, MyIdValueAPIView, \
    GetTopUpInvestment, GetUserDirectTeamAPIView, GetTDSAmountAPIView, DiIncomeAPIView, GetAppDashboardAggregate, \
    GetUserRoyaltyClubStatusAPIView

router = DefaultRouter()
router.register(r'package', PackageViewSet)
router.register(r'commission', CommissionViewSet)
router.register(r'extra-reward', ExtraRewardViewSet)
router.register(r'core-income-earned', CoreIncomeEarnedViewSet)
router.register(r'royalty-master', P2PMBRoyaltyMasterViewSet)
router.register(r'royalty-earned', RoyaltyEarnedViewSet, basename='royalty-earned')

urlpatterns = [
    path('', include(router.urls)),
    path('create/', MLMTreeCreateView.as_view()),
    path('get/', MLMTreeView.as_view()),
    path('get-v2/', MLMTreeViewV2.as_view()),
    path('get-direct-user/', GetUserDirectTeamAPIView.as_view()),
    path('get-level/', GetParentLevelsView.as_view()),
    path('get-level-count/', GetParentLevelCountView.as_view()),
    path('package-status/', PackageBuyView.as_view()),
    path('user-detail/', GetUserDetailsView.as_view()),
    path('my-applying/', MyApplying.as_view()),
    path('direct-income/', DistributeDirectIncome.as_view()),
    path('monthly-direct-income/', MonthlyDistributeDirectIncome.as_view()),
    path('distribute-level-income/', DistributeLevelIncomeAPIView.as_view()),
    path('commission-message/', CommissionMessageAPIView.as_view()),
    path('life-time-reward/', LifeTimeRewardIncomeAPIView.as_view()),
    path('royalty-income/', RoyaltyIncome.as_view()),
    path('monthly-interest/', SendMonthlyInterestIncome.as_view()),
    path('get-payout/', GetAllPayout.as_view()),
    path('my-top-up/', GetTopUpInvestment.as_view()),
    path('my-id-value/', MyIdValueAPIView.as_view()),
    path('get-tds-amount/', GetTDSAmountAPIView.as_view()),
    path('dashboard-aggregate/', GetAppDashboardAggregate.as_view()),
    path('royalty-club-status/', GetUserRoyaltyClubStatusAPIView.as_view()),
    path('di/', DiIncomeAPIView.as_view()),
]