import datetime
from decimal import Decimal
from itertools import combinations

from dateutil.relativedelta import relativedelta
from django.db import transaction

from agency.models import RewardEarned, Investment
from master.models import RewardMaster, RoyaltyMaster
from p2pmb.helpers import create_transaction_entry, create_commission_entry
from p2pmb.models import MLMTree, ScheduledCommission, Commission, RoyaltyClub, Reward, P2PMBRoyaltyMaster
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

                # Process parent commission if exists
                # if profile_instance.parent:
                #     DistributeDirectCommission.process_parent_commission(profile_instance.parent,
                #                                                          profile_instance.child, monthly_commission)

                # Schedule monthly payments for 9 months
                if profile_instance.parent:
                    DistributeDirectCommission.schedule_monthly_payments(profile_instance.child,
                                                                         profile_instance.parent, monthly_commission)

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
        first_of_next_month = (today.replace(day=1) + relativedelta(months=1))
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
        # remaining_below = DistributeLevelIncome.distribute_to_levels_below(
        #     instance, amount, level_below_percent, 10
        # )

        remaining_below = Decimal(amount) * level_below_percent * Decimal(10)

        # Send remaining amounts to the top node
        # instance.send_level_income = True
        # instance.save()
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
                instance.child, top_node.child, total_remaining, 'commission', 'approved',
                f'Level Commission added by adding {instance.child.username} remaining account.')

            # Create commission record
            create_commission_entry(top_node.child, instance.child, 'level', total_remaining,
                                    f'Commission added for {instance.child.username} remaining account.')

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

            parent_wallet = UserWallet.objects.filter(user=parent.parent, status='active').last()
            if parent_wallet:
                parent_wallet.app_wallet_balance += commission
                parent_wallet.save()

            # Create transaction record for this distribution
            create_transaction_entry(
                base_user.child, parent.parent, commission, 'commission', 'approved',
                f'Level Commission added by adding {base_user.child.username}')

            # Create commission record
            create_commission_entry(parent.parent, base_user.child, 'level', commission,
                                    f'Commission added for {base_user.child.username}')

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


class LifeTimeRewardIncome:
    @staticmethod
    def check_and_allocate_rewards():
        parents = MLMTree.objects.filter(parent__isnull=False, status='active').select_related('parent')

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
                            earned_at=datetime.datetime.now(),
                            turnover_at_earning=parent.turnover,
                            is_paid=False,
                            total_month=reward.total_paid_month,
                            is_p2p=True
                        )

                        commission_entries = [
                            ScheduledCommission(
                                created_by=parent.parent,
                                send_by=parent.parent,
                                user=parent.parent,
                                amount=reward.gift_amount,
                                scheduled_date=datetime.datetime.now() + datetime.timedelta(days=30 * i),
                                is_paid=False,
                                remarks=f'Commission added for life time reward earned {reward.name}'
                            )
                            for i in range(reward.total_paid_month)
                        ]
                        ScheduledCommission.objects.bulk_create(commission_entries)
                        break


class RoyaltyClubDistribute:
    @staticmethod
    def check_royalty_club_membership():
        """
        Check and assign royalty club membership based on defined criteria.
        """
        persons = MLMTree.objects.filter(status='active')
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
            team_count_level_one = MLMTree.objects.filter(parent=person.child, status='active').count()
            team_count_level_two = MLMTree.objects.filter(
                parent__in=MLMTree.objects.filter(parent=person.child).values_list('child', flat=True)).count()

            if (direct_ids_count >= 10) or (team_count_level_one >= 5 and team_count_level_two >= 25):
                person.is_working_id = True
                person.save()

    # New Working
    @staticmethod
    def distribute_royalty():
        royalties = P2PMBRoyaltyMaster.objects.filter(month=datetime.datetime.month)
        for royalty_master in royalties:
            eligible_users = royalty_master.eligible_user.all()
            if not eligible_users.exists():
                return "No eligible users found."

            income_fields = {
                'star_income': royalty_master.star_income,
                'two_star_income': royalty_master.two_star_income,
                'three_star_income': royalty_master.three_star_income,
                'lifetime_income': royalty_master.lifetime_income
            }

            for user in eligible_users:
                for income_type, amount in income_fields.items():
                    commission = amount / len(eligible_users)
                    user_wallet = UserWallet.objects.filter(user=user, status='active').last()
                    if user_wallet:
                        user_wallet.app_wallet_balance += commission
                        user_wallet.save()

                    # Create transaction record for this distribution
                    create_transaction_entry(
                        user, user, commission, 'commission', 'approved',
                        f'Royalty Commission added by Click N Pay.')

                    # Create commission record
                    create_commission_entry(user, user, 'royalty', commission,
                                            f'Royalty Commission added by Click N Pay.')

            return "Royalty distributed successfully."


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
    def process_p2pmb_monthly_interest():
        """
        Process monthly interest for all eligible investments.
        """
        investments = Investment.objects.filter(
            status='active', is_approved=True, pay_method='main_wallet', investment_type='p2pmb', is_interest_send=False
        ).select_related('user')

        for investment in investments:
            if investment.investment_guaranteed_type:
                user = investment.user
                interest_rate = ProcessMonthlyInterestP2PMB.calculate_interest_rate(
                    user, investment.investment_guaranteed_type)
                interest_amount = investment.amount * interest_rate

                # Create transaction entry
                create_transaction_entry(
                    user, user, interest_amount, 'interest', 'approved',
                    f'Monthly Interest Added for investment of {investment.amount} in P2PMB.'
                )

                # Update user wallet
                user_wallet = UserWallet.objects.filter(user=user, status='active').last()
                if user_wallet:
                    user_wallet.app_wallet_balance += interest_amount
                    user_wallet.save()

                # Mark investment as interest sent
                investment.is_interest_send = True
                investment.save()

    @staticmethod
    def calculate_interest_rate(user, investment_type):
        """
        Calculate the interest rate based on user's referrals and team conditions.
        """
        referral_count = MLMTree.objects.filter(referral_by=user).count()
        team_members = MLMTree.objects.filter(parent=user)
        team_count = team_members.count()

        base_interest_rate = Decimal('0.01') if investment_type == 'full_payment' else Decimal('0.02')

        if referral_count >= 10 and team_count >= 5:
            eligible_team_count = sum(1 for team in team_members.order_by('level')[:5]
                                      if MLMTree.objects.filter(referral_by=team.user, status='active').count() >= 10)
            if eligible_team_count == 5:
                return Decimal('0.05') if investment_type == 'full_payment' else Decimal('0.10')  # 5x Return

        elif referral_count >= 10:
            return Decimal('0.03') if investment_type == 'full_payment' else Decimal('0.05')  # 3% or 5%

        elif referral_count >= 5:
            return Decimal('0.015') if investment_type == 'full_payment' else Decimal('0.025')  # 1.5% or 2.5%

        return base_interest_rate