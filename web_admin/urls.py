from django.urls import path, include
from rest_framework.routers import DefaultRouter

from web_admin.views import *

router = DefaultRouter()
router.register(r'manual-fund', ManualFundViewSet)
router.register(r'contact-enquiry', ContactUsEnquiryViewSet)
router.register(r'property-enquiry', PropertyInterestEnquiryViewSet)
router.register(r'company-investment', CompanyInvestmentViewSet)
router.register(r'tds-percentage', TDSPercentageViewSet)


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
    path('withdraw-summary', WithdrawSummaryAPIView.as_view(), name='withdraw-summary'),
    path('action-withdraw-request', ApproveRejectWithDrawAPIView.as_view(), name='action-withdraw-request'),
    path('withdraw-dashboard', WithdrawDashboard.as_view(), name='withdraw-dashboard'),
    path('withdraw-dashboard-v2', WithdrawDashboardV2.as_view(), name='withdraw-dashboard-v2'),
    path('commission-list', CommissionListView.as_view(), name='commission-list'),
    path('working-id', UserWithWorkingIDListView.as_view(), name='working-id'),
    path('app-transfer-detail', AppTransferTransaction.as_view(), name='app-transfer-detail'),
    path('change-request-list', ChangeRequestListAPIView.as_view(), name='change-request-list'),
    path('aggregate-change-request', AggregateChangeRequestAPIView.as_view(), name='aggregate-change-request'),
    path('aggregate-transfer-amount', AppTransferSumAmount.as_view(), name='aggregate-transfer-amount'),
    path('add-beneficiary-account', AppBeneficiaryAPI.as_view(), name='add-beneficiary-account'),
    path('roi-aggregate', ROIAggregateAPIView.as_view(), name='roi-aggregate-view'),
    path('core-group-aggregate', CoreGroupIncomeAggregateAPIView.as_view(), name='core-group-aggregate'),
    path('royalty-earned-aggregate', RoyaltyEarnedAggregateAPIView.as_view(), name='royalty-earned-aggregate'),
    path('commission-aggregate', LevelIncomeEarnedAPIView.as_view(), name='commission-aggregate'),
    path('extra-reward-aggregate', ExtraRewardAggregateAPIView.as_view(), name='extra-reward-aggregate'),
    path('reward-aggregate', RewardAggregateAPIView.as_view(), name='reward-aggregate'),
    path('reward-earned', RewardEarnedAPIView.as_view(), name='reward-earned'),
    path('commission-earned', CommissionEarnedAPIView.as_view(), name='commission-earned'),
    path('get-mlm-user', GetMLMUserAPIView.as_view(), name='mlm-user-list'),
    path('get-user-app-dashboard', GetAppDashboardAggregate.as_view(), name='user-dashboard-count'),
    path('get-earned-royalty', RoyaltyEarnedAPIView.as_view(), name='royalty-earned-view'),
    path('get-earned-extra-reward', ExtraRewardEarnedAPIView.as_view(), name='extra-reward-earned-view'),
    path('roi-list', ROIEarnedListAPIView.as_view(), name='roi-earned-view'),
    path('wallet_list', ActiveUserWalletListView.as_view(), name='user-wallet-list'),
    path('stop-roi/<int:user_id>/', StopSendingROIListView.as_view(), name='stop-sending-roi'),
    path('start-roi/<int:user_id>/', StartSendingROIListView.as_view(), name='start-sending-roi'),
    path('send-extra-reward/', SendExtraRewardAPIView.as_view(), name='send-extra-reward'),
    path('send-reward/', SendRewardAPIView.as_view(), name='send-reward'),
    path('investment/<int:id>/', InvestmentDelete.as_view(), name='investment-delete'),
    path('top-up-list/', GetAllTopUpList.as_view(), name='top-up-list'),
    path('core-income-earned/', CoreIncomeEarnedAPIView.as_view(), name='core-income-earned'),

]