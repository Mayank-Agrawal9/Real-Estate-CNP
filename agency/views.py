import datetime
from decimal import Decimal

import requests
from dateutil.relativedelta import relativedelta
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Profile
from master.models import RewardMaster
from p2pmb.calculation import DistributeDirectCommission
from p2pmb.models import MLMTree
from payment_app.models import UserWallet, Transaction
from real_estate import settings
from .calculation import distribute_monthly_rent_for_super_agency, calculate_super_agency_rewards, \
    calculate_agency_rewards, calculate_field_agent_rewards, process_monthly_rentals_for_ppd_interest
from .models import Investment, Commission, RefundPolicy, FundWithdrawal, SuperAgency, Agency, FieldAgent, \
    RewardEarned, PPDAccount, InvestmentInterest
from .serializers import (InvestmentSerializer, CommissionSerializer,
                          RefundPolicySerializer, FundWithdrawalSerializer, SuperAgencySerializer, AgencySerializer,
                          FieldAgentSerializer, PPDModelSerializer, RewardEarnedSerializer, CreateInvestmentSerializer,
                          GetAllEarnedReward, InvestmentInterestSerializer, GetSuperAgencySerializer,
                          GetFieldAgentSerializer, GetAgencySerializer, GetRewardSerializer, IncomeCommissionSerializer)


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

    @action(detail=False, methods=['post'], url_path='get-balance')
    def check_balance(self, request):
        amount = Decimal(request.data.get('amount'))
        wallet_type = request.data.get('wallet_type')
        package = request.data.get('package')
        investment_type = request.data.get('investment_type')
        investment_guaranteed_type = request.data.get('investment_guaranteed_type')
        if not investment_type:
            investment_type = 'p2pmb'
        referral_code = request.data.get('referral_by')
        referral_by = None

        if not amount and not wallet_type and not package:
            return Response({'status': False}, status=status.HTTP_400_BAD_REQUEST)

        if referral_code:
            get_user_by_referral = Profile.objects.filter(referral_code=referral_code).last()
            referral_by = get_user_by_referral.user

        if not referral_by:
            get_user_by_referral = Profile.objects.filter(referral_code='CNPPB007700').last()
            if get_user_by_referral:
                referral_by = get_user_by_referral.user

        filter_condition = Q(user=self.request.user)
        if wallet_type == 'main_wallet':
            filter_condition &= Q(main_wallet_balance__gte=amount)
        if wallet_type == 'app_wallet':
            filter_condition &= Q(app_wallet_balance__gte=amount)
        check_wallet_balance = UserWallet.objects.filter(filter_condition)
        if check_wallet_balance:
            user_wallet = UserWallet.objects.filter(user=self.request.user, status='active').first()
            if wallet_type == 'app_wallet':
                if not user_wallet:
                    return Response({'status': False}, status=status.HTTP_400_BAD_REQUEST)

                if user_wallet.app_wallet_balance < amount:
                    return Response({'status': False}, status=status.HTTP_400_BAD_REQUEST)

                user_wallet.app_wallet_balance -= amount
                user_wallet.save()
            elif wallet_type == 'main_wallet':
                user_wallet = UserWallet.objects.filter(user=self.request.user, status='active').first()

                if not user_wallet:
                    return Response({'status': False}, status=status.HTTP_400_BAD_REQUEST)

                if user_wallet.main_wallet_balance < amount:
                    return Response({'status': False}, status=status.HTTP_400_BAD_REQUEST)
                user_wallet.main_wallet_balance -= amount
                user_wallet.save()

            transaction_data = {
                'created_by': self.request.user,
                'sender': self.request.user,
                'amount': amount,
                'taxable_amount': 0,
                'transaction_type': "investment",
                'transaction_status': "approved",
                'payment_method': "wallet",
                'remarks': "Payment Initiated for P2PMB Model.",
            }

            transaction = Transaction.objects.create(**transaction_data)
            investment_data = {
                'created_by': self.request.user,
                'user': self.request.user,
                'amount': amount,
                'investment_type': investment_type,
                'gst': 0,
                'transaction_id': transaction,
                'pay_method': wallet_type,
                'is_approved': True,
                'approved_by': self.request.user,
                'approved_on': datetime.datetime.now(),
                'investment_guaranteed_type': investment_guaranteed_type,
                'referral_by': referral_by if referral_by else None
            }

            investment = Investment.objects.create(**investment_data)
            if package:
                investment.package.set(package)
            get_mlm = MLMTree.objects.filter(child=self.request.user).last()
            if get_mlm:
                get_mlm.turnover += amount
                get_mlm.save()
            return Response({"status": True}, status=status.HTTP_200_OK)
        else:
            return Response({"status": False}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='initiate-payment-p2pmb')
    class InitiatePaymentView(APIView):
        def post(self, request):
            amount = Decimal(request.data.get('amount'))
            referral_code = request.data.get('referral_by')

            if not amount:
                return Response({'status': False, 'message': 'Amount is required'}, status=status.HTTP_400_BAD_REQUEST)

            referral_by = None
            if referral_code:
                referral_profile = Profile.objects.filter(referral_code=referral_code).last()
                if referral_profile:
                    referral_by = referral_profile.user

            # Create transaction with pending status
            transaction = Transaction.objects.create(
                created_by=request.user,
                sender=request.user,
                amount=amount,
                taxable_amount=0,
                transaction_type="investment",
                transaction_status="pending",
                payment_method="cashfree",
                remarks="Cashfree payment initiated."
            )

            # Cashfree API request
            headers = {
                "Content-Type": "application/json",
                "x-client-id": settings.CASHFREE_APP_ID,
                "x-client-secret": settings.CASHFREE_SECRET_KEY,
                "x-api-version": "2022-09-01"
            }

            payload = {
                "order_id": f"ORD{transaction.id}",
                "order_amount": float(amount),
                "order_currency": "INR",
                "customer_details": {
                    "customer_id": str(request.user.id),
                    "customer_email": request.user.email,
                    "customer_phone": request.user.profile.mobile if hasattr(request.user, 'profile') else "0000000000"
                },
                "order_meta": {
                    "return_url": f"{settings.BASE_URL}/payment/callback?order_id=ORD{transaction.id}",
                    "notify_url": f"{settings.BASE_URL}/api/payment/webhook/"
                }
            }

            response = requests.post(f"{settings.CASHFREE_BASE_URL}/pg/orders", json=payload, headers=headers)

            if response.status_code == 200:
                data = response.json()
                session_id = data.get("payment_session_id")
                payment_url = f"{settings.CASHFREE_BASE_URL}/pg/checkout/post/{session_id}"
                return Response({
                    "status": True,
                    "payment_url": payment_url,
                    "order_id": f"ORD{transaction.id}"
                }, status=status.HTTP_200_OK)

            return Response({"status": False, "message": "Payment initiation failed"},
                            status=status.HTTP_400_BAD_REQUEST)


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
        wallet_type = request.data.get('wallet_type')
        sender_wallet = UserWallet.objects.filter(user=request.user).last()
        if not sender_wallet:
            return Response({"error": "Please create your wallet first."},
                            status=status.HTTP_400_BAD_REQUEST)
        if wallet_type == 'app_wallet' and sender_wallet.app_wallet_balance < deposit_amount:
            return Response({"error": "Insufficient balance in your app wallet."}, status=status.HTTP_400_BAD_REQUEST)
        elif wallet_type == 'main_wallet' and sender_wallet.main_wallet_balance < deposit_amount:
            return Response({"error": "Insufficient balance in your main wallet."},
                            status=status.HTTP_400_BAD_REQUEST)
        if deposit_amount < 100 or deposit_amount > 4999:
            return Response({"error": "Deposit amount must be between ₹100 and ₹4999."},
                            status=status.HTTP_400_BAD_REQUEST)
        if wallet_type == 'app_wallet':
            sender_wallet.app_wallet_balance -= deposit_amount
        if wallet_type == 'main_wallet':
            sender_wallet.main_wallet_balance -= deposit_amount
        sender_wallet.save()

        Transaction.objects.create(
            created_by=request.user,
            sender=request.user,
            amount=deposit_amount,
            transaction_status='approved',
            transaction_type='investment',
            status='active',
            payment_method='wallet'
        )
        ppd_account = PPDAccount.objects.create(created_by=request.user, user=request.user,
                                                deposit_amount=deposit_amount,
                                                deposit_date=datetime.datetime.now().date(), remarks=remarks)
        return Response({"message": "PPD account created successfully.", "account_id": ppd_account.id},
                        status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='withdraw-ppd-amount/(?P<account_id>\d+)')
    def withdraw_ppd_amount(self, request, account_id):
        try:
            if not (request.user.profile.is_kyc and request.user.profile.is_kyc_verified):
                return Response(
                    {"error": "You are not completed your KYC, "
                              "Please first verify your KYC then you are able to withdraw you amount."},
                    status=status.HTTP_400_BAD_REQUEST
                )
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


class InvestmentInterestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = InvestmentInterest.objects.active()
    serializer_class = InvestmentInterestSerializer

    def get_queryset(self):
        return InvestmentInterest.objects.active()


class UserSuperAgencyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = SuperAgency.objects.filter(profile__user=request.user).last()
        if not queryset:
            return Response({'error': "You don't have any super agency yet."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = GetSuperAgencySerializer(queryset, many=False).data
        return Response(serializer, status=status.HTTP_200_OK)


class UserAgencyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Agency.objects.filter(created_by=request.user).last()
        if not queryset:
            return Response({'error': "You don't have any agency yet."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = GetAgencySerializer(queryset, many=False).data
        return Response(serializer, status=status.HTTP_200_OK)


class UserFieldAgentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = FieldAgent.objects.filter(profile__user=request.user).last()
        if not queryset:
            return Response({'error': "You are not field agent yet."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = GetFieldAgentSerializer(queryset, many=False).data
        return Response(serializer, status=status.HTTP_200_OK)


class UserSuperAgencyIncomeDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = SuperAgency.objects.filter(profile__user=request.user).last()
        if not queryset:
            return Response({'error': "You don't have any super agency yet."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = GetSuperAgencySerializer(queryset, many=False).data
        return Response(serializer, status=status.HTTP_200_OK)


class UserAgencyIncomeDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Agency.objects.filter(user=request.user).last()
        if not queryset:
            return Response({'error': "You don't have any agency yet."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = GetAgencySerializer(queryset, many=False).data
        return Response(serializer, status=status.HTTP_200_OK)


class UserFieldAgentIncomeDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = FieldAgent.objects.filter(profile__user=request.user).last()
        if not queryset:
            return Response({'error': "You are not field agent yet."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = GetFieldAgentSerializer(queryset, many=False).data
        return Response(serializer, status=status.HTTP_200_OK)


class EarnedRewardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        applicable_for = (
            request.query_params.get('applicable_for')
        )

        if not applicable_for or applicable_for not in ['super_agency', 'agency', 'field_agent']:
            return Response(
                {"detail": "One applicable_for query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        queryset = RewardEarned.objects.filter(status='active', user=self.request.user,
                                               reward__applicable_for=applicable_for).select_related('reward')
        if not queryset:
            return Response({'error': "You are not earned any reward yet."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = GetAllEarnedReward(queryset, many=True).data
        return Response(serializer, status=status.HTTP_200_OK)


class RemainingRewardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        applicable_for = (
            request.query_params.get('applicable_for')
        )

        if not applicable_for or applicable_for not in ['super_agency', 'agency', 'field_agent']:
            return Response(
                {"detail": "One applicable_for query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        earned_reward = RewardEarned.objects.filter(status='active', user=self.request.user,
                                                    reward__applicable_for=applicable_for).values_list(
            'reward__id', flat=True)

        remaining_rewards = RewardMaster.objects.filter(status='active', applicable_for=applicable_for
                                                        ).exclude(id__in=earned_reward).order_by('turnover_threshold')
        serializer = GetRewardSerializer(remaining_rewards, many=True).data
        return Response(serializer, status=status.HTTP_200_OK)


class IncomeDetailsAPIView(APIView):
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        applicable_for = (
            request.query_params.get('applicable_for')
        )

        if not applicable_for or applicable_for not in ['super_agency', 'agency', 'field_agent']:
            return Response(
                {"detail": "One applicable_for query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        get_income_details = Commission.objects.filter(commission_to=self.request.user, applicable_for=applicable_for,
                                                       is_paid=True)
        serializer = IncomeCommissionSerializer(get_income_details, many=True).data
        return Response(serializer, status=status.HTTP_200_OK)
