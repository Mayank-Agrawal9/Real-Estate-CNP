from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ResendOTPView, VerifyOTPView, RequestOTPView, LogoutView, ProfileView, UserKycAPIView, \
    GetUserFriendReferralCodeDetails, VerifyBankIFSCCodeView, VerifyAndUpdateProfile, FAQAPIView, SoftwarePolicyAPIView, \
    DeleteUser, GetReferralCode, ChangeRequestViewSet, GetPPDReferralCode, ShowUserDetail, UpdateUserBasicDetailAPIView, \
    UserBankDetailsViewSet, UserPersonalDocumentViewSet, GenerateUniqueNumber, GeneratePreviousUniqueCode, LoginAPIView, \
    VerifyOptAPI, OptResendAPIView, ForgotPasswordChangeAPI

router = DefaultRouter()
router.register(r'change-request', ChangeRequestViewSet)
router.register(r'bank-detail', UserBankDetailsViewSet)
router.register(r'personal-document', UserPersonalDocumentViewSet)


urlpatterns = [
    path('', include(router.urls)),
    path('request-otp/', RequestOTPView.as_view(), name='request-otp'),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('verify-opt/', VerifyOptAPI.as_view(), name='verify_otp'),
    path('resend-opt/', OptResendAPIView.as_view(), name='resent_otp'),
    path('update-forgot-password/', ForgotPasswordChangeAPI.as_view(), name='forgot_password'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    path('logout/', LogoutView.as_view()),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('user-kyc/', UserKycAPIView.as_view(), name='user_kyc'),
    path('basic-detail/', UpdateUserBasicDetailAPIView.as_view(), name='user_basic_detail_kyc'),
    path('verify-kyc/', VerifyAndUpdateProfile.as_view(), name='verify_kyc'),
    path('apply-referral-code/', GetUserFriendReferralCodeDetails.as_view(), name='apply_referral_code'),
    path('get-referral-code/', GetReferralCode.as_view(), name='get_referral_code'),
    path('get-ppd-referral-code/', GetPPDReferralCode.as_view(), name='get_p2pmb_code'),
    path('show-detail/', ShowUserDetail.as_view(), name='show_user_detail'),
    path('verify-bank-ifsc-code/', VerifyBankIFSCCodeView.as_view(), name='verify_bank_ifsc_code'),
    path('software-policy/', SoftwarePolicyAPIView.as_view(), name='software-policy'),
    path('faqs/', FAQAPIView.as_view(), name='faqs'),
    path('deactivate-user/', DeleteUser.as_view(), name='delete-user'),
    path('generate-unique-number/', GenerateUniqueNumber.as_view(), name='unique-code'),
    path('generate-previous-unique-number/', GeneratePreviousUniqueCode.as_view(), name='previous-unique-code'),
]