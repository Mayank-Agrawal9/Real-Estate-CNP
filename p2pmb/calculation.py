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
from p2pmb.helpers import create_transaction_entry, create_commission_entry
from p2pmb.models import MLMTree, ScheduledCommission, Commission, RoyaltyClub, Reward, P2PMBRoyaltyMaster, \
    RoyaltyEarned
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
                                                                          is_paid=False)
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
                    f'Level Commission added by {base_user.child.username}'
                )

                # Create commission record
                create_commission_entry(child.child, base_user.child, 'level', commission,
                                        f'Commission added for {base_user.child.username}')

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

    # New Working
    @staticmethod
    def distribute_royalty():
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

        return {"status": "success", "message": f"Royalty distributed among {total_users} users"}


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
        """Example function to calculate monthly interest."""
        interest_rate = ProcessMonthlyInterestP2PMB.calculate_interest_rate(user, investment_type)
        print(interest_rate, "interest_rate")
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
        if today.day != 1 or (today.month <= 3 and today.year <= 2025):
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
                        interest_send_date=today,
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
            return Decimal('0.05') if investment_type == 'full_payment' else Decimal('1.0')

        # 4. Check for 3x: From direct referrals, any 5 have ≥10 referrals
        if referral_count >= 10:
            high_performers_in_directs = sum(
                1 for referral in direct_referrals
                if MLMTree.objects.filter(referral_by=referral.child).count() >= 10
            )
            if high_performers_in_directs >= 5:
                return Decimal('0.03') if investment_type == 'full_payment' else Decimal('0.6')  # 3x

            return Decimal('0.02') if investment_type == 'full_payment' else Decimal('0.4')  # 2x

        # 5. Check for 1.5x
        if referral_count >= 5:
            return Decimal('0.015') if investment_type == 'full_payment' else Decimal('0.3')  # 1.5x

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