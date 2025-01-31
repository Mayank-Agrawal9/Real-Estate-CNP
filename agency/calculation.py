from datetime import datetime, date, timedelta
from decimal import Decimal

from django.db.models import Sum

from agency.models import SuperAgency, Agency, FieldAgent, PPDAccount, RewardEarned
from master.models import RewardMaster
from p2pmb.models import MLMTree
from payment_app.models import UserWallet, Transaction


class CommissionP2pmbCalculator:

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
                if account.has_purchased_property:
                    interest_rate = Decimal('0.01')
                else:
                    interest_rate = Decimal('0.02')

                monthly_rental = Decimal(account.amount_deposited) * interest_rate

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


def get_reward_based_on_turnover(turnover, role):
    """
    Fetches the reward for a given turnover based on the RewardMaster table.

    The reward is the one that has the highest turnover threshold that is less than or equal to
    the provided turnover.

    :param turnover: The total turnover for a user, agency, or super agency.
    :return: The RewardMaster object that matches the turnover threshold, or None if no match is found.
    """
    if turnover is None or turnover <= 0:
        return None
    reward = RewardMaster.objects.filter(turnover_threshold__lte=turnover, applicable_for=role).order_by(
        '-turnover_threshold').first()
    return reward


def calculate_super_agency_rewards():
    """Calculate and return the rewards for each SuperAgency."""
    super_agencies = SuperAgency.objects.prefetch_related(
        'profile',
        'profile__user',
        'agencies',
        'agencies__field_agents'
    ).annotate(
        total_agency_turnover=Sum('agencies__turnover'),
        total_field_agent_turnover=Sum('agencies__field_agents__turnover')
    )
    results = []

    for super_agency in super_agencies:
        total_turnover = super_agency.total_agency_turnover or 0
        total_turnover += super_agency.total_field_agent_turnover or 0
        role = super_agency.profile.role
        reward = get_reward_based_on_turnover(total_turnover, role)
        if reward:
            if not RewardEarned.objects.filter(user=super_agency.profile.user, reward=reward).exists():
                RewardEarned.objects.create(
                    user=super_agency.profile.user,
                    created_by=super_agency.profile.user,
                    reward=reward,
                    turnover_at_earning=total_turnover
                )
    return results


def calculate_agency_rewards():
    """Calculate and return the rewards for each SuperAgency."""
    agencies = Agency.objects.prefetch_related(
        'created_by',
        'created_by__profile',
        'field_agents'
    ).annotate(
        total_field_agent_turnover=Sum('field_agents__turnover')
    )
    results = []

    for agency in agencies:
        total_turnover = agency.total_field_agent_turnover or 0
        role = agency.created_by.profile.role
        reward = get_reward_based_on_turnover(total_turnover, role)
        if reward:
            if not RewardEarned.objects.filter(user=agency.created_by, reward=reward).exists():
                RewardEarned.objects.create(
                    user=agency.created_by,
                    created_by=agency.created_by,
                    reward=reward,
                    turnover_at_earning=total_turnover
                )
    return results


def calculate_field_agent_rewards():
    """Calculate and return the rewards for each SuperAgency."""
    field_agent = FieldAgent.objects.prefetch_related(
        'profile',
        'profile__user'
    )
    results = []

    for agent in field_agent:
        total_turnover = agent.turnover or 0
        role = agent.profile.role
        reward = get_reward_based_on_turnover(total_turnover, role)
        if reward:
            if not RewardEarned.objects.filter(user=agent.profile.user, reward=reward).exists():
                RewardEarned.objects.create(
                    user=agent.profile.user,
                    created_by=agent.profile.user,
                    reward=reward,
                    turnover_at_earning=total_turnover
                )
    return results



# def calculate_rewards(income):
#     """
#     Calculate specific rewards based on turnover.
#     """
#     reward_tiers = [
#         (500000, 1000, 10),
#         (1000000, 1000, 22),
#         (2500000, 2000, 25),
#         (5000000, 4000, 25),
#         (10000000, 6000, 25),
#         (25000000, 8000, 35),
#         (50000000, 10000, 60),
#         (100000000, 20000, 60),
#         (250000000, 50000, 60),
#         (500000000, 100000, 75),
#         (1000000000, 200000, 0)
#     ]
#     rewards = []
#     for turnover_threshold, monthly_income, months in reward_tiers:
#         if income >= turnover_threshold:
#             rewards.append({
#                 "turnover": turnover_threshold,
#                 "monthly_income": monthly_income,
#                 "months": months,
#                 "total_income": monthly_income * months if months > 0 else None,
#             })
#     return rewards

def calculate_p2pmb_rewards():
    """Calculate and return the rewards for each SuperAgency."""
    mlm_tree = MLMTree.objects.select_related('parent', 'child', 'parent__profile', 'child__profile')
    results = []

    for data in mlm_tree:
        total_turnover = data.turnover or 0
        role = data.child.role
        reward = get_reward_based_on_turnover(total_turnover, role)
        if reward:
            if not RewardEarned.objects.filter(user=data.child, reward=reward).exists():
                RewardEarned.objects.create(
                    user=data.child,
                    created_by=data.child,
                    reward=reward,
                    turnover_at_earning=total_turnover
                )
    return results