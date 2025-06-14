import datetime
from decimal import Decimal

from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agency.models import Investment, FundWithdrawal
from payment_app.models import Transaction, UserWallet
from payment_app.serializers import WithdrawRequestSerializer, ApproveTransactionSerializer, PayUserSerializer, \
    UserWalletSerializer, TransactionSerializer, AddMoneyToWalletSerializer


# Create your views here.

class UserWalletViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserWalletSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['user__username',]

    def get_queryset(self):
        return UserWallet.objects.filter(user=self.request.user, status='active')

    @action(detail=False, methods=['post'], url_path='pay-money')
    def send_money_to_user_wallet(self, request):
        serializer = PayUserSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        sender = request.user
        recipient = serializer.validated_data['recipient']
        amount = serializer.validated_data.get('amount')
        wallet_type = serializer.validated_data.get('wallet_type', 'app_wallet')

        if not (sender.profile.is_kyc and sender.profile.is_kyc_verified):
            return Response(
                {"error": "You have not completed KYC verification."},
                status=status.HTTP_400_BAD_REQUEST
            )
        # if not (recipient.profile.is_kyc and recipient.profile.is_kyc_verified):
        #     return Response(
        #         {"error": "Recipient has not completed their KYC verification."},
        #         status=status.HTTP_400_BAD_REQUEST
        #     )

        if amount is None:
            return Response(
                {"message": "Recipient is valid for transfer."},
                status=status.HTTP_200_OK
            )

        sender_wallet = UserWallet.objects.get(user=sender)
        recipient_wallet, _ = UserWallet.objects.get_or_create(user=recipient)
        if wallet_type == "app_wallet":
            taxable_amount = Decimal(amount) * Decimal('0.05')
            payable_amount = Decimal(amount) - taxable_amount
            sender_wallet.app_wallet_balance -= payable_amount
            sender_wallet.save()
            recipient_wallet.app_wallet_balance += payable_amount
            recipient_wallet.save()
            Transaction.objects.create(
                created_by=request.user,
                sender=sender,
                receiver=recipient,
                amount=amount,
                taxable_amount=taxable_amount,
                transaction_status='approved',
                transaction_type='send',
                status='active'
            )
        elif wallet_type == "main_wallet":
            sender_wallet.main_wallet_balance -= Decimal(amount)
            sender_wallet.save()
            recipient_wallet.main_wallet_balance += Decimal(amount)
            recipient_wallet.save()
            Transaction.objects.create(
                created_by=request.user,
                sender=sender,
                receiver=recipient,
                amount=amount,
                transaction_status='approved',
                transaction_type='send',
                status='active'
            )
        else:
            return Response(
                {"message": "Currently we are accepting in-app transfer and main wallet transfer."},
                status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "Payment successfully transferred."}, status=status.HTTP_200_OK)

    # @action(detail=False, methods=['post'], url_path='scan-and-pay')
    # def scan_and_pay_money_to_user_wallet(self, request):
    #     serializer = ScanAndPayUserSerializer(data=request.data, context={'request': request})
    #     serializer.is_valid(raise_exception=True)
    #
    #     sender = request.user
    #     recipient = serializer.validated_data['recipient']
    #     amount = serializer.validated_data.get('amount')
    #     wallet_type = serializer.validated_data.get('wallet_type', 'app_wallet')
    #
    #     if not (sender.profile.is_kyc and sender.profile.is_kyc_verified):
    #         return Response(
    #             {"error": "You have not completed KYC verification."},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )
    #     # if not (recipient.profile.is_kyc and recipient.profile.is_kyc_verified):
    #     #     return Response(
    #     #         {"error": "Recipient has not completed their KYC verification."},
    #     #         status=status.HTTP_400_BAD_REQUEST
    #     #     )
    #
    #     if amount is None:
    #         return Response(
    #             {"message": "Recipient is valid for transfer."},
    #             status=status.HTTP_200_OK
    #         )
    #
    #     sender_wallet = UserWallet.objects.get(user=sender)
    #     recipient_wallet, _ = UserWallet.objects.get_or_create(user=recipient)
    #     if wallet_type == "app_wallet":
    #         taxable_amount = Decimal(amount) * Decimal('0.05')
    #         payable_amount = Decimal(amount) - taxable_amount
    #         sender_wallet.app_wallet_balance -= payable_amount
    #         sender_wallet.save()
    #         recipient_wallet.app_wallet_balance += payable_amount
    #         recipient_wallet.save()
    #         Transaction.objects.create(
    #             created_by=request.user, sender=sender, receiver=recipient,
    #             amount=amount, taxable_amount=taxable_amount, tds_amount=taxable_amount, transaction_status='approved',
    #             transaction_type='send', status='active'
    #         )
    #     elif wallet_type == "main_wallet":
    #         sender_wallet.main_wallet_balance -= Decimal(amount)
    #         sender_wallet.save()
    #         recipient_wallet.main_wallet_balance += Decimal(amount)
    #         recipient_wallet.save()
    #         Transaction.objects.create(
    #             created_by=request.user, sender=sender, receiver=recipient,
    #             amount=amount, transaction_status='approved', tds_amount=taxable_amount,
    #             transaction_type='send', status='active'
    #         )
    #     else:
    #         return Response(
    #             {"message": "Currently we are accepting in-app transfer and main wallet transfer."},
    #             status=status.HTTP_400_BAD_REQUEST)
    #
    #     return Response({"message": "Payment successfully transferred."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='send-money-to-wallet')
    def send_money_to_main_wallet(self, request):
        user_wallet = UserWallet.objects.get(user=request.user)
        transfer_amount = Decimal(request.data.get('amount', 0))

        if not (request.user.profile.is_kyc and request.user.profile.is_kyc_verified):
            return Response(
                {"error": "You has not completed KYC verification."}, status=status.HTTP_400_BAD_REQUEST)

        if transfer_amount <= 0:
            return Response(
                {"error": "Transfer amount must be greater than zero."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if transfer_amount > user_wallet.app_wallet_balance:
            return Response(
                {"error": "Insufficient balance in app wallet."}, status=status.HTTP_400_BAD_REQUEST)

        admin_charge = transfer_amount * Decimal('0.05')
        fee = transfer_amount * Decimal('0.05')
        taxable_amount = admin_charge + fee
        amount_after_fee = transfer_amount - admin_charge - fee

        # Update wallet balances
        user_wallet.app_wallet_balance -= transfer_amount
        user_wallet.main_wallet_balance += amount_after_fee
        user_wallet.tds_amount += taxable_amount if taxable_amount else 0
        user_wallet.save()

        Transaction.objects.create(
            created_by=request.user,
            sender=request.user,
            receiver=request.user,
            amount=amount_after_fee,
            transaction_status='approved',
            transaction_type='transfer',
            status='active',
            taxable_amount=taxable_amount if taxable_amount else 0,
            payment_method='wallet'
        )

        return Response(
            {"message": "Transfer successful.", "transfer_amount": f"{transfer_amount:.2f}",
                "fee_deducted": f"{fee:.2f}", "admin_charges": f"{admin_charge:.2f}",
             "amount_transferred_to_main_wallet": f"{amount_after_fee:.2f}",
                "app_wallet_balance": f"{user_wallet.app_wallet_balance:.2f}",
             "main_wallet_balance": f"{user_wallet.main_wallet_balance:.2f}",
            }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='withdraw-payment')
    def withdraw_payment(self, request):
        if not (request.user.profile.is_kyc and request.user.profile.is_kyc_verified):
            return Response(
                {"error": "You has not completed KYC verification."}, status=status.HTTP_400_BAD_REQUEST
            )
        serializer = WithdrawRequestSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data['amount']
        taxable_amount = (Decimal(amount) * Decimal('0.05'))
        Transaction.objects.create(
            created_by=request.user, sender=request.user,
            receiver=request.user, amount=amount,
            taxable_amount=taxable_amount, transaction_type='withdraw', transaction_status='pending'
        )
        FundWithdrawal.objects.create(user=request.user, withdrawal_amount=amount,
                                      withdrawal_date=datetime.datetime.now(), taxable_amount=taxable_amount)
        return Response({"message": "Your withdrawal will be credited to your account within 48 hours. "
                                    "Thank you for your patience."}, status=status.HTTP_201_CREATED)


class TransactionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['transaction_type', 'transaction_status', 'payment_method']
    search_fields = ['transaction_id', 'deposit_transaction_id']

    def get_queryset(self):
        return Transaction.objects.filter(Q(sender=self.request.user, transaction_status='transfer') | Q(receiver=self.request.user),
                                          status='active').order_by('-date_created')

    @action(detail=False, methods=['post'], url_path='add-money-to-wallet')
    def add_money_to_wallet(self, request):
        serializer = AddMoneyToWalletSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        sender = request.user
        # if not (sender.profile.is_kyc and sender.profile.is_kyc_verified):
        #     return Response(
        #         {"error": "KYC verification is incomplete, you can not add the money."},
        #         status=status.HTTP_400_BAD_REQUEST)

        Transaction.objects.create(
            sender=sender, transaction_status='pending', transaction_type='deposit', **serializer.validated_data
        )
        Investment.objects.create(
            user=sender,
            amount=serializer.validated_data['amount'],
            investment_type=sender.profile.role,
            gst=0
        )
        return Response({"message": "Request for payment deposit sent successfully."}, status=status.HTTP_200_OK)


class ApproveTransactionView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, transaction_id):
        if not request.user.is_staff:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        try:
            transaction = Transaction.objects.get(transaction_id=transaction_id, status='pending')
        except Exception as e:
            return Response({"error": "Transaction not found or already processed"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ApproveTransactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data['action'] == 'approve':
            if transaction.transaction_type == 'withdraw':
                wallet = UserWallet.objects.get(user=transaction.sender)
                if wallet.main_wallet_balance < transaction.amount:
                    return Response({"error": "Insufficient balance for withdrawal."},
                                    status=status.HTTP_400_BAD_REQUEST)
                wallet.balance -= transaction.amount
                wallet.save()

            elif transaction.transaction_type == 'deposit':
                wallet = UserWallet.objects.filter(user=transaction.receiver).last()
                wallet.main_wallet_balance += transaction.amount
                wallet.save()

            transaction.status = 'approved'

        elif serializer.validated_data['action'] == 'reject':
            transaction.status = 'rejected'

        transaction.verified_by = request.user
        transaction.verified_on = datetime.datetime.now()
        transaction.save()

        return Response({"message": f"Transaction {serializer.validated_data['action']}ed successfully."}, status=status.HTTP_200_OK)

