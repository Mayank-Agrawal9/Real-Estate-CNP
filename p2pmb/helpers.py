import datetime

from p2pmb.models import Commission, MLMTree
from payment_app.models import Transaction


def create_commission_entry(commission_to, commission_by, commission_type, amount, description):
    Commission.objects.create(
        created_by=commission_to,
        commission_by=commission_by,
        commission_to=commission_to,
        commission_type=commission_type,
        amount=amount,
        description=description
    )


def create_transaction_entry(sender, receiver, amount, transaction_type, transaction_status, remarks):
    Transaction.objects.create(
        created_by=sender,
        sender=sender,
        receiver=receiver,
        amount=amount,
        transaction_type=transaction_type,
        transaction_status=transaction_status,
        payment_method='wallet',
        remarks=remarks,
        verified_on=datetime.datetime.now()
    )


def get_levels_above_count(user):
    """ Retrieve and count all levels of parent users recursively until the root is reached. """
    current_user = user.parent
    level_count = 0

    while current_user:
        parent = MLMTree.objects.filter(child=current_user, status='active', is_show=True).first()
        if not parent or not parent.parent:
            break

        current_user = parent.parent
        level_count += 1

    return level_count


def count_all_descendants(user):
    """
    Recursively count all child users at all levels.
    """
    children = MLMTree.objects.filter(parent=user, status='active', is_show=True)
    count = children.count()

    for child in children:
        count += count_all_descendants(child.child)

    return count


def get_downline_count(user):
    def count_children(parent_user):
        children = MLMTree.objects.filter(parent=parent_user, is_show=True)
        count = children.count()
        for child_entry in children:
            count += count_children(child_entry.child)
        return count

    return count_children(user)
