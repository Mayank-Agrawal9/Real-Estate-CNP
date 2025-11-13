import datetime
from collections import deque
from decimal import Decimal
from itertools import combinations

from dateutil.relativedelta import relativedelta
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Sum

from agency.models import RewardEarned, Investment, InvestmentInterest
from master.models import RewardMaster, RoyaltyMaster
from p2pmb.helpers import create_transaction_entry, create_commission_entry, get_level_counts
from p2pmb.models import MLMTree, ScheduledCommission, Commission, RoyaltyClub, Reward, P2PMBRoyaltyMaster, \
    RoyaltyEarned, HoldLevelIncome, ROIOverride, LapsedAmount
from payment_app.models import Transaction, UserWallet
from real_estate.constant import TURNOVER_DISTRIBUTION


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
                DistributeDirectCommission.schedule_monthly_payments(profile_instance.child,
                                                                     referral_by, monthly_commission)

                # Process parent commission if exists
                # if profile_instance.parent:
                #     DistributeDirectCommission.process_parent_commission(profile_instance.parent,
                #                                                          profile_instance.child, monthly_commission)

                # Schedule monthly payments for 9 months
                # if profile_instance.parent:


            else:
                # Handle case where there is no referral
                DistributeDirectCommission.handle_no_referral(profile_instance, instant_commission, monthly_commission)

            profile_instance.send_direct_income = True
            profile_instance.save()

    @staticmethod
    def process_referral_commission(referral_by, child, instant_commission):
        referral_user_wallet = UserWallet.objects.filter(user=referral_by, status='active').last()
        mlm_commission = MLMTree.objects.filter(child=referral_by, status='active').last()
        if referral_user_wallet:
            referral_user_wallet.app_wallet_balance += instant_commission
            referral_user_wallet.save()
            if mlm_commission:
                mlm_commission.commission_earned += instant_commission
                mlm_commission.save()

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
        top_user = MLMTree.objects.filter(parent=12, position=1).first()
        admin_wallet = UserWallet.objects.filter(user=top_user.child, status='active').last()
        if top_user:
            admin_wallet.app_wallet_balance += instant_commission
            top_user.commission_earned += instant_commission
            admin_wallet.save()
            top_user.save()

            DistributeDirectCommission.create_commission_entry(
                top_user.child, profile_instance.child, 'direct', instant_commission,
                f'Direct Commission Added while adding {profile_instance.child.username}')

            DistributeDirectCommission.create_transaction_entry(
                profile_instance.child, top_user.child, instant_commission, 'commission',
                'approved', f'Direct Commission Added while adding {profile_instance.child.username}')

            if profile_instance.parent:
                DistributeDirectCommission.schedule_monthly_payments(profile_instance.child,
                                                                     profile_instance.parent, monthly_commission)

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
        for month in range(1, 11):
            DistributeDirectCommission.schedule_payment(child, parent, monthly_amount, month)

    @staticmethod
    def schedule_payment(sender, user, amount, months_ahead):
        today = datetime.date.today()
        first_of_next_month = (today.replace(day=1) + relativedelta(months=2))
        scheduled_date = first_of_next_month + relativedelta(months=months_ahead - 1)
        ScheduledCommission.objects.create(
            created_by=user,
            send_by=sender,
            user=user,
            amount=amount,
            scheduled_date=scheduled_date
        )

    @staticmethod
    def cron_send_monthly_payment_direct_income():
        schedule_commission_instance = ScheduledCommission.objects.filter(scheduled_date__date__lte=datetime.datetime.today(),
                                                                          is_paid=False, remarks__isnull=True)
        for income in schedule_commission_instance:
            user_wallet = UserWallet.objects.filter(user=income.user, status='active').last()
            if not user_wallet:
                continue

            user_wallet.app_wallet_balance += income.amount
            user_wallet.save()

            DistributeDirectCommission.create_commission_entry(
                income.user, income.send_by, 'direct', income.amount,
                f'Direct Income Monthly Installment Added while adding {income.send_by.username}')

            DistributeDirectCommission.create_transaction_entry(
                income.user, income.user, income.amount, 'commission', 'approved',
                f'Direct Income Monthly Installment Added while adding {income.send_by.username}')

            income.is_paid = True
            income.save()

    @staticmethod
    def distribute_monthly_commission():
        schedule_commission_instance = ScheduledCommission.objects.filter(scheduled_date__date__lte=datetime.datetime.today(),
                                                                          is_paid=False, remarks__isnull=False)
        for income in schedule_commission_instance:
            user_wallet = UserWallet.objects.filter(user=income.user, status='active').last()
            if not user_wallet:
                continue

            user_wallet.app_wallet_balance += income.amount
            user_wallet.save()

            DistributeDirectCommission.create_commission_entry(
                income.user, income.send_by, 'direct', income.amount,
                income.remarks)

            DistributeDirectCommission.create_transaction_entry(
                income.user, income.user, income.amount, 'commission', 'approved',
                income.remarks)

            income.is_paid = True
            income.save()


# Distribute Level Income
class DistributeLevelIncome:

    @staticmethod
    def get_user_level(direct_count):
        level_map = {
            5: 5,
            4: 4,
            3: 3,
            2: 2,
            1: 1,
            0: 0,
        }

        for count, level in level_map.items():
            if direct_count >= count:
                return level
        return 0

    @staticmethod
    def get_user_down_level(direct_count):
        level_map = {
            5: 5,
            4: 4,
            3: 3,
            2: 2,
            1: 1,
            0: 0,
        }

        for count, level in level_map.items():
            if direct_count >= count:
                return level
        return 0

    @staticmethod
    def get_level_counts(direct_count):
        """
        Returns (up_levels, down_levels) based on direct count
        """
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

    @staticmethod
    def get_level_by_direct_user_required_counts(level):
        """
        Given a level, return the key whose value range includes that level,
        picking the smallest key that still qualifies.
        """
        level_map = {
            1: 2,
            2: 5,
            3: 10,
            4: 15,
            5: 20,
        }

        for key, max_level in sorted(level_map.items()):
            if level <= max_level:
                return key
        return None

    @staticmethod
    def get_below_level_by_direct_user_required_counts(level):
        """
        Given a level, return the key whose value range includes that level,
        picking the smallest key that still qualifies.
        """
        level_map = {
            1: 2,
            2: 5,
            3: 10
        }

        for key, max_level in sorted(level_map.items()):
            if level <= max_level:
                return key
        return None

    @staticmethod
    def distribute_level_income(instance, amount, up_max_level, down_max_level):
        """
        Distribute level income over 30 levels:
        - 0.15% for 20 levels above the user
        - 0.15% for 10 levels below the user
        - Remaining amount goes to the top node if levels are not complete.
        """
        total_up_amount_send = amount * Decimal(0.03)
        total_down_amount_send = amount * Decimal(0.015)
        level_above_percent = Decimal(0.0015)
        level_below_percent = Decimal(0.0015)

        # Distribute to 20 levels above
        total_amount_send_above = DistributeLevelIncome.distribute_to_levels_above(
            instance, amount, level_above_percent, up_max_level
        )

        # Distribute to 10 levels below
        total_amount_send_below = DistributeLevelIncome.distribute_to_levels_below(
            instance, amount, level_below_percent, down_max_level
        )

        remaining_above = total_up_amount_send - total_amount_send_above
        remaining_below = total_down_amount_send - total_amount_send_below

        if int(remaining_above) > 0:
            LapsedAmount.objects.create(user=instance.child, earned_type='level_income', amount=remaining_above,
                                        remarks=f'Up Level Income Remaining in the top up of {amount}')

        if int(remaining_below) > 0:
            LapsedAmount.objects.create(user=instance.child, earned_type='level_income', amount=remaining_below,
                                        remarks=f'Down Level Income Remaining in the top up of {amount}')

    @staticmethod
    def distribute_to_levels_above(user, amount, percent, max_levels):
        """
        Distribute commission up to max_levels above the user.
        Based on the receiver's directs and depth logic.
        """
        current_user = user.parent
        base_user = user
        distributed_levels = 0
        commission = Decimal(amount) * percent
        total_distributed = Decimal('0')

        level = 1

        while distributed_levels < max_levels and current_user:
            parent_relation = MLMTree.objects.filter(child=current_user).first()

            if not parent_relation:
                break

            direct_count = MLMTree.objects.filter(referral_by=current_user).count()
            up_levels, down_levels = DistributeLevelIncome.get_level_counts(direct_count)
            if direct_count == 0:
                direct_id_required = DistributeLevelIncome.get_level_by_direct_user_required_counts(level)
                total_distributed += commission
                HoldLevelIncome.objects.create(
                    commission_by=base_user.child,
                    commission_to=current_user,
                    level_type='up',
                    amount=commission,
                    on_level=parent_relation.show_level or 0,
                    description=f'Level Commission added for {base_user.child.username}',
                    direct_user_required=direct_id_required,
                )
            else:
                if level <= up_levels:
                    total_distributed += commission
                    parent_wallet = UserWallet.objects.filter(user=current_user, status='active').last()
                    if parent_wallet:
                        parent_wallet.app_wallet_balance += commission
                        parent_wallet.save()

                    create_transaction_entry(
                        base_user.child, current_user, commission, 'commission', 'approved',
                        f'Level Commission added by adding {base_user.child.username}'
                    )

                    create_commission_entry(current_user, base_user.child, 'level', commission,
                                            f'Level Commission added for {base_user.child.username}')
                else:
                    direct_id_required = DistributeLevelIncome.get_level_by_direct_user_required_counts(level)
                    total_distributed += commission
                    HoldLevelIncome.objects.create(
                        commission_by=base_user.child,
                        commission_to=current_user,
                        level_type='up',
                        amount=commission,
                        on_level=parent_relation.show_level or 0,
                        description=f'Level Commission added for {base_user.child.username}',
                        direct_user_required=direct_id_required,
                    )

            distributed_levels += 1
            level += 1
            current_user = parent_relation.parent

        return total_distributed

    @staticmethod
    def distribute_to_levels_below(user, amount, percent, max_levels):
        """
        Distribute commission starting from the *first* downline user,
        going down a single branch only.
        """
        base_user = user.child
        commission = Decimal(amount) * percent
        total_distributed = Decimal('0')

        distributed_levels = 0
        level = 1

        # Get the very first child of the starting user
        relation = MLMTree.objects.filter(parent=user.child).select_related('child').first()
        current_user = relation.child if relation else None

        while distributed_levels < max_levels and current_user:
            direct_count = MLMTree.objects.filter(referral_by=current_user).count()
            up_levels, down_levels = DistributeLevelIncome.get_level_counts(direct_count)

            if direct_count == 0:
                direct_id_required = DistributeLevelIncome.get_level_by_direct_user_required_counts(level)
                HoldLevelIncome.objects.create(
                    commission_by=base_user,
                    commission_to=current_user,
                    level_type='down',
                    amount=commission,
                    on_level=level,
                    description=f'Down Level Commission added for {base_user.username}',
                    direct_user_required=direct_id_required,
                )
                total_distributed += commission
            else:
                if level <= down_levels:
                    parent_wallet = UserWallet.objects.filter(user=current_user, status='active').last()
                    if parent_wallet:
                        parent_wallet.app_wallet_balance += commission
                        parent_wallet.save()

                    create_transaction_entry(
                        base_user, current_user, commission, 'commission', 'approved',
                        f'Down Level Commission added by {base_user.username}'
                    )

                    create_commission_entry(current_user, base_user, 'level', commission,
                                            f'Down Level Commission added for {base_user.username}')
                    total_distributed += commission
                else:
                    direct_id_required = DistributeLevelIncome.get_below_level_by_direct_user_required_counts(level)
                    HoldLevelIncome.objects.create(
                        commission_by=base_user,
                        commission_to=current_user,
                        level_type='down',
                        amount=commission,
                        on_level=level,
                        description=f'Down Level Commission added for {base_user.username}',
                        direct_user_required=direct_id_required,
                    )
                    total_distributed += commission

            # Move to that user's first child
            relation = MLMTree.objects.filter(parent=current_user).select_related('child').first()
            current_user = relation.child if relation else None

            distributed_levels += 1
            level += 1

        return total_distributed


    # @staticmethod
    # def distribute_to_levels_below(user, amount, percent, max_levels, direct_id_required):
    #     """
    #     Distribute commission to levels below the user (one per level, follow deepest path).
    #     Returns the remaining amount if fewer levels are available.
    #     """
    #     current_user = user.child
    #     base_user = user
    #     distributed_levels = 0
    #     commission = Decimal(amount) * percent
    #
    #     while distributed_levels < max_levels:
    #         children = MLMTree.objects.filter(parent=current_user, status='active')
    #
    #         if not children:
    #             break
    #
    #         next_child_user = None
    #         for child in children:
    #             if MLMTree.objects.filter(parent=child.child, status='active').exists():
    #                 next_child_user = child.child
    #                 break
    #
    #         if not next_child_user:
    #             next_child_user = children.first().child
    #
    #         if not next_child_user:
    #             break
    #
    #         child_direct_count = MLMTree.objects.filter(status='active', referral_by=next_child_user).count()
    #         child_level = DistributeLevelIncome.get_user_level(child_direct_count)
    #
    #         if child_level >= direct_id_required:
    #             child_wallet = UserWallet.objects.filter(user=next_child_user, status='active').last()
    #             if child_wallet:
    #                 child_wallet.app_wallet_balance += commission
    #                 child_wallet.save()
    #
    #             create_transaction_entry(
    #                 base_user.child, next_child_user, commission, 'commission', 'approved',
    #                 f'Level Commission added by {base_user.child.username}'
    #             )
    #
    #             create_commission_entry(
    #                 next_child_user, base_user.child, 'level', commission,
    #                 f'Level Commission added by {base_user.child.username}'
    #             )
    #         else:
    #             HoldLevelIncome.objects.create(
    #                 commission_by=base_user.child,
    #                 commission_to=next_child_user,
    #                 level_type='down',
    #                 amount=commission,
    #                 on_level=base_user.show_level or 0,
    #                 description=f'User not qualified for level {distributed_levels + 1}',
    #                 direct_user_required=direct_id_required,
    #             )
    #
    #         distributed_levels += 1
    #         current_user = next_child_user
    #
    #     remaining_levels = max_levels - distributed_levels
    #     return commission * Decimal(remaining_levels)


class LifeTimeRewardIncome:
    @staticmethod
    def check_and_allocate_rewards():
        parents = MLMTree.objects.filter(parent__isnull=False, status='active', is_show=True).select_related('parent')

        processed_parents = {}

        reward_master_queryset = RewardMaster.objects.filter(applicable_for='p2pmb').only(
            'id', 'turnover_threshold', 'gift_amount', 'total_paid_month'
        )

        for parent in parents:
            if parent.parent_id in processed_parents:
                continue

            children = list(MLMTree.objects.filter(parent=parent.parent, status='active')[:5])

            if len(children) < 4:
                continue

            processed_parents[parent.parent_id] = True

            for reward in reward_master_queryset:
                if RewardEarned.objects.filter(
                        user=parent.parent, reward=reward, status='active', is_p2p=True
                ).exists():
                    continue

                threshold = reward.turnover_threshold

                for comb in combinations(children, 4):
                    turnovers = sorted([child.turnover for child in comb], reverse=True)

                    if all(turnovers[i] >= (threshold * TURNOVER_DISTRIBUTION[i]) / 100 for i in range(4)):
                        parent.commission_earned += reward.gift_amount or 0
                        parent.save()

                        RewardEarned.objects.create(
                            user=parent.parent,
                            created_by=parent.parent,
                            reward=reward,
                            earned_at=datetime.datetime.now().today().replace(day=1),
                            turnover_at_earning=parent.turnover,
                            is_paid=True,
                            total_month=reward.total_paid_month,
                            is_p2p=True
                        )
                        break


class RoyaltyClubDistribute:

    # @staticmethod
    # def get_eligible_user():
    #     star =



    @staticmethod
    def check_royalty_club_membership():
        """
        Check and assign royalty club membership based on defined criteria.
        """
        persons = MLMTree.objects.filter(status='active', is_show=True)
        royalties = RoyaltyMaster.objects.filter(status='active')
        for royalty in royalties:
            for person in persons:
                direct_ids_count = MLMTree.objects.filter(referral_by=person.child, status='active').count()
                team_count_level_one = MLMTree.objects.filter(parent=person.child, status='active').count()
                team_count_level_two = MLMTree.objects.filter(
                    parent__in=MLMTree.objects.filter(parent=person.child).values_list('child', flat=True)).count()

                if (direct_ids_count >= royalty.direct_ids_required and
                        team_count_level_one >= royalty.level_one_required and
                        team_count_level_two >= royalty.level_two_required):
                    gift_amount = royalty.gift_amount
                    person.commission_earned += gift_amount
                    person.save()
                    Commission.objects.get_or_create(
                        created_by=person.child, commission_by=person.child, commission_to=person.child,
                        commission_type='royalty', amount=gift_amount,
                        description=f'Earned commission for royalty income in {royalty.club_type}.'
                    )
                    RoyaltyClub.objects.get_or_create(
                        person=person, club_type=royalty.club_type, turnover_limit=royalty.turnover_limit,
                        direct_ids_required=royalty.direct_ids_required, level_one_required=royalty.level_one_required,
                        level_two_required=royalty.level_two_required, gifts_value=royalty.gift_amount
                    )

    @staticmethod
    def check_working_id_active():
        """
        Check and update the status of working id.
        """
        persons = MLMTree.objects.filter(status='active', is_working_id=False)
        for person in persons:
            direct_ids_count = MLMTree.objects.filter(referral_by=person.child, status='active').count()
            if direct_ids_count >= 2:
                person.is_working_id = True
                person.save()
            # team_count_level_one = MLMTree.objects.filter(parent=person.child, status='active').count()
            # team_count_level_two = MLMTree.objects.filter(
            #     parent__in=MLMTree.objects.filter(parent=person.child).values_list('child', flat=True)).count()
            #
            # if (direct_ids_count >= 10) or (team_count_level_one >= 5 and team_count_level_two >= 25):
            #     person.is_working_id = True
            #     person.save()

    @staticmethod
    def calculate_royalty(user):
        """Calculate royalty for a given user in MLMTree."""
        mlm_entry = MLMTree.objects.filter(child=user).last()
        if not mlm_entry:
            return {"status": "error", "message": "User not found in MLM Tree"}

        direct_referrals = MLMTree.objects.filter(referral_by=user).count()
        total_team_count = MLMTree.objects.filter(parent__in=MLMTree.objects.filter(parent=user)).count()
        direct_users = MLMTree.objects.filter(parent=user)
        compulsory_royalty_users = direct_users.filter(turnover__gte=mlm_entry.turnover).count()

        if direct_referrals >= 5 and compulsory_royalty_users >= 5:
            royalty = min(200000, mlm_entry.turnover)
            star_level = "1 Star"
        elif direct_referrals >= 10 and compulsory_royalty_users >= 10:
            royalty = min(500000, mlm_entry.turnover)
            star_level = "2 Star"
        elif direct_referrals >= 10:
            valid_users = direct_users.annotate(direct_count=Count('children')).filter(direct_count__gte=10).count()
            if valid_users >= 5:
                royalty = min(2500000, mlm_entry.turnover)
                star_level = "3 Star"
            else:
                royalty = 0
                star_level = "Not Qualified"
        elif total_team_count >= 10:
            count_3star_users = MLMTree.objects.filter(child__in=direct_users, level=3).count()
            if count_3star_users >= 10:
                royalty = "Lifetime Royalty"
                star_level = "5 Star"
            else:
                royalty = 0
                star_level = "Not Qualified"
        else:
            royalty = 0
            star_level = "Not Qualified"
        return {"star_level": star_level, "royalty": royalty}

    @staticmethod
    def one_star_royalty():
        royalty = P2PMBRoyaltyMaster.objects.filter(
            month__month=datetime.datetime.now().month, month__year=datetime.datetime.now().year,
            is_distributed=False
        ).last()

        if not royalty or royalty.star_income == 0:
            return {"status": "error", "message": "No valid royalty to distribute"}

        eligible_users = MLMTree.objects.filter(
            status='active', is_show=True, referral_by__isnull=False
        ).values_list('referral_by', flat=True).distinct()

        if not eligible_users:
            return {"status": "error", "message": "No eligible users for royalty distribution"}

        final_eligible_users = []

        for elg_user in eligible_users:
            user = User.objects.filter(id=elg_user).last()
            eligible_users = MLMTree.objects.filter(
                status='active', is_show=True, referral_by__isnull=False, referral_by=user
            )
            if not eligible_users or eligible_users.count() < 5:
                continue

            # Investment.objects :todo -> Add Amount greater then or equal to logic

            referrer_earnings = RoyaltyEarned.objects.filter(
                user=user, club_type='star'
            ).aggregate(total_earned=Sum('earned_amount'))["total_earned"] or 0

            if referrer_earnings > 200000:
                continue

            final_eligible_users.append(user)

        default_user = User.objects.filter(id=33).first()
        if default_user and default_user not in final_eligible_users:
            final_eligible_users.append(default_user)

        if not final_eligible_users:
            return {"status": "error", "message": "No eligible users after applying earnings filter"}

        total_users = len(final_eligible_users)
        total_income_distributed = royalty.star_income / total_users if total_users > 0 else 0

        for user in final_eligible_users:
            RoyaltyEarned.objects.create(
                user=user, club_type='star', earned_date=datetime.datetime.now(),
                earned_amount=total_income_distributed, royalty=royalty, is_paid=True
            )
            user_wallet = UserWallet.objects.filter(user=user, status='active').last()
            if user_wallet:
                user_wallet.app_wallet_balance += total_income_distributed
                user_wallet.save()

            create_transaction_entry(
                user, user, total_income_distributed, 'commission', 'approved',
                'Royalty Commission for 1 Star.'
            )

            create_commission_entry(
                user, user, 'royalty', total_income_distributed,
                'Royalty Commission for 1 Star.'
            )
        royalty.is_distributed = True
        royalty.save()
        return total_users

    @staticmethod
    def two_star_royalty():
        royalty = P2PMBRoyaltyMaster.objects.filter(
            month__month=datetime.datetime.now().month, month__year=datetime.datetime.now().year,
            is_two_star_distributed=False
        ).last()

        if not royalty or royalty.star_income == 0:
            return 0

        eligible_users = MLMTree.objects.filter(
            status='active', is_show=True, referral_by__isnull=False
        ).values_list('referral_by', flat=True).distinct()

        if not eligible_users:
            return 0

        final_eligible_users = []

        for elg_user in eligible_users:
            user = User.objects.filter(id=elg_user).last()
            eligible_users = MLMTree.objects.filter(
                status='active', is_show=True, referral_by__isnull=False, referral_by=user
            )
            if not eligible_users or eligible_users.count() < 10:
                continue

            # Investment.objects :todo -> Add Amount greater then or equal to logic

            referrer_earnings = RoyaltyEarned.objects.filter(
                user=user, club_type='2_star'
            ).aggregate(total_earned=Sum('earned_amount'))["total_earned"] or 0

            if referrer_earnings > 500000:
                continue

            final_eligible_users.append(user)

        default_user = User.objects.filter(id=33).first()
        if default_user and default_user not in final_eligible_users:
            final_eligible_users.append(default_user)

        if not final_eligible_users:
            return 0

        total_users = len(final_eligible_users)
        total_income_distributed = royalty.two_star_income / total_users if total_users > 0 else 0

        for user in final_eligible_users:
            RoyaltyEarned.objects.create(
                user=user, club_type='2_star', earned_date=datetime.datetime.now(),
                earned_amount=total_income_distributed, royalty=royalty, is_paid=True
            )
            user_wallet = UserWallet.objects.filter(user=user, status='active').last()
            if user_wallet:
                user_wallet.app_wallet_balance += total_income_distributed
                user_wallet.save()

            create_transaction_entry(
                user, user, total_income_distributed, 'commission', 'approved',
                'Royalty Commission for 1 Star.'
            )

            create_commission_entry(
                user, user, 'royalty', total_income_distributed,
                'Royalty Commission for 1 Star.'
            )
        royalty.is_two_star_distributed = True
        royalty.save()
        return total_users

    @staticmethod
    def three_star_royalty():
        royalty = P2PMBRoyaltyMaster.objects.filter(
            month__month=datetime.datetime.now().month, month__year=datetime.datetime.now().year
        ).last()

        if not royalty or royalty.star_income == 0:
            return {"status": "error", "message": "No valid royalty to distribute"}

        eligible_users = MLMTree.objects.filter(
            status='active', is_show=True, referral_by__isnull=False
        ).values_list('referral_by', flat=True).distinct()

        if not eligible_users:
            return {"status": "error", "message": "No eligible users for royalty distribution"}

        final_eligible_users = []

        for elg_user in eligible_users:
            user = User.objects.filter(id=elg_user).last()
            eligible_users = MLMTree.objects.filter(
                status='active', is_show=True, referral_by__isnull=False, referral_by=user
            )
            if not eligible_users or eligible_users.count() < 5:
                continue

            # Investment.objects :todo -> Add Amount greater then or equal to logic

            referrer_earnings = RoyaltyEarned.objects.filter(
                user=user, club_type='star'
            ).aggregate(total_earned=Sum('earned_amount'))["total_earned"] or 0

            if referrer_earnings > 200000:
                continue

            final_eligible_users.append(user)

        default_user = User.objects.filter(id=33).first()
        if default_user and default_user not in final_eligible_users:
            final_eligible_users.append(default_user)

        if not final_eligible_users:
            return {"status": "error", "message": "No eligible users after applying earnings filter"}

        total_users = len(final_eligible_users)
        total_income_distributed = royalty.star_income / total_users if total_users > 0 else 0

        for user in final_eligible_users:
            RoyaltyEarned.objects.create(
                user=user, club_type='star', earned_date=datetime.datetime.now(),
                earned_amount=total_income_distributed, royalty=royalty, is_paid=True
            )
            user_wallet = UserWallet.objects.filter(user=user, status='active').last()
            if user_wallet:
                user_wallet.app_wallet_balance += total_income_distributed
                user_wallet.save()

            create_transaction_entry(
                user, user, total_income_distributed, 'commission', 'approved',
                'Royalty Commission for 1 Star.'
            )

            create_commission_entry(
                user, user, 'royalty', total_income_distributed,
                'Royalty Commission for 1 Star.'
            )
        royalty.is_distributed = True
        royalty.save()
        return total_users

    @staticmethod
    def five_star_royalty():
        royalty = P2PMBRoyaltyMaster.objects.filter(
            month__month=datetime.datetime.now().month, month__year=datetime.datetime.now().year,
            is_distributed=False
        ).last()

        if not royalty or royalty.star_income == 0:
            return {"status": "error", "message": "No valid royalty to distribute"}

        eligible_users = MLMTree.objects.filter(
            status='active', is_show=True, referral_by__isnull=False
        ).values_list('referral_by', flat=True).distinct()

        if not eligible_users:
            return {"status": "error", "message": "No eligible users for royalty distribution"}

        final_eligible_users = []

        for elg_user in eligible_users:
            user = User.objects.filter(id=elg_user).last()
            eligible_users = MLMTree.objects.filter(
                status='active', is_show=True, referral_by__isnull=False, referral_by=user
            )
            if not eligible_users or eligible_users.count() < 5:
                continue

            # Investment.objects :todo -> Add Amount greater then or equal to logic

            referrer_earnings = RoyaltyEarned.objects.filter(
                user=user, club_type='star'
            ).aggregate(total_earned=Sum('earned_amount'))["total_earned"] or 0

            if referrer_earnings > 200000:
                continue

            final_eligible_users.append(user)

        default_user = User.objects.filter(id=33).first()
        if default_user and default_user not in final_eligible_users:
            final_eligible_users.append(default_user)

        if not final_eligible_users:
            return {"status": "error", "message": "No eligible users after applying earnings filter"}

        total_users = len(final_eligible_users)
        total_income_distributed = royalty.star_income / total_users if total_users > 0 else 0

        for user in final_eligible_users:
            RoyaltyEarned.objects.create(
                user=user, club_type='star', earned_date=datetime.datetime.now(),
                earned_amount=total_income_distributed, royalty=royalty, is_paid=True
            )
            user_wallet = UserWallet.objects.filter(user=user, status='active').last()
            if user_wallet:
                user_wallet.app_wallet_balance += total_income_distributed
                user_wallet.save()

            create_transaction_entry(
                user, user, total_income_distributed, 'commission', 'approved',
                'Royalty Commission for 1 Star.'
            )

            create_commission_entry(
                user, user, 'royalty', total_income_distributed,
                'Royalty Commission for 1 Star.'
            )
        royalty.is_distributed = True
        royalty.save()
        return total_users

    @staticmethod
    def distribute_royalty():
        total_one_star_user = RoyaltyClubDistribute.one_star_royalty()
        # total_two_star_user = RoyaltyClubDistribute.two_star_royalty()
        # total_three_star_user = RoyaltyClubDistribute.three_star_royalty()
        # total_five_star_user = RoyaltyClubDistribute.five_star_royalty()
        return {"status": "success", "message": f"Royalty distributed among {total_one_star_user} users"}


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


class ProcessMonthlyInterestP2PMB:

    @staticmethod
    def calculate_monthly_interest_amount(user, investment_type, invested_amount):
        """Calculate monthly interest with all ROI overrides applied."""
        interest_rate = ProcessMonthlyInterestP2PMB.calculate_interest_rate(user, investment_type)

        overrides = ROIOverride.objects.filter(user=user, status='active')

        for override in overrides:
            percentage_value = override.percentage or 0
            adjustment = Decimal(str(percentage_value)) / Decimal('100')

            if override.action_type == 'increase':
                interest_rate += adjustment
            elif override.action_type == 'decrease':
                interest_rate -= adjustment

        if interest_rate < Decimal('0'):
            interest_rate = Decimal('0')

        interest_amount = invested_amount * interest_rate
        return interest_amount

    @staticmethod
    def get_investment_duration(investment_type):
        """Example function to calculate monthly interest."""
        investment_duration = {
            "full_payment": 10,
            "part_payment": 6,
        }
        return investment_duration.get(investment_type, 0)

    @staticmethod
    def generate_interest_for_all_investments():
        """Generate interest for all approved investments that need interest payments."""
        today = datetime.datetime.now().date()
        if today.day != 2 or (today.month <= 3 and today.year <= 2025):
            print("Interest calculation skipped. Only runs on the 1st of each month.")
            return
        investments = Investment.objects.filter(
            status='active', is_approved=True, pay_method='main_wallet', investment_type='p2pmb',
            package__isnull=False, investment_guaranteed_type__isnull=False, date_created__gte='2025-03-01'
        ).select_related('user')

        interest_records = []

        for investment in investments:
            if investment.user and investment.user.profile and not investment.user.profile.is_roi_send:
                continue
            user = investment.user
            approved_date = investment.date_created.date()
            duration_years = ProcessMonthlyInterestP2PMB.get_investment_duration(investment.investment_guaranteed_type)

            if duration_years == 0:
                continue

            first_interest_date = (approved_date.replace(day=1) + relativedelta(months=1))
            end_date = approved_date + relativedelta(years=duration_years)

            if today > end_date:
                continue

            existing_interest = InvestmentInterest.objects.filter(
                investment=investment, interest_send_date=today.replace(day=1)
            ).exists()

            if existing_interest:
                continue

            amount = ProcessMonthlyInterestP2PMB.calculate_monthly_interest_amount(
                user, investment.investment_guaranteed_type, investment.amount)

            # Handle partial month interest for the first month
            if approved_date.year == today.year and approved_date.month == today.month - 1:
                days_remaining = (first_interest_date - approved_date).days
                full_month_days = (first_interest_date - datetime.timedelta(days=1)).day

                amount = (amount / full_month_days) * days_remaining

                interest_records.append(
                    InvestmentInterest(
                        created_by=user,
                        investment=investment,
                        interest_amount=amount,
                        interest_send_date=today.replace(day=1),
                        is_sent=True,
                        end_date=end_date
                    )
                )
            else:
                interest_records.append(
                    InvestmentInterest(
                        created_by=user,
                        investment=investment,
                        interest_amount=amount,
                        interest_send_date=today.replace(day=1),
                        is_sent=True,
                        end_date=end_date
                    )
                )

            create_transaction_entry(
                user, user, amount, 'interest', 'approved',
                f'Monthly Interest Added for investment of {investment.amount} in P2PMB.'
            )

            # Update user wallet
            user_wallet = UserWallet.objects.filter(user=user, status='active').last()
            if user_wallet:
                user_wallet.app_wallet_balance += amount
                user_wallet.save()

            # Mark investment as interest sent
            investment.is_interest_send = True
            investment.save()

        if interest_records:
            InvestmentInterest.objects.bulk_create(interest_records)
            print(f"Interest records created for {len(interest_records)} investments.")

    @staticmethod
    def calculate_interest_rate(user, investment_type):
        direct_referrals = MLMTree.objects.filter(referral_by=user).select_related('child')
        referral_count = direct_referrals.count()

        base_interest_rate = Decimal('0.01') if investment_type == 'full_payment' else Decimal('0.02')

        full_team_users = ProcessMonthlyInterestP2PMB.get_full_team_users(user)
        high_performers_in_team = sum(
            1 for member in full_team_users
            if MLMTree.objects.filter(referral_by=member).count() >= 10
        )
        if high_performers_in_team >= 10:
            return Decimal('0.05') if investment_type == 'full_payment' else Decimal('0.1')

        # 4. Check for 3x: From direct referrals, any 5 have ≥10 referrals
        if referral_count >= 10:
            high_performers_in_directs = sum(
                1 for referral in direct_referrals
                if MLMTree.objects.filter(referral_by=referral.child).count() >= 10
            )
            if high_performers_in_directs >= 5:
                return Decimal('0.03') if investment_type == 'full_payment' else Decimal('0.06')  # 3x

            return Decimal('0.02') if investment_type == 'full_payment' else Decimal('0.04')  # 2x

        # 5. Check for 1.5x
        if referral_count >= 5:
            return Decimal('0.015') if investment_type == 'full_payment' else Decimal('0.03')  # 1.5x

        # 6. Fallback
        return base_interest_rate

    @staticmethod
    def get_full_team_users(user):
        """
        Traverses the MLM tree downward starting from the given user
        and returns a set of all users in their full team (all levels).
        """
        visited = set()
        queue = deque()

        # Start with direct children
        children = MLMTree.objects.filter(parent=user).select_related('child')
        for node in children:
            queue.append(node.child)

        while queue:
            current_user = queue.popleft()
            if current_user in visited:
                continue
            visited.add(current_user)

            # Enqueue current_user's children
            children = MLMTree.objects.filter(parent=current_user).select_related('child')
            for node in children:
                queue.append(node.child)

        return visited