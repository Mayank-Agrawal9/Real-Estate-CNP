import random
import os, sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'real_estate.settings')

import django

django.setup()


from django.contrib.auth.models import User
from agency.models import Investment
from accounts.helpers import generate_unique_referral_code
from accounts.models import Profile
from payment_app.models import UserWallet


def create_users_with_profiles_and_wallets():
    for i in range(1, 21):
        username = f"user{i}"
        email = f"user{i}@example.com"
        password = "password123"
        amount = random.randint(10000, 1000000)

        # Create User
        user, created = User.objects.get_or_create(username=username, defaults={'email': email})
        if created:
            user.set_password(password)
            user.save()
            referral_code = generate_unique_referral_code()
            Profile.objects.create(user=user, verified_by=user, referral_code=referral_code)
            UserWallet.objects.create(user=user, main_wallet_balance=amount)
            investment = Investment.objects.create(user=user, investment_type='p2pmb', amount=amount, gst=0)
            investment.package.set([1])
            print(f"Created: {username} | Profile | Wallet")

        else:
            print(f"User {username} already exists.")


if __name__ == "__main__":
    create_users_with_profiles_and_wallets()
