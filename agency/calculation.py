from datetime import datetime, date, timedelta
from decimal import Decimal

from agency.models import SuperAgency, Agency, FieldAgent, PPDAccount
from payment_app.models import UserWallet, Transaction


class CommissionCalculator:

    @staticmethod
    def calculate_direct_income(turnover):
        return turnover * Decimal(0.043)  # 4.30% of turnover

    @staticmethod
    def calculate_level_income(turnover):
        return turnover * Decimal(0.045)  # 4.50% of turnover for level income

    @staticmethod
    def calculate_lifetime_reward_income(turnover):
        # 40% for the first leg, 30% for the second, 20% for the third, 10% for the fourth leg
        reward = {
            'first_leg': turnover * Decimal(0.40),
            'second_leg': turnover * Decimal(0.30),
            'third_leg': turnover * Decimal(0.20),
            'fourth_leg': turnover * Decimal(0.10)
        }
        return reward

    @staticmethod
    def calculate_royalty_income(turnover):
        if turnover <= Decimal(1000000):
            return turnover * Decimal(0.01)  # Star Club
        elif turnover <= Decimal(2500000):
            return turnover * Decimal(0.015)  # 2-Star Club
        elif turnover <= Decimal(5000000):
            return turnover * Decimal(0.02)  # 3-Star Club
        elif turnover <= Decimal(10000000):
            return turnover * Decimal(0.025)  # 5-Star Club
        return Decimal(0)


class WithdrawalHandler:

    @staticmethod
    def calculate_withdrawal_charge(withdrawal_type, amount):
        if withdrawal_type == 'account':
            return amount * Decimal(0.10)  # 10% withdrawal charge for account withdrawal
        elif withdrawal_type == 'p2p':
            return amount * Decimal(0.05)  # 5% transaction fee for P2P
        return Decimal(0)

    @staticmethod
    def calculate_tds(amount):
        return amount * Decimal(0.05)  # 5% TDS deduction


def distribute_monthly_rent_for_super_agency():
    today = datetime.today().date()
    first_of_month = today.replace(day=1)

    if today != first_of_month:
        return "Today is not the first of the month. No distribution performed."

    super_agencies = SuperAgency.objects.filter(profile__is_kyc_verified=True, profile__is_kyc=True)

    for agency in super_agencies:
        user = agency.profile.user

        first_transaction = Transaction.objects.filter(
            receiver=user,
            transaction_type='rent',
            transaction_status='approved'
        ).order_by('verified_on').first()

        start_date = first_transaction.verified_on.date() if first_transaction else today
        end_date = start_date + timedelta(days=365 * 10)

        if not (start_date <= today <= end_date):
            print(f"Rent payment period has ended for {user.username}. No distribution performed.")
            continue

        rent_sent_this_month = Transaction.objects.filter(
            receiver=user,
            transaction_type='rent',
            verified_on__year=today.year,
            verified_on__month=today.month,
            transaction_status='approved'
        ).exists()

        if rent_sent_this_month:
            print(f"Rent already sent this month for {user.username}.")
            continue

        wallet, _ = UserWallet.objects.get_or_create(user=user)
        wallet.app_wallet_balance += 50000
        wallet.save()

        Transaction.objects.create(
            verified_on=today,
            receiver=user,
            amount=50000,
            transaction_type='rent',
            transaction_status='approved',
            remarks='Super Agency Rent Payment sent by CLICKNPAY REAL ESTATE.'
        )

    return "Monthly rent distributed successfully."


def distribute_monthly_rent_for_agency():
    today = datetime.today().date()
    first_of_month = today.replace(day=1)

    if today != first_of_month:
        return "Today is not the first of the month. No distribution performed."

    agencies = Agency.objects.filter(created_by__profile__is_kyc_verified=True, created_by__profile__is_kyc=True)

    for agency in agencies:
        user = agency.created_by

        first_transaction = Transaction.objects.filter(
            receiver=user,
            transaction_type='rent',
            transaction_status='approved'
        ).order_by('verified_on').first()

        start_date = first_transaction.verified_on.date() if first_transaction else today
        end_date = start_date + timedelta(days=365 * 10)

        if not (start_date <= today <= end_date):
            print(f"Rent payment period has ended for {user.username}. No distribution performed.")
            continue

        rent_sent_this_month = Transaction.objects.filter(
            receiver=user,
            transaction_type='rent',
            transaction_status='approved',
            verified_on__year=today.year,
            verified_on__month=today.month
        ).exists()

        if rent_sent_this_month:
            print(f"Rent already sent this month for {user.username}.")
            continue

        wallet, _ = UserWallet.objects.get_or_create(user=user)
        wallet.app_wallet_balance += 25000
        wallet.save()

        Transaction.objects.create(
            verified_on=today,
            receiver=user,
            amount=25000,
            transaction_type='rent',
            transaction_status='approved',
            remarks='Agency Rent Payment sent by CLICKNPAY REAL ESTATE'
        )

    return "Monthly rent distributed successfully."


def process_monthly_rentals():
    """
    Process monthly rentals for all active PPD accounts.
    The rental will be sent every month until the account is withdrawn or inactive.
    """
    today = date.today()
    active_accounts = PPDAccount.objects.filter(is_active=True)
    results = []

    for account in active_accounts:
        try:
            deposit_date = account.deposit_date
            months_since_deposit = (today.year - deposit_date.year) * 12 + (today.month - deposit_date.month)

            if months_since_deposit >= 0:
                monthly_rental = Decimal(account.amount_deposited) * Decimal('0.02')

                wallet, created = UserWallet.objects.get_or_create(user=account.user)
                wallet.app_wallet_balance += monthly_rental
                wallet.save()

                Transaction.objects.create(
                    receiver=account.user,
                    amount=monthly_rental,
                    transaction_type='interest',
                    transaction_status='approved',
                    remarks='Property Payment Deposit Interest Send by CNP'
                )

                results.append(
                    f"Monthly rental of ₹{monthly_rental} processed for {account.user.username}."
                )
        except Exception as e:
            results.append(f"Failed for {account.user.username}: {str(e)}")

    return results
