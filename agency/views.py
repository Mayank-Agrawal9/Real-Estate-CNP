import base64
import datetime
import hashlib
import hmac
import json
from decimal import Decimal

import requests
from dateutil.relativedelta import relativedelta
from django.db.models import Q, Sum
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, status, filters
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
    calculate_agency_rewards, calculate_field_agent_rewards, process_monthly_rentals_for_ppd_interest, \
    distribute_monthly_rent_for_agency
from .models import Investment, Commission, RefundPolicy, FundWithdrawal, SuperAgency, Agency, FieldAgent, \
    RewardEarned, PPDAccount, InvestmentInterest, AgencyPackagePurchase
from .serializers import (InvestmentSerializer, CommissionSerializer,
                          RefundPolicySerializer, FundWithdrawalSerializer, SuperAgencySerializer, AgencySerializer,
                          FieldAgentSerializer, PPDModelSerializer, RewardEarnedSerializer, CreateInvestmentSerializer,
                          GetAllEarnedReward, InvestmentInterestSerializer, GetSuperAgencySerializer,
                          GetFieldAgentSerializer, GetAgencySerializer, GetRewardSerializer, IncomeCommissionSerializer,
                          BuyPackageSerializer)


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
            get_user_by_referral = Profile.objects.filter(referral_code='GAVIRON001166').last()
            if get_user_by_referral:
                referral_by = get_user_by_referral.user

        previous_investment = Investment.objects.filter(user=request.user, status='active', package__isnull=False,
                                                        package__applicable_for='p2pmb').order_by('-amount').first()

        if previous_investment and previous_investment.amount >= amount:
            return Response({
                'status': False,
                'message': f"You cannot buy this package because you already bought ₹{previous_investment.amount} package or higher."
            }, status=status.HTTP_400_BAD_REQUEST)

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
                'status': 'active',
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
    def initiate_payment(self, request):
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
            get_user_by_referral = Profile.objects.filter(referral_code='GAVIRON001166').last()
            if get_user_by_referral:
                referral_by = get_user_by_referral.user

        previous_investment = Investment.objects.filter(user=request.user, status='active', package__isnull=False,
                                                        package__applicable_for='p2pmb').order_by('-amount').first()

        if previous_investment and previous_investment.amount >= amount:
            return Response({
                'status': False,
                'message': f"You cannot buy this package because you already bought ₹{previous_investment.amount} package or higher."
            }, status=status.HTTP_400_BAD_REQUEST)

        filter_condition = Q(user=self.request.user)
        if wallet_type == 'main_wallet':
            filter_condition &= Q(main_wallet_balance__gte=amount)
        if wallet_type == 'app_wallet':
            filter_condition &= Q(app_wallet_balance__gte=amount)

        if not amount:
            return Response({'status': False, 'message': 'Amount is required'}, status=status.HTTP_400_BAD_REQUEST)

        if amount < 10:
            return Response({'status': False, 'message': 'Minimum amount is ₹10'}, status=status.HTTP_400_BAD_REQUEST)

        transaction = Transaction.objects.create(
            created_by=request.user, sender=request.user, amount=amount,
            taxable_amount=0, transaction_type="investment",
            transaction_status="pending", payment_method="cashfree",
            remarks="Cashfree payment initiated."
        )

        investment_data = {
            'created_by': self.request.user,
            'status': 'inactive',
            'user': self.request.user,
            'amount': amount,
            'investment_type': investment_type,
            'gst': 0,
            'transaction_id': transaction,
            'pay_method': wallet_type,
            'is_approved': False,
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

        profile = getattr(request.user, 'profile', None)
        mobile_number = getattr(profile, 'mobile_number', '') if profile else ''
        customer_phone = (
            str(mobile_number).strip()
            if mobile_number and str(mobile_number).strip().lower() not in ['null', 'none', '']
            else "0000000000"
        )
        headers = {
            "Content-Type": "application/json",
            "x-client-id": settings.CASHFREE_APP_ID,
            "x-client-secret": settings.CASHFREE_SECRET_KEY,
            "x-api-version": "2025-01-01"
        }

        payload = {
            "order_id": f"{transaction.id}",
            "order_amount": float(amount),
            "order_currency": "INR",
            "customer_details": {
                "customer_id": str(request.user.id),
                "customer_email": request.user.email or "test@example.com",
                "customer_phone": customer_phone,
                "customer_name": request.user.get_full_name() or "Customer"
            },
            "order_meta": {
                "return_url": f"{settings.BASE_URL}/api/agency/callback?order_id={transaction.id}",
                "notify_url": f"{settings.BASE_URL}/api/agency/webhook/",
                "payment_methods": "cc,dc,upi,paypal",
                "investment_id": investment.id
            }
        }
        res = None
        try:
            response = requests.post(
                f"{settings.CASHFREE_ORDER_URL}", json=payload, headers=headers
            )
            res = response.text
            response.raise_for_status()
            data = response.json()
            if response.status_code == 200:
                session_id = data.get("payment_session_id")
                payment_url = f"{settings.CASHFREE_BASE_URL}/checkout/post/{session_id}"
                transaction.gateway_reference = data.get("cf_order_id")
                transaction.save()

                return Response({
                    "status": True,
                    "payment_url": payment_url,
                    "order_id": payload["order_id"],
                    "session_id": session_id
                }, status=status.HTTP_200_OK)

            return Response({
                "status": False,
                "message": "Payment initiation failed",
                "error": data.get("message", "Unknown error")
            }, status=status.HTTP_400_BAD_REQUEST)

        except requests.exceptions.RequestException as e:
            return Response({
                "status": False,
                "message": "Payment gateway error",
                "error": str(e),
                "text_reponse": res,
                "payload": payload,
                "headers": headers,
            }, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class CashfreeWebhookView(APIView):

    def post(self, request):
        raw_body = request.body
        signature = request.headers.get("x-cf-signature")

        if not signature:
            return Response({'status': False, 'message': 'Missing signature'}, status=status.HTTP_403_FORBIDDEN)

        computed_signature = base64.b64encode(
            hmac.new(
                key=bytes(settings.CASHFREE_SECRET_KEY, 'utf-8'), msg=raw_body, digestmod=hashlib.sha256
            ).digest()
        ).decode()

        if computed_signature != signature:
            return Response({'status': False, 'message': 'Invalid signature'}, status=status.HTTP_403_FORBIDDEN)

        try:
            data = json.loads(raw_body)
        except Exception:
            return Response({'status': False, 'message': 'Invalid JSON body'}, status=status.HTTP_400_BAD_REQUEST)

        order_id = data.get('order_id')
        transaction_status = data.get('order_status')
        order_meta = data.get('order_meta', {})
        investment_id = order_meta.get('investment_id')

        if not order_id or not transaction_status or not investment_id:
            return Response({'status': False, 'message': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            transaction = Transaction.objects.get(id=order_id)
        except Exception as e:
            return Response({'status': False, 'message': 'Transaction not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            investment = Investment.objects.get(id=investment_id)
        except Exception as e:
            return Response({'status': False, 'message': 'Investment not found'}, status=status.HTTP_404_NOT_FOUND)

        if transaction_status == 'PAID':
            if transaction.transaction_status != 'approved':
                transaction.transaction_status = 'approved'
                transaction.save()

            if investment.status != 'active' or not investment.is_approved:
                investment.status = 'active'
                investment.is_approved = True
                investment.save()

            return Response({'status': True, 'message': 'Payment successfully processed'}, status=status.HTTP_200_OK)
        return Response({'status': True, 'message': f'Status received: {transaction_status}'}, status=status.HTTP_200_OK)


class CommissionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Commission.objects.all()
    serializer_class = CommissionSerializer
    filterset_fields = ['commission_type', 'applicable_for']

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

    @action(detail=True, methods=['post'], url_path='withdraw-ppd-amount')
    def withdraw_ppd_amount(self, request, pk=None):
        try:
            if not (request.user.profile.is_kyc and request.user.profile.is_kyc_verified):
                return Response(
                    {"error": "You are not completed your KYC, "
                              "Please first verify your KYC then you are able to withdraw you amount."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            ppd_account = PPDAccount.objects.get(id=pk, user=request.user, is_active=True)
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
        qs = RewardEarned.objects.filter(user=self.request.user)

        applicable_for = self.request.query_params.get("applicable_for")
        if applicable_for:
            qs = qs.filter(reward__applicable_for=applicable_for)

        return qs


class InvestmentInterestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = InvestmentInterest.objects.active()
    filter_backends = [filters.SearchFilter]
    search_fields = ['investment__user__username', 'investment__user__email', 'investment__user__first_name',
                     'investment__user__last_name']
    serializer_class = InvestmentInterestSerializer

    def get_queryset(self):
        queryset = InvestmentInterest.objects.active().select_related('investment', 'investment__user')
        month = self.request.query_params.get("month")
        year = self.request.query_params.get("year")
        if month:
            queryset = queryset.filter(interest_send_date__month=int(month))
        if year:
            queryset = queryset.filter(interest_send_date__year=int(year))
        return queryset


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
        applicable_for = (request.query_params.get('applicable_for'))

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


class BuyPackageView(APIView):
    """API to purchase a package using wallet balance"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BuyPackageSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success': True, 'message': 'Package purchased successfully'},
                        status=status.HTTP_200_OK)


class DistributeSuperAgencyRent(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        distribute_monthly_rent_for_super_agency()
        return Response({'message': 'Super Agency Rent Distributed successfully'})


class DistributeAgencyRent(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        distribute_monthly_rent_for_agency()
        return Response({'message': 'Agency Rent Distributed successfully'})


class SuperAgencyAppCommission(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        investment_data = (
            AgencyPackagePurchase.objects.filter(
                user=user, status='completed', buy_for='super_agency', package__isnull=False
            ).aggregate(total=Sum('amount_paid'))
        )
        invested_amount = investment_data['total'] or Decimal('0')

        commissions = (
            Commission.objects.filter(status='active', commission_to=user, applicable_for='super_agency')
            .values('commission_type')
            .annotate(total=Sum('commission_amount'))
        )

        commission_totals = {
            'turnover_commission': Decimal('0'),
            'rent': Decimal('0'),
            'agency_commission': Decimal('0'),
            'field_agent_commission': Decimal('0'),
            'reward': Decimal('0'),
        }

        for item in commissions:
            ctype = item['commission_type']
            if ctype in commission_totals:
                commission_totals[ctype] = item['total'] or Decimal('0')

        response = {
            'invested_amount': invested_amount,
            'return_amount': invested_amount * Decimal('3'),
            'office_rent': commission_totals['rent'],
            'agency_commission': commission_totals['agency_commission'],
            'field_agent_commission': commission_totals['field_agent_commission'],
            'turnover_commission': commission_totals['turnover_commission'],
            'reward_commission': commission_totals['reward'],
        }

        return Response(response, status=status.HTTP_200_OK)


class SuperAgencyPackageDetails(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        get_rewards = RewardMaster.objects.filter(
            status='active', applicable_for='super_agency').order_by('turnover_threshold')
        response = {
            'invested_amount': '50,00,000 ₹ + 90,000 ₹ = 50,90,000 ₹',
            'return_amount': 5000000 * Decimal('3'),
            'office_rent': '50,000₹/Month for 10 years = 60,00,000₹',
            'agency_commission': '25% for each agency (5,00,000₹ Each Agency) upto 100 agency',
            'field_agent_commission': '5% for each field agent upto 10,000 field agent',
            'turnover_commission': '0.25% of total turnover',
            'reward_commission': '₹10,000 to ₹100 crore',
            'area_required': '650 Sq.ft',
            'rewards': GetRewardSerializer(get_rewards, many=True).data,
        }
        return Response(response, status=status.HTTP_200_OK)


class AgencyPackageDetails(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        get_rewards = RewardMaster.objects.filter(
            status='active', applicable_for='agency').order_by('turnover_threshold')
        response = {
            'invested_amount': '50,00,00 ₹ + 9000 ₹ = 50,90,00 ₹',
            'return_amount': 500000 * Decimal('2'),
            'office_rent': '5000₹/Month for 10 years = 60,00,00₹',
            'field_agent_commission': '25% for each field agent upto 100 field agent',
            'turnover_commission': '0.5% of agent generated turnover',
            'reward_commission': '₹10,000 to ₹10 crore',
            'area_required': '100 Sq.ft',
            'rewards': GetRewardSerializer(get_rewards, many=True).data,
        }
        return Response(response, status=status.HTTP_200_OK)


class FieldAgentPackageDetails(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        get_rewards = RewardMaster.objects.filter(
            status='active', applicable_for='field_agent').order_by('turnover_threshold')
        response = {
            'invested_amount': '25,000 ₹ + 4,500 ₹ = 29,500 ₹',
            'commission': '3% on every transaction with TDS support',
            'reward_commission': '₹10,000 to ₹1 Crore',
            'rewards': GetRewardSerializer(get_rewards, many=True).data,
        }
        return Response(response, status=status.HTTP_200_OK)


class AgencyAppCommission(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        investment_data = (
            AgencyPackagePurchase.objects.filter(
                user=user, status='completed', buy_for='agency', package__isnull=False
            ).aggregate(total=Sum('amount_paid'))
        )
        invested_amount = investment_data['total'] or Decimal('0')

        commissions = (
            Commission.objects.filter(status='active', commission_to=user, applicable_for='agency')
            .values('commission_type').annotate(total=Sum('commission_amount'))
        )

        commission_totals = {
            'turnover_commission': Decimal('0'),
            'rent': Decimal('0'),
            'field_agent_commission': Decimal('0'),
            'reward': Decimal('0'),
        }

        for item in commissions:
            ctype = item['commission_type']
            if ctype in commission_totals:
                commission_totals[ctype] = item['total'] or Decimal('0')

        response = {
            'invested_amount': invested_amount,
            'return_amount': invested_amount * Decimal('2'),
            'office_rent': commission_totals['rent'],
            'field_agent_commission': commission_totals['field_agent_commission'],
            'turnover_commission': commission_totals['turnover_commission'],
            'reward_commission': commission_totals['reward'],
        }

        return Response(response, status=status.HTTP_200_OK)