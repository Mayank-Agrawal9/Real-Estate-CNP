import os
from agency.models import Investment
from p2pmb.calculation import DistributeDirectCommission, DistributeLevelIncome
from p2pmb.models import MLMTree


LOCK_FILE = "/tmp/distribute_direct_income.lock"
LOCK_LEVEL_INCOME_FILE = "/tmp/distribute_level_income.lock"


def distribute_direct_income():
    """
    Function to distribute direct income only if the previous job has completed.
    """
    if os.path.exists(LOCK_FILE):
        print("🔴 Previous job is still running. Skipping this execution.")
        return

    try:
        open(LOCK_FILE, "w").close()
        print("🚀 Starting Direct Income Distribution...")

        investments = Investment.objects.filter(
            status='active', is_approved=True, pay_method='main_wallet', investment_type='p2pmb',
            send_direct_income=False
        ).order_by('id')
        for investment_instance in investments:
            if investment_instance and investment_instance.user:
                instance = MLMTree.objects.filter(status='active', child=investment_instance.user).last()
                if instance:
                    DistributeDirectCommission.distribute_p2pmb_commission(instance, investment_instance.amount)
                    investment_instance.send_direct_income = True
                    investment_instance.save()
                    print("✅ Payment of Direct Income Distributed successfully.")
                else:
                    print(f"{instance.user.username} is not enroll in MLM yet.")

    finally:
        os.remove(LOCK_FILE)
        print("🔄 Job finished. Ready for next execution.")


def distribute_level_income():
    """
    Function to distribute level income only if the previous job has completed.
    """
    if os.path.exists(LOCK_LEVEL_INCOME_FILE):
        print("🔴 Previous job is still running. Skipping this execution.")
        return

    try:
        open(LOCK_LEVEL_INCOME_FILE, "w").close()
        print("🚀 Starting Direct Income Distribution...")

        investments = Investment.objects.filter(status='active', is_approved=True, pay_method='main_wallet', investment_type='p2pmb', send_level_income=False)
        for investment_instance in investments:

            if investment_instance and investment_instance.user:
                instance = MLMTree.objects.filter(status='active', child=investment_instance.user).last()
                if instance:
                    amount = investment_instance.amount if investment_instance.amount else 0
                    DistributeLevelIncome.distribute_level_income(instance, amount)
                    investment_instance.send_level_income = True
                    investment_instance.save()
                    print(f"✅ Payment of Direct Income Distributed successfully of user "
                          f"{investment_instance.user.username}.")
                else:
                    print(f"{investment_instance.user.username} is not enroll in MLM yet.")

    finally:
        os.remove(LOCK_LEVEL_INCOME_FILE)
        print("🔄 Job finished. Ready for next execution.")