import os, sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'real_estate.settings')

import django

django.setup()

from agency.models import Investment
from p2pmb.calculation import DistributeLevelIncome
from p2pmb.helpers import get_level_counts
from p2pmb.models import MLMTree


def distribute_level_income():
    """
    Function to distribute level income only if the previous job has completed.
    """
    try:
        print("🚀 Starting Direct Income Distribution...")

        investments = Investment.objects.filter(status='active', is_approved=True, pay_method='main_wallet',
                                                investment_type='p2pmb', send_level_income=False,
                                                package__isnull=False).order_by('date_created')
        for investment_instance in investments:
            if investment_instance and investment_instance.user:
                instance = MLMTree.objects.filter(status='active', child=investment_instance.user).last()
                direct_count = MLMTree.objects.filter(status='active', referral_by=instance.referral_by).count()
                up_level, down_level = get_level_counts(direct_count)
                if instance and up_level and down_level:
                    amount = investment_instance.amount if investment_instance.amount else 0
                    DistributeLevelIncome.distribute_level_income(instance, amount, up_level, down_level)
                    investment_instance.send_level_income = True
                    investment_instance.save()
                    print(f"✅ Payment of Direct Income Distributed successfully of user "
                          f"{investment_instance.user.username}.")
                else:
                    print(f"{investment_instance.user.username} is not enroll in MLM yet.")

    finally:
        print("🔄 Job finished. Ready for next execution.")


if __name__ == "__main__":
    distribute_level_income()