from django.urls import path, include
from rest_framework.routers import DefaultRouter

from web_admin.views import StaffLoginAPIView, VerifyKycAPIView, InvestmentAPIView, CreateManualInvestmentAPIView, \
    GetUserAPIView, ManualFundViewSet, DeductManualInvestmentAPIView, UpdatePasswordView

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
    path('dashboard-count/', GetUserAPIView.as_view(), name='get-all-user'),
    path('', include(router.urls)),
]