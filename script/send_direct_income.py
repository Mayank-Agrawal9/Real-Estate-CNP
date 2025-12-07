import os, sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'real_estate.settings')

import django

django.setup()

from agency.models import Investment
from p2pmb.calculation import DistributeDirectCommission
from p2pmb.models import MLMTree


def distribute_direct_income():
    """
    Function to distribute direct income only if the previous job has completed.
    """
    try:
        print("🚀 Starting Direct Income Distribution...")
        investments = Investment.objects.filter(
            status='active', is_approved=True, pay_method='main_wallet', investment_type='p2pmb',
            send_direct_income=False, package__isnull=False
        ).order_by('id')[:5]
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
        print("🔄 Job finished. Ready for next execution.")


if __name__ == "__main__":
    distribute_direct_income()