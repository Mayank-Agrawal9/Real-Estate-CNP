import os, sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'real_estate.settings')

import django

django.setup()

from p2pmb.models import Commission, ScheduledCommission, MLMTree
from payment_app.models import UserWallet

# def create_users_with_profiles_and_wallets():
#     investments = InvestmentInterest.objects.filter(interest_send_date='2025-07-01')
#     success_count = 0
#     failure_count = 0
#     errors = []
#     for investment in investments:
#         user = investment.created_by
#         amount = investment.interest_amount
#
#         try:
#             wallet = UserWallet.objects.filter(user=user).last()
#
#             if wallet.app_wallet_balance < amount:
#                 errors.append(f"Insufficient balance for user {user.id}")
#                 failure_count += 1
#                 continue
#
#             wallet.app_wallet_balance -= amount
#             wallet.save()
#             investment.delete()
#             success_count += 1
#
#         except Exception as e:
#             print(e)
#             errors.append(f"Failed for user {user.id}: {str(e)}")
#             failure_count += 1


def revert_monthly_interest():
    investments = Commission.objects.filter(commission_type='direct', date_created__date='2025-07-01')
    success_count = 0
    failure_count = 0
    errors = []
    for investment in investments:
        user = investment.commission_to
        amount = investment.amount

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


# def schedule_commission_revert():
#     get_schedule_commission = ScheduledCommission.objects.filter(scheduled_date='2025-07-01')
#     for data in get_schedule_commission:
#         Transaction

def update_schedule_commission():
    commission = ScheduledCommission.objects.filter(send_by__isnull=False)
    for data in commission:
        get_mlm = MLMTree.objects.filter(child=data.send_by).last()
        if get_mlm and get_mlm.referral_by:
            data.user = get_mlm.referral_by
            data.save()


if __name__ == "__main__":
    # create_users_with_profiles_and_wallets()
    # ProcessMonthlyInterestP2PMB.generate_interest_for_all_investments()
    update_schedule_commission()