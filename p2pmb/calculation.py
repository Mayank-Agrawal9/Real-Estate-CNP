import datetime
from decimal import Decimal

from django.db import transaction

from p2pmb.helpers import create_transaction_entry, create_commission_entry
from p2pmb.models import MLMTree, ScheduledCommission, Commission, Reward, RoyaltyClub
from payment_app.models import Transaction, UserWallet


# def calculate_level_income(instance, amount):
#     """
#     Calculate level income for 30 levels.
#     """
#     level_income = Decimal(0.0)
#     current_node = instance
#     for i in range(30):
#         if current_node.parent:
#             if i < 20:
#                 level_income += current_node.turnover * Decimal(0.0015)
#             else:
#                 level_income += current_node.turnover * Decimal(0.0015)
#             current_node = current_node.parent
#         else:
#             break
#     return level_income

# Distribute Direct Income
class DistributeDirectCommission:
    @staticmethod
    def distribute_p2pmb_commission(profile_instance, amount):
        if not profile_instance or not amount:
            return

        instant_commission = Decimal(amount) * Decimal('0.03')
        monthly_commission = Decimal(amount) * Decimal('0.0015')
        referral_by = profile_instance.referral_by

        with transaction.atomic():
            if referral_by:
                # Process referral commission
                DistributeDirectCommission.process_referral_commission(referral_by, profile_instance.child,
                                                                       instant_commission)

                # Process parent commission if exists
                if profile_instance.parent:
                    DistributeDirectCommission.process_parent_commission(profile_instance.parent,
                                                                         profile_instance.child, monthly_commission)

                # Schedule monthly payments for 9 months
                DistributeDirectCommission.schedule_monthly_payments(profile_instance.child, profile_instance.parent,
                                                                     monthly_commission)

            else:
                # Handle case where there is no referral
                DistributeDirectCommission.handle_no_referral(profile_instance, instant_commission, monthly_commission)

            profile_instance.send_direct_income = True
            profile_instance.save()

    @staticmethod
    def process_referral_commission(referral_by, child, instant_commission):
        referral_user_wallet = UserWallet.objects.filter(user=referral_by, status='active').last()
        if referral_user_wallet:
            referral_user_wallet.app_wallet_balance += instant_commission
            referral_user_wallet.save()

            DistributeDirectCommission.create_commission_entry(
                referral_by, child, 'direct', instant_commission,
                f'Direct Commission Added while adding {child.username}')

            DistributeDirectCommission.create_transaction_entry(
                referral_by, referral_by, instant_commission, 'commission', 'approved',
                f'Direct Commission Added while adding {child.username}')

    @staticmethod
    def process_parent_commission(parent, child, monthly_commission):
        regular_leader_wallet = UserWallet.objects.filter(user=parent, status='active').last()
        if regular_leader_wallet:
            regular_leader_wallet.app_wallet_balance += monthly_commission
            regular_leader_wallet.save()

            DistributeDirectCommission.create_commission_entry(
                parent, child, 'direct', monthly_commission,
                f'Direct Commission Added while adding {child.username}')

            DistributeDirectCommission.create_transaction_entry(
                child, parent, monthly_commission, 'commission',
                'approved', f'Direct Commission Added while adding {child.username}')

    @staticmethod
    def handle_no_referral(profile_instance, instant_commission, monthly_commission):
        top_user = MLMTree.objects.filter(parent=None).first()
        if top_user:
            top_user.app_wallet_balance += instant_commission
            top_user.commission_earned += instant_commission
            top_user.save()

            DistributeDirectCommission.create_commission_entry(
                top_user.child, profile_instance.child, 'direct', instant_commission,
                f'Direct Commission Added while adding {profile_instance.child.username}')

            DistributeDirectCommission.create_transaction_entry(
                profile_instance.child, top_user.child, instant_commission, 'commission',
                'approved', f'Direct Commission Added while adding {profile_instance.child.username}')

            if profile_instance.parent:
                DistributeDirectCommission.process_parent_commission(profile_instance.parent, profile_instance.child,
                                                                     monthly_commission)

    @staticmethod
    def create_commission_entry(created_by, commission_by, commission_type, amount, description):
        Commission.objects.create(
            created_by=created_by,
            commission_by=commission_by,
            commission_to=created_by,
            commission_type=commission_type,
            amount=amount,
            description=description
        )

    @staticmethod
    def create_transaction_entry(created_by, receiver, amount, transaction_type,
                                  transaction_status, remarks):
        Transaction.objects.create(
            created_by=created_by,
            sender=created_by,
            receiver=receiver,
            amount=amount,
            transaction_type=transaction_type,
            transaction_status=transaction_status,
            payment_method='wallet',
            remarks=remarks,
            verified_on=datetime.datetime.now()
        )

    @staticmethod
    def schedule_monthly_payments(child, parent, monthly_amount):
        for month in range(1, 10):
            DistributeDirectCommission.schedule_payment(child, parent, monthly_amount, month)

    @staticmethod
    def schedule_payment(sender, user, amount, months_ahead):
        scheduled_date = datetime.datetime.now() + datetime.timedelta(days=31 * months_ahead)
        ScheduledCommission.objects.create(created_by=user, send_by=sender, user=user, amount=amount,
                                           scheduled_date=scheduled_date)

    @staticmethod
    def cron_send_monthly_payment_direct_income():
        schedule_commission_instance = ScheduledCommission.objects.filter(scheduled_date__date=datetime.datetime.today(),
                                                                          is_paid=False)
        for income in schedule_commission_instance:
            user_wallet = UserWallet.objects.filter(user=income.user, status='active').last()
            if not user_wallet:
                continue

            user_wallet.app_wallet_balance += income.amount
            user_wallet.save()

            DistributeDirectCommission.create_commission_entry(
                income.user, income.send_by, 'direct', income.amount,
                f'Direct Commission Monthly Installment Added while adding {income.send_by.username}')

            DistributeDirectCommission.create_transaction_entry(
                income.user, income.user, income.amount, 'commission', 'approved',
                f'Direct Commission Monthly Installment Added while adding {income.send_by.username}')

            income.is_paid = True
            income.save()


# Distribute Level Income
class DistributeLevelIncome:
    @staticmethod
    def distribute_level_income(instance, amount):
        """
        Distribute level income over 30 levels:
        - 0.15% for 20 levels above the user
        - 0.15% for 10 levels below the user
        - Remaining amount goes to the top node if levels are not complete.
        """
        level_above_percent = Decimal(0.0015)
        level_below_percent = Decimal(0.0015)

        # Distribute to 20 levels above
        remaining_above = DistributeLevelIncome.distribute_to_levels_above(
            instance, amount, level_above_percent, 20
        )

        # Distribute to 10 levels below
        remaining_below = DistributeLevelIncome.distribute_to_levels_below(
            instance, amount, level_below_percent, 10
        )

        # Send remaining amounts to the top node
        instance.send_level_income = True
        instance.save()
        top_node = MLMTree.objects.filter(parent=None).first()
        if top_node:
            total_remaining = remaining_above + remaining_below
            wallet = UserWallet.objects.filter(user=top_node.child, status='active').last()
            wallet.app_wallet_balance += total_remaining
            wallet.save()
            top_node.commission_earned += total_remaining
            wallet.save()

            # Create transaction record for this distribution
            create_transaction_entry(
                instance.child, top_node, total_remaining, 'commission', 'approved',
                f'Level Commission added by adding {instance.child.get_full_name()}')

            # Create commission record
            create_commission_entry(top_node, instance.child, 'level', total_remaining,
                                    f'Commission added for {instance.child.get_full_name()}')

    @staticmethod
    def distribute_to_levels_above(user, amount, percent, max_levels):
        """
        Distribute commission to levels above the user.
        Returns the remaining amount if fewer levels are available.
        """
        current_user = user.parent
        base_user = user
        distributed_levels = 0
        commission = Decimal(amount) * percent

        while distributed_levels < max_levels:
            parent = MLMTree.objects.filter(child=current_user).first()

            if not parent or not parent.parent:
                break

            for child in parent:
                # Update parent wallet balance
                parent_wallet = UserWallet.objects.filter(user=child.parent, status='active')
                if parent_wallet:
                    parent_wallet.app_wallet_balance += commission
                    parent_wallet.save()

                # Create transaction record for this distribution
                create_transaction_entry(
                    base_user.child, child.parent, commission, 'commission', 'approved',
                    f'Level Commission added by adding {base_user.child.get_full_name()}')

                # Create commission record
                create_commission_entry(child.parent, base_user.child, 'level', commission,
                                        f'Commission added for {base_user.child.get_full_name()}')

                current_user = parent.parent
                distributed_levels += 1

        remaining_levels = max_levels - distributed_levels
        return Decimal(amount) * percent * Decimal(remaining_levels)

    @staticmethod
    def distribute_to_levels_below(user, amount, percent, max_levels):
        """
        Distribute commission to levels below the user.
        Returns the remaining amount if fewer levels are available.
        """
        current_user = user.child
        base_user = user
        distributed_levels = 0
        commission = Decimal(amount) * percent

        while distributed_levels < max_levels:
            # Get all children of the current user
            children = MLMTree.objects.filter(parent=current_user, status='active')

            if not children.exists():
                break

            for child in children:
                # Update child's wallet balance
                child_wallet = UserWallet.objects.filter(user=child.child, status='active').last()
                if child_wallet:
                    child_wallet.app_wallet_balance += commission
                    child_wallet.save()

                # Create transaction record for this distribution
                create_transaction_entry(
                    base_user.child, child.child, commission, 'commission', 'approved',
                    f'Level Commission added by {base_user.child.get_full_name()}'
                )

                # Create commission record
                create_commission_entry(child.child, base_user.child, 'level', commission,
                                        f'Commission added for {base_user.child.get_full_name()}')

                distributed_levels += 1

                # Break if we have reached the maximum levels to distribute
                if distributed_levels >= max_levels:
                    break

            current_user = children.first().child

        remaining_levels = max_levels - distributed_levels
        return Decimal(amount) * percent * Decimal(remaining_levels)


def calculate_lifetime_reward_income_task():
    """
    Celery task to calculate and award lifetime reward income based on turnover.
    """
    persons = MLMTree.objects.filter(status='active')
    for person in persons:
        turnover = int(person.turnover)
        if turnover >= 500000000:
            reward_type = 'blue_sapphire'
        elif turnover >= 250000000:
            reward_type = 'commander'
        elif turnover >= 100000000:
            reward_type = 'relic'
        elif turnover >= 50000000:
            reward_type = 'almighty'
        elif turnover >= 25000000:
            reward_type = 'conqueron'
        elif turnover >= 10000000:
            reward_type = 'titan'
        elif turnover >= 5000000:
            reward_type = 'diamond'
        elif turnover >= 2500000:
            reward_type = 'gold'
        elif turnover >= 1000000:
            reward_type = 'silver'
        elif turnover >= 500000:
            reward_type = 'star'
        else:
            continue

        try:
            reward = Reward.objects.filter(person=person, reward_type=reward_type).last()
            if reward:
                continue
        except Exception as e:
            continue
        if reward_type == 'star':
            monthly_payment = 1000
            months_duration = 10
        elif reward_type == 'silver':
            monthly_payment = 1000
            months_duration = 22
        elif reward_type == 'gold':
            monthly_payment = 2000
            months_duration = 25
        elif reward_type == 'diamond':
            monthly_payment = 4000
            months_duration = 25
        elif reward_type == 'titan':
            monthly_payment = 6000
            months_duration = 25
        elif reward_type == 'conqueron':
            monthly_payment = 8000
            months_duration = 35
        elif reward_type == 'almighty':
            monthly_payment = 10000
            months_duration = 60
        elif reward_type == 'relic':
            monthly_payment = 20000
            months_duration = 60
        elif reward_type == 'commander':
            monthly_payment = 50000
            months_duration = 60
        elif reward_type == 'blue_sapphire':
            monthly_payment = 100000
            months_duration = 75
        else:
            print("Invalid reward type")
            continue

        Reward.objects.create(
            person=person,
            reward_type=reward_type,
            turnover_required=turnover,
            monthly_payment=monthly_payment,
            months_duration=months_duration,
            achieved_date=datetime.datetime.now()
        )
        print(f"Created {reward_type} reward for {person.user.username}.")


def process_monthly_reward_payments():
    """
    Celery task to process monthly reward payments and update relevant fields.
    """
    today = datetime.datetime.today()
    rewards = Reward.objects.filter(status='active')

    for reward in rewards:
        person = reward.person

        if reward.last_payment_send is None or reward.last_payment_send < today and reward.months_duration > 0:
            transfer_to_wallet(person, reward.monthly_payment)
            reward.last_payment_send = today
            reward.months_duration -= 1
            reward.save()
            print(f"Reward payment processed for {person.username} - {reward.reward_type}. "
                  f"Remaining months: {reward.months_duration}")
        else:
            print(f"Reward payment already sent for {person.username} - {reward.reward_type} this month.")


def transfer_to_wallet(person, amount):

    """
    This function to simulate transferring the amount to the user's wallet.
    Replace this with your actual wallet transfer logic.
    """
    user_wallet = UserWallet.objects.filter(user=person.child).last()
    user_wallet.app_wallet_balance += amount
    user_wallet.save()
    if person and person.parent:
        get_mlm = MLMTree.objects.filter(status='active', child=person.parent).last()
        get_mlm.commission_earned += amount
        get_mlm.save()
        Transaction.objects.create(
            created_by=person.child,
            sender=person.child,
            receiver=person.child,
            amount=amount,
            transaction_type='commission',
            transaction_status='approved',
            payment_method='wallet'
        )
    Transaction.objects.create(
        created_by=person.child,
        sender=person.child,
        receiver=person.child,
        amount=amount,
        transaction_type='commission',
        transaction_status='approved',
        payment_method='wallet'
    )
    Commission.objects.create(
        commission_by__id=1,
        commission_to=person.child,
        commission_type='reward',
        amount=amount,
        description=f'Commission Added while adding {person.username}'
    )


def check_royalty_club_membership():
    """
    Check and assign royalty club membership based on defined criteria.
    """
    persons = MLMTree.objects.filter(status='active')
    for person in persons:
        direct_ids_count = MLMTree.objects.filter(referral_by=person.child).count()
        team_count_level_one = MLMTree.objects.filter(parent=person.child).count()
        team_count_level_two = MLMTree.objects.filter(
            parent__in=MLMTree.objects.filter(parent=person.child).values_list('child', flat=True)).count()

        if direct_ids_count >= 10:
            RoyaltyClub.objects.get_or_create(person=person, club_type='star', turnover_limit=1000000,
                                              direct_ids_required=10, level_one_required=0, level_two_required=0,
                                              gifts_value=1000000)

        if direct_ids_count >= 10 and team_count_level_one >= 5 and team_count_level_two >= 25:
            RoyaltyClub.objects.get_or_create(person=person, club_type='2_star', turnover_limit=2500000,
                                              direct_ids_required=10, level_one_required=5, level_two_required=25,
                                              gifts_value=5000000)

        if team_count_level_one >= 25 and team_count_level_two >= 125:
            RoyaltyClub.objects.get_or_create(person=person, club_type='3_star', turnover_limit=5000000,
                                              direct_ids_required=5, level_one_required=5, level_two_required=25,
                                              gifts_value=5000000)

        if team_count_level_one >= 100 and team_count_level_two >= 500:
            RoyaltyClub.objects.get_or_create(person=person, club_type='5_star', turnover_limit=10000000,
                                              direct_ids_required=10, level_one_required=5, level_two_required=25,
                                              gifts_value=10000000)