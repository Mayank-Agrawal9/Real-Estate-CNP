from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (InvestmentViewSet, CommissionViewSet, RewardViewSet, RefundViewSet, FundWithdrawalViewSet,
                    SuperAgencyViewSet, AgencyViewSet, FieldAgentViewSet, PPDModelViewSet, RewardEarnedViewSet)

router = DefaultRouter()
router.register(r'super-agency', SuperAgencyViewSet)
router.register(r'agency', AgencyViewSet)
router.register(r'field-agent', FieldAgentViewSet)
router.register(r'investment', InvestmentViewSet)
router.register(r'commissions', CommissionViewSet)
router.register(r'refunds', RefundViewSet)
router.register(r'ppd-model', PPDModelViewSet)
router.register(r'fund-withdrawals', FundWithdrawalViewSet)
router.register(r'rewards', RewardViewSet)
router.register(r'reward-earned', RewardEarnedViewSet)


urlpatterns = [
    path('', include(router.urls)),
]