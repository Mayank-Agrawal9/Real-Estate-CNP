import datetime
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from payment_app.models import UserWallet, Transaction
from .calculation import distribute_monthly_rent_for_super_agency, calculate_super_agency_rewards, \
    calculate_agency_rewards, calculate_field_agent_rewards, process_monthly_rentals_for_ppd_interest
from .models import Investment, Commission, RefundPolicy, FundWithdrawal, SuperAgency, Agency, FieldAgent, \
    RewardEarned, PPDAccount
from .serializers import (InvestmentSerializer, CommissionSerializer,
                          RefundPolicySerializer, FundWithdrawalSerializer, SuperAgencySerializer, AgencySerializer,
                          FieldAgentSerializer, PPDModelSerializer, RewardEarnedSerializer, CreateInvestmentSerializer,
                          GetAllEarnedReward)


class SuperAgencyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = SuperAgency.objects.all()
    serializer_class = SuperAgencySerializer

    def get_queryset(self):
        return SuperAgency.objects.filter(profile=self.request.user.profile, status='active')


class AgencyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Agency.objects.all()
    serializer_class = AgencySerializer

    def get_queryset(self):
        return Agency.objects.filter(created_by=self.request.user, status='active')


class FieldAgentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = FieldAgent.objects.all()
    serializer_class = FieldAgentSerializer

    def get_queryset(self):
        return FieldAgent.objects.filter(profile=self.request.user.profile, status='active')


class InvestmentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Investment.objects.filter(status='active')
    serializer_class = InvestmentSerializer

    def get_queryset(self):
        return Investment.objects.filter(user=self.request.user, status='active')

    @action(detail=False, methods=['post'], url_path='create-investment')
    def create_investment(self, request):
        serializer = CreateInvestmentSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Request for payment deposit sent successfully."}, status=status.HTTP_200_OK)


class CommissionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Commission.objects.all()
    serializer_class = CommissionSerializer

    def get_queryset(self):
        return Commission.objects.filter(commission_to=self.request.user, status='active')


class RefundViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = RefundPolicy.objects.all()
    serializer_class = RefundPolicySerializer

    def get_queryset(self):
        return RefundPolicy.objects.filter(user=self.request.user, status='active')

    @action(detail=False, methods=['post'], url_path='create-refund-request')
    def create_refund_request(self, request):
        investment_id = request.data.get('investment_id')
        investment = Investment.objects.filter(id=investment_id, user=request.user).last()
        if not investment:
            return Response(
                {"error": "Investment not found or you are not authorized to access it."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        refund_initiate_date = investment.date_created.date()
        current_date = datetime.datetime.today().date()
        delta = relativedelta(current_date, refund_initiate_date)
        months_passed = delta.years * 12 + delta.months

        if months_passed <= 1:
            deduction_percentage = 50
            refund_type = "within_1_month"
        elif months_passed <= 3:
            deduction_percentage = 60
            refund_type = "within_3_months"
        elif months_passed <= 6:
            deduction_percentage = 75
            refund_type = "within_6_months"
        elif months_passed <= 12:
            deduction_percentage = 90
            refund_type = "within_1_year"
        else:
            deduction_percentage = 100
            refund_type = "no_refund"

        amount_paid = investment.amount
        refund_amount = float(amount_paid) * (100 - deduction_percentage) / 100

        refund_policy = RefundPolicy.objects.create(
            user=request.user,
            refund_type=refund_type,
            refund_status="pending",
            deduction_percentage=deduction_percentage,
            amount_refunded=refund_amount,
        )

        response_serializer = RefundPolicySerializer(refund_policy)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='approve-refund-request')
    def approve_refund_request(self, request):
        refund_id = request.data.get('refund_id')
        refund_status = request.data.get('refund_status')
        refund = RefundPolicy.objects.filter(id=refund_id).last()
        if not refund:
            return Response(
                {"error": "Refund request not found or you are not authorized to access it."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if refund.refund_status in ["approved", "rejected"]:
            return Response(
                {"error": f"This refund request is already {refund}."}, status=status.HTTP_400_BAD_REQUEST,
            )

        refund.refund_status = refund_status
        refund.refund_process_date = datetime.datetime.today()
        refund.refund_process_by = self.request.user
        refund.save()

        Transaction.objects.create(
            created_by=request.user,
            sender=request.user,
            receiver=refund.user,
            amount=refund.amount_refunded,
            transaction_type='refund',
            transaction_status='approved',
            verified_by=self.request.user,
            verified_on=datetime.datetime.today(),
            payment_method='wallet'
        )

        user_wallet = UserWallet.objects.filter(user=refund.user).last()
        user_wallet.app_wallet_balance += refund.amount_refunded
        user_wallet.save()
        response_serializer = RefundPolicySerializer(refund)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class PPDAccountViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = PPDAccount.objects.all()
    serializer_class = PPDModelSerializer

    def get_queryset(self):
        return PPDAccount.objects.filter(user=self.request.user, status='active')

    @action(detail=False, methods=['post'], url_path='create-account')
    def create_ppd_account(self, request):
        deposit_amount = Decimal(request.data.get('deposit_amount'))
        remarks = request.data.get('remarks')
        if not (request.user.profile.is_kyc and request.user.profile.is_kyc_verified):
            return Response(
                {"error": "You has not completed you KYC verification."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if deposit_amount < 100 or deposit_amount > 4999:
            return Response({"error": "Deposit amount must be between ₹100 and ₹4999."},
                            status=status.HTTP_400_BAD_REQUEST)
        sender_wallet = UserWallet.objects.filter(user=request.user).last()
        if not sender_wallet:
            return Response({"error": "Please create your wallet first."},
                            status=status.HTTP_400_BAD_REQUEST)
        if sender_wallet.app_wallet_balance < deposit_amount:
            return Response({"error": "Insufficient balance in your wallet."}, status=status.HTTP_400_BAD_REQUEST)

        sender_wallet.app_wallet_balance -= deposit_amount
        sender_wallet.save()

        Transaction.objects.create(
            created_by=request.user,
            sender=request.user,
            amount=deposit_amount,
            transaction_status='approved',
            transaction_type='investment',
            status='active'
        )

        ppd_account = PPDAccount.objects.create(created_by=request.user, user=request.user,
                                                deposit_amount=deposit_amount,
                                                deposit_date=datetime.datetime.now().date(), remarks=remarks)
        return Response({"message": "PPD account created successfully.", "account_id": ppd_account.id},
                        status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='withdraw-ppd-amount/(?P<account_id>\d+)')
    def withdraw_ppd_amount(self, request, account_id):
        try:
            ppd_account = PPDAccount.objects.get(id=account_id, user=request.user, is_active=True)
            withdrawal_amount = ppd_account.calculate_withdrawal_amount()
            ppd_account.withdrawal_date = datetime.datetime.now().date()
            ppd_account.withdrawal_amount = withdrawal_amount
            ppd_account.is_active = False
            ppd_account.save()

            Transaction.objects.create(
                created_by=request.user,
                sender=request.user,
                amount=withdrawal_amount,
                transaction_status='approved',
                transaction_type='withdraw',
                status='active',
                payment_method='wallet',
                verified_on=datetime.datetime.today()
            )

            return Response({
                "message": "Withdrawal successful.",
                "withdrawal_amount": withdrawal_amount,
                "deduction_percentage": ppd_account.calculate_deduction() * 100,
                "deduction_amount": ppd_account.deposit_amount * ((ppd_account.calculate_deduction() * 100) / 100),
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": "PPD account not found or already withdrawn."},
                            status=status.HTTP_400_BAD_REQUEST)


class FundWithdrawalViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = FundWithdrawal.objects.all()
    serializer_class = FundWithdrawalSerializer

    def get_queryset(self):
        return FundWithdrawal.objects.filter(user=self.request.user, status='active')


class RewardEarnedViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = RewardEarned.objects.all()
    serializer_class = RewardEarnedSerializer

    serializer_classes = {
        'list': GetAllEarnedReward,
        'create': RewardEarnedSerializer,
        'retrieve': GetAllEarnedReward,
    }
    default_serializer_class = RewardEarnedSerializer

    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.default_serializer_class)

    def get_queryset(self):
        return RewardEarned.objects.filter(user=self.request.user, status='active')

