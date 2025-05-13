from django.urls import path, include
from rest_framework.routers import DefaultRouter

from web_admin.views import *

router = DefaultRouter()
router.register(r'manual-fund', ManualFundViewSet)
router.register(r'contact-enquiry', ContactUsEnquiryViewSet)
router.register(r'property-enquiry', PropertyInterestEnquiryViewSet)


urlpatterns = [
    path('', include(router.urls)),
    path('login/', StaffLoginAPIView.as_view(), name='login'),
    path('verify-kyc/', VerifyKycAPIView.as_view(), name='kyc-verify'),
    path('document-verification-update/', ApproveRejectDocumentsAPIView.as_view(), name='document-update'),
    path('update-staff-password/', UpdatePasswordView.as_view(), name='up'),
    path('investment/', InvestmentAPIView.as_view(), name='verify-investment'),
    path('create-manual-investment/', CreateManualInvestmentAPIView.as_view(), name='manual-fund-add'),
    path('deduct-investment/', DeductManualInvestmentAPIView.as_view(), name='manual-fund-add'),
    path('get-user/', GetUserAPIView.as_view(), name='get-all-user'),
    path('get-user-permission/', GetUserWithPermissionAPIView.as_view(), name='user-permission'),
    path('create-user/', CreateUserWithPermissionAPIView.as_view(), name='create-user'),
    path('user-document/', UserDocumentAPIView.as_view(), name='user-document'),
    path('user-bank-detail/', UserBankDetailAPIView.as_view(), name='user-bank-detail'),
    path('user-company-detail/', UserCompanyDetailAPIView.as_view(), name='user-company-detail'),
    path('reject-user-kyc/', RejectKYCStatusAPIView.as_view(), name='reject-user-kyc'),
    path('dashboard-count/', DashboardCountAPIView.as_view(), name='dashboard-count'),
    path('dashboard-manual-fund-count/', ManualFundGraphAPIView.as_view(), name='graph-api'),
    path('fund-distribution-p2pmb/', ManualFundDistributionAPIView.as_view(), name='fund-distribution'),
    path('fund-distribution-agency/', ManualFundDistributionAgencyAPIView.as_view(), name='fund-distribution-agency'),
    path('get-all-property/', GetAllPropertyAPIView.as_view(), name='get-all-property'),
    path('property-detail/<int:id>/', PropertyDetailAPIView.as_view(), name='property-detail'),
    path('user-fund-distribution/<int:id>/', UserWiseFundDistributionAPIView.as_view(), name='user-fund-distribution'),
    path('company-liability', CompanyLiabilityStatsAPIView.as_view(), name='company-liability'),
    path('withdraw-request', WithDrawRequest.as_view(), name='withdraw-request'),
    path('withdraw-dashboard', WithdrawDashboard.as_view(), name='withdraw-dashboard'),
    path('withdraw-dashboard-v2', WithdrawDashboardV2.as_view(), name='withdraw-dashboard-v2'),
    path('commission-list', CommissionListView.as_view(), name='commission-list'),
    path('working-id', UserWithWorkingIDListView.as_view(), name='working-id'),
]