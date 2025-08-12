from django.urls import path, include
from rest_framework.routers import DefaultRouter

from payment_app.views import *

router = DefaultRouter()
router.register(r'user-wallet', UserWalletViewSet, basename='user_wallet')
router.register(r'transaction', TransactionViewSet, basename='transaction')

urlpatterns = [
    path('', include(router.urls)),
    path('approve-transaction', ApproveTransactionView.as_view()),
    path('tds-list/', ListTDSAmountListView.as_view()),
    path('tds-submit/', TDSSubmissionAPIView.as_view()),
    path('tds-submitted-log/', TDSSubmissionLogListAPIView.as_view()),
]