from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (InvestmentViewSet, CommissionViewSet, RefundViewSet, FundWithdrawalViewSet,
                    SuperAgencyViewSet, AgencyViewSet, FieldAgentViewSet, RewardEarnedViewSet,
                    PPDAccountViewSet, InvestmentInterestViewSet, UserFieldAgentAPIView, UserAgencyAPIView,
                    UserSuperAgencyAPIView, EarnedRewardAPIView, RemainingRewardAPIView, IncomeDetailsAPIView,
                    CashfreeWebhookView, BuyPackageView, DistributeSuperAgencyRent, DistributeAgencyRent,
                    AgencyAppCommission, SuperAgencyAppCommission, FieldAgentPackageDetails, AgencyPackageDetails,
                    SuperAgencyPackageDetails)

router = DefaultRouter()
router.register(r'super-agency', SuperAgencyViewSet)
router.register(r'agency', AgencyViewSet)
router.register(r'field-agent', FieldAgentViewSet)
router.register(r'investment', InvestmentViewSet)
router.register(r'commissions', CommissionViewSet)
router.register(r'refunds', RefundViewSet)
router.register(r'ppd-account', PPDAccountViewSet)
router.register(r'fund-withdrawals', FundWithdrawalViewSet)
router.register(r'reward-earned', RewardEarnedViewSet)
router.register(r'monthly-interest', InvestmentInterestViewSet)


urlpatterns = [
    path('', include(router.urls)),
    path('user-super-agency/', UserSuperAgencyAPIView.as_view()),
    path('user-agency/', UserAgencyAPIView.as_view()),
    path('user-field-agent/', UserFieldAgentAPIView.as_view()),
    path('get-earned-reward/', EarnedRewardAPIView.as_view()),
    path('get-pending-reward/', RemainingRewardAPIView.as_view()),
    path('income-details/', IncomeDetailsAPIView.as_view()),
    path('webhook/', CashfreeWebhookView.as_view()),
    path('buy-agency-package/', BuyPackageView.as_view()),
    path('super-agency-rent/', DistributeSuperAgencyRent.as_view()),
    path('agency-rent/', DistributeAgencyRent.as_view()),
    path('super-agency-commission/', SuperAgencyAppCommission.as_view()),
    path('agency-commission/', AgencyAppCommission.as_view()),
    path('super-agency-package-details/', SuperAgencyPackageDetails.as_view()),
    path('agency-package-details/', AgencyPackageDetails.as_view()),
    path('field-agent-package-details/', FieldAgentPackageDetails.as_view()),
]
