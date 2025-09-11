import os, sys
from decimal import Decimal, ROUND_HALF_UP

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'real_estate.settings')

import django
from django.db.models import Sum, F

django.setup()

from payment_app.models import Transaction, UserWallet


def fix_tds_amount():
    transactions = Transaction.objects.filter(transaction_status='approved', transaction_type='transfer',
                                              status='active', sender=F("receiver"))
    for tx in transactions:
        final_amount = (tx.amount / Decimal('0.9')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        tx.tds_amount = (final_amount * Decimal('0.05')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        tx.taxable_amount = (final_amount * Decimal('0.10')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        tx.save(update_fields=['tds_amount', 'taxable_amount'])


def update_wallet_tds_amount():
    transactions = Transaction.objects.filter(
        transaction_status='approved', transaction_type='transfer', status='active', sender=F("receiver")
    )

    sender_tds = transactions.values('sender').annotate(total_tds=Sum('tds_amount'))

    for record in sender_tds:
        sender_id = record['sender']
        total_tds = record['total_tds'] or 0

        try:
            wallet = UserWallet.objects.filter(user=sender_id).last()
            wallet.tds_amount = total_tds
            wallet.admin_amount = total_tds * 2
            wallet.save(update_fields=['tds_amount', 'admin_amount'])
        except Exception as e:
            print(f"Wallet not found for sender {sender_id}, error is {e}")


if __name__ == "__main__":
    fix_tds_amount()
    update_wallet_tds_amount()