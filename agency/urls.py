from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (InvestmentViewSet, CommissionViewSet, RefundViewSet, FundWithdrawalViewSet,
                    SuperAgencyViewSet, AgencyViewSet, FieldAgentViewSet, RewardEarnedViewSet,
                    PPDAccountViewSet, InvestmentInterestViewSet)

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
]
