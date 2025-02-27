from django.urls import path
from admin.views import StaffLoginAPIView, VerifyKycAPIView, InvestmentAPIView

urlpatterns = [
    path('login/', StaffLoginAPIView.as_view(), name='login'),
    path('verify-kyc/', VerifyKycAPIView.as_view(), name='kyc-verify'),
    path('investment/', InvestmentAPIView.as_view(), name='verify-investment'),
]