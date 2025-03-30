from django.urls import path, include
from rest_framework.routers import DefaultRouter

from web_admin.views import StaffLoginAPIView, VerifyKycAPIView, InvestmentAPIView, CreateManualInvestmentAPIView, \
    GetUserAPIView, ManualFundViewSet, DeductManualInvestmentAPIView, UpdatePasswordView, DashboardCountAPIView, \
    ManualFundGraphAPIView, ManualFundDistributionAPIView

router = DefaultRouter()
router.register(r'manual-fund', ManualFundViewSet)


urlpatterns = [
    path('login/', StaffLoginAPIView.as_view(), name='login'),
    path('verify-kyc/', VerifyKycAPIView.as_view(), name='kyc-verify'),
    path('update-staff-password/', UpdatePasswordView.as_view(), name='up'),
    path('investment/', InvestmentAPIView.as_view(), name='verify-investment'),
    path('create-manual-investment/', CreateManualInvestmentAPIView.as_view(), name='manual-fund-add'),
    path('deduct-investment/', DeductManualInvestmentAPIView.as_view(), name='manual-fund-add'),
    path('get-user/', GetUserAPIView.as_view(), name='get-all-user'),
    path('dashboard-count/', DashboardCountAPIView.as_view(), name='dashboard-count'),
    path('dashboard-manual-fund-count/', ManualFundGraphAPIView.as_view(), name='graph-api'),
    path('fund-distribution/', ManualFundDistributionAPIView.as_view(), name='fund-distribution'),
    path('', include(router.urls)),
]