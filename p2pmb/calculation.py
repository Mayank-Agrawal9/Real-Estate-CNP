import datetime
from decimal import Decimal

from p2pmb.models import MLMTree, ScheduledCommission
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


def calculate_lifetime_reward_income(income):
    """
    Calculate lifetime reward income based on turnover.
    """
    reward_income = Decimal(0.0)
    reward_distribution = [0.4, 0.3, 0.2, 0.1]
    for index, ratio in enumerate(reward_distribution):
        reward_income += income * Decimal(0.02) * Decimal(ratio)
    return reward_income


def calculate_royalty_income(company_turnover):
    """
    Calculate royalty income based on company turnover.
    """
    royalty_income = Decimal(0.0)
    if company_turnover <= 1000000:
        royalty_income = company_turnover * Decimal(0.01)
    elif company_turnover <= 2500000:
        royalty_income = company_turnover * Decimal(0.01)
    elif company_turnover <= 5000000:
        royalty_income = company_turnover * Decimal(0.01)
    elif company_turnover <= 10000000:
        royalty_income = company_turnover * Decimal(0.01)
    return royalty_income

# Distribute Commission while added payment


def distribute_p2pmb_commission(instance, amount):
    if not instance or not amount:
        return
    instant_commission = Decimal(amount) * Decimal(0.03)
    monthly_commission = Decimal(amount) * Decimal(0.015)
    referral_by = instance.referral_by if instance.referral_by else None

    if referral_by:
        get_wallet = UserWallet.objects.filter(user=instance.referral_by, status='active').last()
        if not get_wallet:
            return
        get_wallet.app_wallet_balance += instant_commission
        referral_by.save()
        instance.commission_earned += instant_commission
        instance.save()
        Transaction.objects.create(
            created_by=get_wallet.user,
            sender=get_wallet.user,
            amount=instant_commission,
            transaction_type='commission',
            transaction_status='approved',
            remarks=f'Commission Added while added {instance.child.username}'
        )
        for month in range(1, 11):
            schedule_payment(referral_by, monthly_commission, month)
    else:
        top_user = MLMTree.objects.filter(parent=None).first()
        top_user.app_wallet_balance += instant_commission
        top_user.save()
        top_user.commission_earned += instant_commission
        top_user.save()
        Transaction.objects.create(
            created_by=top_user.user,
            sender=top_user.user,
            amount=instant_commission,
            transaction_type='commission',
            transaction_status='approved',
            remarks=f'Commission Added while added {instance.child.username}'
        )
        for month in range(1, 11):
            schedule_payment(top_user, monthly_commission, month)


def schedule_payment(user, amount, months_ahead):
    scheduled_date = datetime.datetime.now() + datetime.timedelta(days=30 * months_ahead)
    ScheduledCommission.objects.create(created_by=user, user=user, amount=amount, scheduled_date=scheduled_date)

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
            created_by=top_node.user,
            sender=top_node.user,
            amount=total_remaining,
            transaction_type='commission',
            transaction_status='approved',
            remarks=f'Commission Added while added {instance.child.username}'
        )


def distribute_to_levels_above(user, amount, percent, max_levels):
    """
    Distribute commission to levels above the user.
    Returns the remaining amount if fewer levels are available.
    """
    current_user = user
    distributed_levels = 0

    while distributed_levels < max_levels:
        parent = MLMTree.objects.filter(child=current_user).first()
        if not parent or not parent.parent:
            break
        wallet = UserWallet.objects.filter(user=parent.parent, status='active').last()
        commission = Decimal(amount) * percent
        wallet.app_wallet_balance += commission
        parent.parent.save()

        current_user = parent.parent
        distributed_levels += 1
        Transaction.objects.create(
            created_by=parent.parent,
            sender=parent.parent,
            amount=commission,
            transaction_type='commission',
            transaction_status='approved',
            remarks=f'Commission Added while added {current_user.get_full_name()}'
        )

    remaining_levels = max_levels - distributed_levels
    return Decimal(amount) * percent * Decimal(remaining_levels)


def distribute_to_levels_below(user, amount, percent, max_levels):
    """
    Distribute commission to levels below the user.
    Returns the remaining amount if fewer levels are available.
    """
    children = MLMTree.objects.filter(parent=user)
    remaining_levels = max_levels
    next_level_children = list(children)
    distributed_levels = 0

    while next_level_children and remaining_levels > 0:
        current_level_commission = Decimal(amount) * percent
        next_level_children = []
        wallet = UserWallet.objects.filter(user=children.parent, status='active').last()

        for child_entry in children:
            child = child_entry.child
            child.app_wallet_balance += current_level_commission
            child.save()
            next_level_children.extend(MLMTree.objects.filter(parent=child))
            Transaction.objects.create(
                created_by=children.parent,
                sender=children.parent,
                amount=current_level_commission,
                transaction_type='commission',
                transaction_status='approved',
                remarks=f'Commission Added while added {wallet.user.get_full_name()}'
            )

        remaining_levels -= 1
        distributed_levels += 1

    # Calculate remaining amount
    return Decimal(amount) * percent * Decimal(remaining_levels)