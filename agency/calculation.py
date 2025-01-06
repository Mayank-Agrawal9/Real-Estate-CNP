from datetime import datetime
from decimal import Decimal

from agency.models import SuperAgency
from payment_app.models import UserWallet


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
    today = datetime.today()
    first_of_month = today.replace(day=1)

    if today == first_of_month:
        super_agencies = SuperAgency.objects.filter(user__kyc__is_verified=True)

        for agency in super_agencies:
            wallet, created = UserWallet.objects.get_or_create(user=agency.user)
            wallet.app_wallet_balance += 50000
            wallet.save()

        return "Monthly rent distributed successfully."

    return "Today is not the first of the month. No distribution performed."


def distribute_monthly_rent_for_agency():
    today = datetime.today()
    first_of_month = today.replace(day=1)

    if today == first_of_month:
        super_agencies = SuperAgency.objects.filter(user__kyc__is_verified=True)

        for agency in super_agencies:
            wallet, created = Wallet.objects.get_or_create(user=agency.user)
            wallet.main_wallet_balance += agency.rent_per_month
            wallet.save()

        return "Monthly rent distributed successfully."

    return "Today is not the first of the month. No distribution performed."


def distribute_monthly_rent_for_field_agent():
    today = datetime.today()
    first_of_month = today.replace(day=1)

    if today == first_of_month:
        super_agencies = SuperAgency.objects.filter(user__kyc__is_verified=True)

        for agency in super_agencies:
            wallet, created = Wallet.objects.get_or_create(user=agency.user)
            wallet.main_wallet_balance += agency.rent_per_month
            wallet.save()

        return "Monthly rent distributed successfully."

    return "Today is not the first of the month. No distribution performed."
