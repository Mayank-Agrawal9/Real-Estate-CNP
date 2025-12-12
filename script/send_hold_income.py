import os, sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'real_estate.settings')

import django

django.setup()

from django.db import transaction
from p2pmb.models import HoldLevelIncome, MLMTree, Commission
from django.utils import timezone
from p2pmb.helpers import create_transaction_entry
from payment_app.models import UserWallet


def send_hold_income():
    total_processed = 0

    incomes = HoldLevelIncome.objects.filter(
        status='active', release_status='on_hold'
    ).select_related('commission_by', 'commission_to')

    with transaction.atomic():
        for income in incomes:
            direct_count = MLMTree.objects.filter(
                status='active', is_show=True, referral_by=income.commission_to
            ).count()

            if direct_count >= income.direct_user_required:
                username = income.commission_by.username if income.commission_by else 'Unknown'
                Commission.objects.create(
                    created_by=income.commission_by, commission_by=income.commission_by,
                    commission_to=income.commission_to, commission_type='level', amount=income.amount,
                    level_type=income.level_type, description=f'Commission added for {username}'
                )
                create_transaction_entry(
                    income.commission_by, income.commission_to, income.amount, 'commission',
                    'approved',
                    f'Level Commission added by adding {income.commission_by.username}')

                wallet, _ = UserWallet.objects.get_or_create(user=income.commission_to)
                wallet.app_wallet_balance += income.amount
                wallet.save()

                income.release_status = 'release'
                income.date_updated = timezone.now()
                income.released_date = timezone.now()
                income.save()
                total_processed += 1

    print(f"Successfully processed {total_processed} hold-level incomes.")


if __name__ == "__main__":
    send_hold_income()