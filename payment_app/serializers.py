import datetime
import uuid

from django.contrib.auth.models import User
from rest_framework import serializers

from payment_app.choices import PAYMENT_METHOD
from payment_app.models import UserWallet, Transaction


class PayUserSerializer(serializers.Serializer):
    recipient_email = serializers.EmailField(required=True)
    amount = serializers.FloatField(required=False, min_value=0.01)
    wallet_type = serializers.ChoiceField(choices=['main_wallet', 'app_wallet'], default='app_wallet')

    def validate(self, data):
        sender = self.context['request'].user
        recipient_email = data['recipient_email']
        amount = data.get('amount')
        wallet_type = data.get('wallet_type')

        try:
            recipient = User.objects.filter(username=recipient_email).last()
        except Exception as e:
            raise serializers.ValidationError("Recipient not found.")

        if sender == recipient:
            raise serializers.ValidationError("You cannot send money to yourself.")

        sender_wallet = UserWallet.objects.filter(user=sender).first()
        if not sender_wallet:
            raise serializers.ValidationError("Sender's wallet not found.")

        if amount:
            if wallet_type == 'app_wallet' and sender_wallet.app_wallet_balance < amount:
                raise serializers.ValidationError("Insufficient balance in your wallet.")
            if wallet_type == 'main_wallet' and sender_wallet.main_wallet_balance < amount:
                raise serializers.ValidationError("Insufficient balance in your wallet.")

        data['recipient'] = recipient
        return data


# class ScanAndPayUserSerializer(serializers.Serializer):
#     recipient = serializers.CharField(required=True)
#     amount = serializers.FloatField(required=False, min_value=0.01)
#     wallet_type = serializers.ChoiceField(choices=['main_wallet', 'app_wallet'], default='app_wallet')
#
#     def validate(self, data):
#         sender = self.context['request'].user
#         recipient = data['recipient']
#         amount = data.get('amount')
#         wallet_type = data.get('wallet_type')
#
#         recipient = User.objects.filter(username=recipient).last()
#         if not recipient:
#             raise serializers.ValidationError("Recipient not found.")
#
#         if sender == recipient:
#             raise serializers.ValidationError("You cannot send money to yourself.")
#
#         sender_wallet = UserWallet.objects.filter(user=sender).first()
#         if not sender_wallet:
#             raise serializers.ValidationError("Sender's wallet not found.")
#
#         if amount:
#             if wallet_type == 'app_wallet' and sender_wallet.app_wallet_balance < amount:
#                 raise serializers.ValidationError("Insufficient balance in your wallet.")
#             if wallet_type == 'main_wallet' and sender_wallet.main_wallet_balance < amount:
#                 raise serializers.ValidationError("Insufficient balance in your wallet.")
#
#         data['recipient'] = recipient
#         return data


class WithdrawRequestSerializer(serializers.Serializer):
    amount = serializers.FloatField(required=True, min_value=0.01)

    def validate(self, data):
        wallet = UserWallet.objects.filter(user=self.context['request'].user).last()
        if not wallet:
            raise serializers.ValidationError("You do not have a wallet. Please connect to web_admin.")
        if wallet.main_wallet_balance < data['amount']:
            raise serializers.ValidationError("Insufficient balance.")

        allowed_dates = [10, 20, 30]
        current_date = datetime.datetime.now()
        if current_date.day not in allowed_dates:
            raise serializers.ValidationError(
                "Withdrawals are only allowed on the 10th, 20th, or 30th of each month."
            )

        withdrawal_start_time = datetime.time(10, 0, 0)
        withdrawal_end_time = datetime.time(18, 0, 0)
        current_time = current_date.time()
        if not (withdrawal_start_time <= current_time <= withdrawal_end_time):
            raise serializers.ValidationError(
                "Withdrawals can only be made between 10:00 AM to 6:00 PM."
            )
        return data


class ApproveTransactionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'reject'], required=True)


class UserWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserWallet
        fields = '__all__'


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'


class AddMoneyToWalletSerializer(serializers.Serializer):
    amount = serializers.FloatField(required=True, min_value=0.01)
    payment_method = serializers.ChoiceField(choices=PAYMENT_METHOD, required=True)
    payment_slip = serializers.FileField(required=True)
    deposit_transaction_id = serializers.CharField(read_only=True)
    remarks = serializers.CharField(required=True)

    def validate(self, data):
        data['deposit_transaction_id'] = str(uuid.uuid4())
        return data