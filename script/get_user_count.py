import os, sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'real_estate.settings')

import django

django.setup()

from agency.models import InvestmentInterest
from payment_app.models import UserWallet


def create_users_with_profiles_and_wallets():
    investments = InvestmentInterest.objects.filter(interest_send_date='2025-07-01')
    success_count = 0
    failure_count = 0
    errors = []
    for investment in investments:
        user = investment.created_by
        amount = investment.interest_amount

        try:
            wallet = UserWallet.objects.filter(user=user).last()

            if wallet.app_wallet_balance < amount:
                errors.append(f"Insufficient balance for user {user.id}")
                failure_count += 1
                continue

            wallet.app_wallet_balance -= amount
            wallet.save()
            investment.delete()
            success_count += 1

        except Exception as e:
            print(e)
            errors.append(f"Failed for user {user.id}: {str(e)}")
            failure_count += 1


if __name__ == "__main__":
    create_users_with_profiles_and_wallets()