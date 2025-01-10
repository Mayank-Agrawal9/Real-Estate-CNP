import uuid

from django.contrib.auth.models import User
from rest_framework import serializers

from payment_app.choices import PAYMENT_METHOD
from payment_app.models import UserWallet, Transaction


class PayUserSerializer(serializers.Serializer):
    recipient_email = serializers.EmailField(required=True)
    amount = serializers.FloatField(required=True, min_value=0.01)

    def validate(self, data):
        sender = self.context['request'].user
        recipient_email = data['recipient_email']
        amount = data['amount']

        try:
            recipient = User.objects.get(email=recipient_email)
        except User.DoesNotExist:
            raise serializers.ValidationError("Recipient not found.")

        if sender == recipient:
            raise serializers.ValidationError("You cannot send money to yourself.")

        sender_wallet = UserWallet.objects.filter(user=sender).first()
        if not sender_wallet:
            raise serializers.ValidationError("Sender's wallet not found.")
        if sender_wallet.main_wallet_balance < amount:
            raise serializers.ValidationError("Insufficient balance in your wallet.")

        data['recipient'] = recipient
        return data


class WithdrawRequestSerializer(serializers.Serializer):
    amount = serializers.FloatField(required=True, min_value=0.01)

    def validate(self, data):
        wallet = UserWallet.objects.filter(user=self.context['request'].user).first()
        if not wallet:
            raise serializers.ValidationError("You do not have wallet please connect to admin.")
        if wallet.main_wallet_balance < data['amount']:
            raise serializers.ValidationError("Insufficient balance.")
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