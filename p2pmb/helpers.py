import datetime

import django_filters
from django.db.models import Q
from rest_framework.pagination import PageNumberPagination

from p2pmb.models import Commission, MLMTree, ExtraReward
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


def get_level_counts(direct_count):
    level_map = {
        5: (20, 10),
        4: (15, 10),
        3: (10, 10),
        2: (5, 5),
        1: (2, 2),
        0: (0, 0),
    }

    return next(
        (upl, downl) for count, (upl, downl) in level_map.items() if direct_count >= count
    )


class ExtraRewardFilter(django_filters.FilterSet):
    is_expire = django_filters.BooleanFilter(method="filter_is_expire")

    class Meta:
        model = ExtraReward
        fields = ["reward_type", "status", "is_expire"]

    def filter_is_expire(self, queryset, name, value):
        today = datetime.date.today()
        if value is True:
            return queryset.filter(end_date__lt=today)
        elif value is False:
            return queryset.filter(
                Q(end_date__gte=today) | Q(end_date__isnull=True)
            )
        return queryset


class PackagePagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = 'page_size'
    max_page_size = 100