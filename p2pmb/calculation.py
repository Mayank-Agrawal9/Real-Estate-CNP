import datetime
from decimal import Decimal

from django.db import transaction

from p2pmb.models import MLMTree, ScheduledCommission, Commission, Reward, RoyaltyClub
from payment_app.models import Transaction, UserWallet


def send_direct_income(amount):
    """
    Calculate direct income and send 3% instance to their parent.
    """
    direct_income = MLMTree.objects.filter(parent__is_null=False, status='active')
    for income in direct_income:
        calculated_income = direct_income * Decimal(0.03)
        income.commission_earned += calculated_income
        income.save()
        parent_wallet = UserWallet.objects.filter(user=income.parent).last()
        parent_wallet.app_wallet_balance += calculated_income
        parent_wallet.save()
        Transaction.objects.create(
            created_by=income.parent,
            sender=income.parent,
            amount=calculated_income,
            transaction_type='commission',
            transaction_status='approved'
        )


def calculate_level_income(instance, amount):
    """
    Calculate level income for 30 levels.
    """
    level_income = Decimal(0.0)
    current_node = instance
    for i in range(30):
        if current_node.parent:
            if i < 20:
                level_income += current_node.turnover * Decimal(0.0015)
            else:
                level_income += current_node.turnover * Decimal(0.0015)
            current_node = current_node.parent
        else:
            break
    return level_income


def distribute_p2pmb_commission(profile_instance, amount):
    if not profile_instance or not amount:
        return

    instant_commission = Decimal(amount) * Decimal('0.03')
    monthly_commission = Decimal(amount) * Decimal('0.015')
    referral_by = profile_instance.referral_by

    with transaction.atomic():
        if referral_by:
            referral_user_wallet = UserWallet.objects.filter(user=referral_by, status='active').last()
            if referral_user_wallet:
                referral_user_wallet.app_wallet_balance += instant_commission
                referral_user_wallet.save()

                Commission.objects.create(
                    created_by=profile_instance.user,
                    commission_by=profile_instance.user,
                    commission_to=profile_instance.user,
                    commission_type='direct',
                    amount=instant_commission,
                    description=f'Commission Added while adding {profile_instance.child.username}'
                )

                Transaction.objects.create(
                    created_by=referral_user_wallet.user,
                    sender=referral_user_wallet.user,
                    receiver=referral_user_wallet.user,
                    amount=instant_commission,
                    transaction_type='commission',
                    transaction_status='approved',
                    remarks=f'Commission Added while adding {profile_instance.child.username}'
                )

                if profile_instance.parent:
                    regular_leader_wallet = UserWallet.objects.filter(user=profile_instance.parent, status='active').last()
                    if regular_leader_wallet:
                        regular_leader_wallet.app_wallet_balance += monthly_commission
                        regular_leader_wallet.save()

                        Commission.objects.create(
                            created_by=profile_instance.user,
                            commission_by=profile_instance.user,
                            commission_to=profile_instance.user,
                            commission_type='direct',
                            amount=monthly_commission,
                            description=f'Commission Added while adding {profile_instance.child.username}'
                        )

                        Transaction.objects.create(
                            created_by=regular_leader_wallet.user,
                            sender=regular_leader_wallet.user,
                            receiver=profile_instance.parent,
                            amount=monthly_commission,
                            transaction_type='commission',
                            transaction_status='approved',
                            remarks=f'Commission Added while adding {profile_instance.child.username}'
                        )

            for month in range(1, 10):
                schedule_payment(profile_instance.parent, monthly_commission, month)
        else:
            top_user = MLMTree.objects.filter(parent=None).first()
            if top_user:
                top_user.app_wallet_balance += instant_commission
                top_user.commission_earned += instant_commission
                top_user.save()

                Commission.objects.create(
                    created_by=profile_instance.user,
                    commission_by=profile_instance.user,
                    commission_to=profile_instance.user,
                    commission_type='direct',
                    amount=instant_commission,
                    description=f'Commission Added while adding {profile_instance.child.username}'
                )

                Transaction.objects.create(
                    created_by=profile_instance.child,
                    sender=profile_instance.child,
                    receiver=top_user.child,
                    amount=instant_commission,
                    transaction_type='commission',
                    transaction_status='approved',
                    remarks=f'Commission Added while adding {profile_instance.child.username}'
                )

                if profile_instance.parent:
                    parent_wallet = UserWallet.objects.filter(user=profile_instance.parent, status='active').last()
                    if parent_wallet:
                        parent_wallet.app_wallet_balance += monthly_commission
                        parent_wallet.save()

                        Commission.objects.create(
                            created_by=profile_instance.user,
                            commission_by=profile_instance.user,
                            commission_to=profile_instance.user,
                            commission_type='direct',
                            amount=monthly_commission,
                            description=f'Commission Added while adding {profile_instance.child.username}'
                        )

                        Transaction.objects.create(
                            created_by=profile_instance.child,
                            sender=profile_instance.child,
                            receiver=profile_instance.parent,
                            amount=monthly_commission,
                            transaction_type='commission',
                            transaction_status='approved',
                            remarks=f'Commission Added while adding {profile_instance.child.username}'
                        )
                for month in range(1, 10):
                    schedule_payment(top_user, monthly_commission, month)


def schedule_payment(sender, user, amount, months_ahead):
    scheduled_date = datetime.datetime.now() + datetime.timedelta(days=30 * months_ahead)
    ScheduledCommission.objects.create(created_by=user, send_by=sender, user=user, amount=amount,
                                       scheduled_date=scheduled_date)

# Distribute Level Income


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
    remaining_above = distribute_to_levels_above(instance, amount, level_above_percent, 20)

    # Distribute to 10 levels below
    remaining_below = distribute_to_levels_below(instance, amount, level_below_percent, 10)

    # Send remaining amounts to the top node
    top_node = MLMTree.objects.filter(parent=None).first()
    if top_node:
        total_remaining = remaining_above + remaining_below
        wallet = UserWallet.objects.filter(user=top_node.child, status='active').last()
        wallet.app_wallet_balance += total_remaining
        wallet.save()
        top_node.commission_earned += total_remaining
        wallet.save()
        Transaction.objects.create(
            created_by=instance.child, sender=instance.child, receiver=top_node.child, amount=total_remaining,
            transaction_type='commission', transaction_status='approved',
            remarks=f'Commission Added while added {instance.child.username}'
        )

        Commission.objects.create(
            created_by=instance.child, commission_by=instance.child, commission_to=top_node.child,
            commission_type='level', amount=amount,
            description=f'Commission Added while added {instance.child.get_full_name()}'
        )


def distribute_to_levels_above(user, amount, percent, max_levels):
    """
    Distribute commission to levels above the user.
    Returns the remaining amount if fewer levels are available.
    """
    current_user = user.child
    distributed_levels = 0

    while distributed_levels < max_levels:
        parent = MLMTree.objects.filter(child=current_user).first()
        if not parent or not parent.parent:
            break
        wallet = UserWallet.objects.filter(user=parent.parent, status='active').last()
        commission = Decimal(amount) * percent
        wallet.app_wallet_balance += commission
        wallet.app_wallet_balance += commission
        wallet.save()
        parent.parent.save()

        current_user = parent.parent
        distributed_levels += 1
        Transaction.objects.create(
            created_by=parent.parent, sender=parent.parent, receiver=parent.parent, amount=commission, transaction_type='commission',
            transaction_status='approved', remarks=f'Commission Added while added {current_user.get_full_name()}'
        )
        Commission.objects.create(
            created_by=parent.parent, commission_by=parent.parent, commission_to=parent.parent, commission_type='level',
            amount=amount, description=f'Commission Added while added {current_user.get_full_name()}'
        )

    remaining_levels = max_levels - distributed_levels
    return Decimal(amount) * percent * Decimal(remaining_levels)


def distribute_to_levels_below(user, amount, percent, max_levels):
    """
    Distribute commission to levels below the user.
    Returns the remaining amount if fewer levels are available.
    """
    children = MLMTree.objects.filter(parent=user.child)
    remaining_levels = max_levels
    next_level_children = list(children)
    distributed_levels = 0

    while next_level_children and remaining_levels > 0:
        current_level_commission = Decimal(amount) * percent
        next_level_children = []
        wallet = UserWallet.objects.filter(user=children.parent, status='active').last()

        for child_entry in children:
            child = child_entry.child
            child.wallet.app_wallet_balance += current_level_commission
            child.wallet.save()
            next_level_children.extend(MLMTree.objects.filter(parent=child))
            Transaction.objects.create(
                created_by=child.parent, sender=child.parent, receiver=child, amount=current_level_commission,
                transaction_type='commission', transaction_status='approved',
                remarks=f'Commission Added while added {wallet.user.get_full_name()}'
            )
            Commission.objects.create(
                created_by=child.parent, commission_by=child.parent, commission_to=child, commission_type='level',
                amount=amount, description=f'Commission Added while added {child.get_full_name()}'
            )

        remaining_levels -= 1
        distributed_levels += 1

    return Decimal(amount) * percent * Decimal(remaining_levels)


def calculate_lifetime_reward_income_task():
    """
    Celery task to calculate and award lifetime reward income based on turnover.
    """
    persons = MLMTree.objects.filter(status='active')
    for person in persons:
        turnover = person.turnover
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
            return

        try:
            reward = Reward.objects.filter(person=person, reward_type=reward_type).last()
            if reward:
                continue
        except Exception as e:
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
                return

            Reward.objects.create(
                person=person,
                reward_type=reward_type,
                turnover_required=turnover,
                monthly_payment=monthly_payment,
                months_duration=months_duration,
                achieved_date=datetime.datetime.now()
            )
            print(f"Created {reward_type} reward for {person.user.username}.")
        except Exception as e:
            print(f"An error occurred: {e}")


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
            print(f"Reward payment processed for {person.user.username} - {reward.reward_type}. "
                  f"Remaining months: {reward.months_duration}")
        else:
            print(f"Reward payment already sent for {person.user.username} - {reward.reward_type} this month.")


def transfer_to_wallet(person, amount):

    """
    This function to simulate transferring the amount to the user's wallet.
    Replace this with your actual wallet transfer logic.
    """
    user_wallet = UserWallet.objects.filter(user=person).last()
    user_wallet.app_wallet_balance += amount
    user_wallet.save()
    person.parent_relation.commission_earned += amount
    person.parent_relation.save()
    Transaction.objects.create(
        created_by=person,
        sender=person,
        receiver=person,
        amount=amount,
        transaction_type='commission',
        transaction_status='approved',
        payment_method='wallet'
    )
    Commission.objects.create(
        commission_by__id=1,
        commission_to=person,
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