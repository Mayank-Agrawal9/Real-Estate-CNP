from django.urls import path
from .views import ResendOTPView, VerifyOTPView, RequestOTPView, LogoutView, ProfileView, UserKycAPIView, \
    GetUserFriendReferralCodeDetails, VerifyBankIFSCCodeView

urlpatterns = [
    path('request-otp/', RequestOTPView.as_view(), name='request-otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    path('logout/', LogoutView.as_view()),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('user-kyc/', UserKycAPIView.as_view(), name='user_kyc'),
    path('apply-referral-code/', GetUserFriendReferralCodeDetails.as_view(), name='apply_referral_code'),
    path('verify-bank-ifsc-code/', VerifyBankIFSCCodeView.as_view(), name='verify_bank_ifsc_code'),
]