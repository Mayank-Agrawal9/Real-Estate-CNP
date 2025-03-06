import os
from agency.models import Investment
from p2pmb.calculation import DistributeDirectCommission
from p2pmb.models import MLMTree


LOCK_FILE = "/tmp/distribute_direct_income.lock"


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

        investment_instance = Investment.objects.filter(
            status='active', is_approved=True, pay_method='main_wallet', investment_type='p2pmb',
            send_direct_income=False
        ).last()

        if investment_instance and investment_instance.user:
            instance = MLMTree.objects.filter(status='active', child=investment_instance.user).last()
            DistributeDirectCommission.distribute_p2pmb_commission(instance, investment_instance.amount)
            investment_instance.send_direct_income = True
            investment_instance.save()
            print("✅ Payment of Direct Income Distributed successfully.")

    finally:
        os.remove(LOCK_FILE)
        print("🔄 Job finished. Ready for next execution.")