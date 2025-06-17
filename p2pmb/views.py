import datetime
from collections import deque
from decimal import Decimal

from django.db.models import Sum
from django.utils.dateparse import parse_date
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers, status, viewsets
from rest_framework.filters import SearchFilter
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agency.models import Investment, RewardEarned
from p2pmb.calculation import (RoyaltyClubDistribute, DistributeDirectCommission, DistributeLevelIncome,
                               LifeTimeRewardIncome, ProcessMonthlyInterestP2PMB)
from p2pmb.cron import distribute_level_income
from p2pmb.models import MLMTree, Package, Commission, ExtraReward, CoreIncomeEarned, P2PMBRoyaltyMaster, RoyaltyEarned
from p2pmb.serializers import MLMTreeSerializer, MLMTreeNodeSerializer, PackageSerializer, CommissionSerializer, \
    ShowInvestmentDetail, GetP2PMBLevelData, GetMyApplyingData, MLMTreeNodeSerializerV2, MLMTreeParentNodeSerializerV2, \
    ExtraRewardSerializer, CoreIncomeEarnedSerializer, RoyaltyEarnedSerializer, P2PMBRoyaltyMasterSerializer, \
    CreateRoyaltyEarnedSerializer, TransactionSerializer, GetDirectUserSerializer
from payment_app.models import Transaction, UserWallet


# Create your views here.


class MLMTreeCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Handle the creation of a new child in the MLM tree.

        Validate the input and add the child to the appropriate position.
        """
        serializer = MLMTreeSerializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.create(serializer.validated_data)
                return Response({'message': 'Congratulations, You are now member in Person 2 Person modal. '},
                                status=status.HTTP_200_OK)
            except serializers.ValidationError as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MLMTreeView(APIView):
    """
    API to retrieve the MLM tree structure.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        master_node = MLMTree.objects.filter(parent=None).select_related('child', 'parent', 'referral_by').first()
        if not master_node:
            return Response({"detail": "Error"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = MLMTreeNodeSerializer(master_node)
        return Response(serializer.data)


class MLMTreeViewV2(APIView):
    """
    API to retrieve the MLM tree structure.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        child = request.query_params.get('child', None)
        show_parent = request.query_params.get('show_parent', False)
        if not child:
            master_node = MLMTree.objects.filter(level=12, position=1, is_show=True).select_related(
                'child', 'parent', 'referral_by').first()
            # master_node = MLMTree.objects.filter(parent=None, is_show=True).select_related(
            #     'child', 'parent', 'referral_by').first()
            if not master_node:
                return Response({"detail": "Error"}, status=status.HTTP_400_BAD_REQUEST)
            serializer = MLMTreeNodeSerializerV2(master_node)
            return Response(serializer.data)
        else:
            if not show_parent:
                master_node = MLMTree.objects.filter(parent=child, is_show=True).select_related('child', 'parent',
                                                                                                'referral_by')
                serializer = MLMTreeNodeSerializerV2(master_node, many=True)
            else:
                master_node = MLMTree.objects.filter(child=child, is_show=True).select_related('child', 'parent',
                                                                                               'referral_by')
                serializer = MLMTreeParentNodeSerializerV2(master_node, many=True)

            return Response(serializer.data)


class GetUserDirectTeamAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GetDirectUserSerializer

    def get_queryset(self):
        return MLMTree.objects.filter(
            referral_by=self.request.user, is_show=True
        ).select_related('child', 'parent', 'referral_by').order_by('-id')


class GetTDSAmountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet = UserWallet.objects.filter(user=request.user).order_by('-id').last()

        if wallet:
            return Response({"tds_amount": wallet.tds_amount})
        else:
            return Response({"tds_amount": 0})


class GetParentLevelsView(APIView):
    """
    API to get up to 20 levels of parent users above the given child ID.
    """
    permission_classes = [IsAuthenticated]

    def get_levels_above(self, user, max_levels=20):
        """ Retrieve up to 20 levels of parent users. """
        current_user = user.parent
        levels = []
        level_count = 0

        while level_count < max_levels and current_user:
            parent = MLMTree.objects.filter(child=current_user, status='active', is_show=True).first()
            if not parent or not parent.parent:
                break

            levels.append(parent)
            current_user = parent.parent
            level_count += 1

        return levels

    def get_users_below(self, user, max_levels=10):
        """
        Retrieves child users up to a maximum depth of `max_levels`.
        """
        levels = []
        current_user = user.child
        distributed_levels = 0

        while distributed_levels < max_levels:
            children = MLMTree.objects.filter(parent=current_user, status='active', is_show=True).first()

            if not children:
                break

            levels.append(children)
            distributed_levels += 1

            if distributed_levels >= max_levels:
                break

            current_user = children.child

        return levels

    def get(self, request):
        """
        Get parent hierarchy for a given child user up to 20 levels.
        """
        level = request.query_params.get('level')
        user = MLMTree.objects.filter(child=self.request.user, status='active', is_show=True).last()
        if not user:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        if level == 'up':
            users = self.get_levels_above(user)
        elif level == 'down':
            users = self.get_users_below(user)
        else:
            return Response({"error": "Invalid level type"}, status=status.HTTP_404_NOT_FOUND)
        serialized_data = GetP2PMBLevelData(users, many=True).data
        return Response(serialized_data, status=status.HTTP_200_OK)


class PackageBuyView(APIView):
    """
    API to retrieve the MLM tree structure.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        do_investment = Investment.objects.filter(user=self.request.user, package__isnull=False)
        if do_investment.exists():
            return Response({"message": True}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"message": False}, status=status.HTTP_400_BAD_REQUEST)


class GetUserDetailsView(APIView):
    """
    API to get the user details according to the child id.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        child_id = request.query_params.get('child_id')

        if not child_id:
            return Response({"error": "child_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        get_user_details = Investment.objects.filter(user=child_id, package__isnull=False).last()
        if get_user_details:
            serializer = ShowInvestmentDetail(get_user_details, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid User Id."}, status=status.HTTP_400_BAD_REQUEST)


class MyApplying(APIView):
    """
    API to get my applying.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = MLMTree.objects.filter(child=self.request.user, status='active', is_show=True).last()
        serializer = GetMyApplyingData(user, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PackageViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PackageSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name', 'applicable_for']
    filterset_fields = ['applicable_for', ]
    queryset = Package.objects.all()

    def get_queryset(self):
        return Package.objects.filter(status='active')

    def get_serializer_context(self):
        """Pass the user context to the serializer"""
        context = super().get_serializer_context()
        context['user'] = None
        return context


class CommissionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CommissionSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    queryset = Commission.objects.all()
    filterset_fields = ['commission_type', 'commission_to', 'commission_by']

    def get_queryset(self):
        return Commission.objects.filter(status='active', commission_to=self.request.user).order_by('-date_created')

    def get_level_difference(self, from_user_id, to_user_id):
        """Find level difference between from_user and to_user. Tries downline first, then upline."""

        # 1. Try Downline Traversal (BFS)
        visited = set()
        queue = deque([(from_user_id, 0)])  # (user_id, level)

        while queue:
            current_user_id, level = queue.popleft()
            if current_user_id in visited:
                continue
            visited.add(current_user_id)

            children = MLMTree.objects.filter(parent=current_user_id, status='active', is_show=True)
            for entry in children:
                child_id = entry.child.id
                if child_id == to_user_id:
                    return level + 1
                queue.append((child_id, level + 1))

        # 2. Try Upline Traversal (BFS)
        visited = set()
        queue = deque([(from_user_id, 0)])

        while queue:
            current_user_id, level = queue.popleft()
            if current_user_id in visited:
                continue
            visited.add(current_user_id)

            parents = MLMTree.objects.filter(child=current_user_id, status='active', is_show=True)
            for entry in parents:
                parent_id = entry.parent.id
                if parent_id == to_user_id:
                    return level + 1
                queue.append((parent_id, level + 1))

        return None

    def list(self, request, *args, **kwargs):
        """ Add MLM levels only if `commission_type` is 'level'. """
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        serialized_data = self.get_serializer(page, many=True).data if page is not None else self.get_serializer(
            queryset, many=True).data

        for item in serialized_data:
            if item["commission_type"] == "level":
                commission_by_user = item["commission_by"]
                if commission_by_user == request.user.id:
                    item["show_level"] = 0
                else:
                    level = self.get_level_difference(request.user.id, commission_by_user)
                    item["show_level"] = level

        if page is not None:
            return self.get_paginated_response(serialized_data)
        return Response(serialized_data)


class ExtraRewardViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ExtraRewardSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    queryset = ExtraReward.objects.all()
    filterset_fields = ['reward_type',]

    def get_queryset(self):
        return ExtraReward.objects.filter(status='active', start_date__lte=datetime.datetime.now().date(),
                                          end_date__gte=datetime.datetime.now().date()).order_by('turnover_amount')


class CoreIncomeEarnedViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CoreIncomeEarnedSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    queryset = CoreIncomeEarned.objects.active()
    filterset_fields = ['income_type',]


class P2PMBRoyaltyMasterViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = P2PMBRoyaltyMasterSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    queryset = P2PMBRoyaltyMaster.objects.active()
    filterset_fields = ['is_distributed',]


class RoyaltyEarnedViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_classes = {
        'list': RoyaltyEarnedSerializer,
        'retrieve': RoyaltyEarnedSerializer,
    }
    default_serializer_class = CreateRoyaltyEarnedSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    queryset = RoyaltyEarned.objects.active()
    filterset_fields = ['club_type', 'is_paid']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']

    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.default_serializer_class)


class DistributeLevelIncomeAPIView(APIView):
    """
    API to distribute level income.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        distribute_level_income()
        # investment_id = request.data.get('investment_id')
        # investment_instance = Investment.objects.filter(
        #     id=investment_id, status='active', is_approved=True, pay_method='main_wallet', investment_type='p2pmb',
        #     send_level_income=False
        # ).last()
        # if investment_instance and investment_instance.user:
        #     instance = MLMTree.objects.filter(status='active', child=investment_instance.user).last()
        #     if instance:
        #         amount = investment_instance.amount if investment_instance.amount else 0
        #         DistributeLevelIncome.distribute_level_income(instance, amount)
        #         investment_instance.send_level_income = True
        #         investment_instance.save()
        #         return Response({'message': 'Payment of Level Income Distribute successfully.'},
        #                         status=status.HTTP_200_OK)
        #     return Response({'message': 'This user is not enroll in MLM model.'},
        #                     status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': 'This user is not invest any amount yet.'},
                        status=status.HTTP_400_BAD_REQUEST)


class CommissionMessageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        commissions = Commission.objects.filter(commission_type='level')
        for commission in commissions:
            commission.description = f"Level Commission added while adding {commission.commission_by.username}"
            commission.save()

        return Response({'message': 'Update Message.'}, status=status.HTTP_200_OK)


class DistributeDirectIncome(APIView):
    """
    API to distribute level income.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        investment_id = request.data.get('investment_id')
        investment_instance = Investment.objects.filter(
            id=investment_id, status='active', is_approved=True, pay_method='main_wallet', investment_type='p2pmb',
            send_direct_income=False
        ).last()
        if investment_instance and investment_instance.user:
            instance = MLMTree.objects.filter(status='active', child=investment_instance.user).last()
            if instance:
                DistributeDirectCommission.distribute_p2pmb_commission(instance, investment_instance.amount)
                investment_instance.send_direct_income = True
                investment_instance.save()
                return Response({'message': 'Payment of Direct Income Distribute successfully.'},
                                status=status.HTTP_200_OK)
            return Response({'message': 'This user is not enroll in MLM model.'},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': 'This user is not invest any amount.'},
                        status=status.HTTP_400_BAD_REQUEST)


class LifeTimeRewardIncomeAPIView(APIView):
    """
    API to distribute level income.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # calculate_lifetime_reward_income_task()
        # process_monthly_reward_payments()
        LifeTimeRewardIncome.check_and_allocate_rewards()
        return Response({"message": "successful earned life time Income"})


class MonthlyDistributeDirectIncome(APIView):
    """
    API to distribute level income.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        DistributeDirectCommission.cron_send_monthly_payment_direct_income()
        return Response({"message": "successful send Income"})


class RoyaltyIncome(APIView):
    """
    API to distribute level income.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        RoyaltyClubDistribute.distribute_royalty()
        return Response({"message": "Royalty income distribute successfully."})


class SendMonthlyInterestIncome(APIView):
    """
    API to distribute level income.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ProcessMonthlyInterestP2PMB.generate_interest_for_all_investments()
        return Response({"message": "Monthly Interest distribute successfully."})


class GetAllPayout(ListAPIView):
    '''
    This API is used to get all the payout which we send to user.
    '''
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Transaction.objects.filter(
            receiver=user, transaction_type__in=('reward', 'commission', 'rent', 'interest')
        ).order_by('-created_at')

        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if start_date:
            queryset = queryset.filter(created_at__date__gte=parse_date(start_date))
        if end_date:
            queryset = queryset.filter(created_at__date__lte=parse_date(end_date))

        return queryset


class GetParentLevelCountView(APIView):
    """
    API to get the count of parent and child levels.
    """
    permission_classes = [IsAuthenticated]

    def get_levels_above_count(self, user):
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

    def count_all_descendants(self, user):
        """
        Recursively count all child users at all levels.
        """
        children = MLMTree.objects.filter(parent=user, status='active', is_show=True)
        count = children.count()

        for child in children:
            count += self.count_all_descendants(child.child)

        return count

    def get(self, request):
        """
        Get the count of parent and child levels.
        """
        user = MLMTree.objects.filter(child=self.request.user, status='active', is_show=True).last()
        if not user:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        upper_count = self.get_levels_above_count(user)
        lower_count = self.count_all_descendants(user.child)

        return Response({
            "upper_count": upper_count,
            "lower_count": lower_count
        }, status=status.HTTP_200_OK)


class GetTopUpInvestment(APIView):
    '''
    This API is used to get all the payout which we send to user.
    '''
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        get_investment = Investment.objects.filter(status='active', user=self.request.user, package__isnull=False,
                                                   investment_type='p2pmb', pay_method='main_wallet',
                                                   is_approved=True).distinct()
        total_top_up = get_investment.count()
        if total_top_up < 2:
            return Response({'message': 'No top-up found. You need at least two active investments to view top-up '
                                        'details.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            get_top_up_detail = get_investment.last()
            packages = get_top_up_detail.package.all()
            total_package_amount = packages.aggregate(total=Sum('amount'))['total'] or 0
            response = {
                'total_top_up': total_top_up,
                'top_up_amount': total_package_amount,
                'top_up_at': get_top_up_detail.date_created
            }
            return Response(response, status=status.HTTP_200_OK)


class MyIdValueAPIView(APIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        get_investment = Investment.objects.filter(status='active', user=self.request.user, package__isnull=False,
                                                   investment_type='p2pmb').last()
        check_working_id = MLMTree.objects.filter(referral_by=self.request.user).count()
        if check_working_id and check_working_id >= 2:
            is_working_id = True
            total_return_amount = (get_investment.amount or 0) * 4.4
        else:
            is_working_id = False
            total_return_amount = (get_investment.amount or 0) * 2.1

        total_income_earned = Commission.objects.filter(commission_to=request.user).aggregate(
            total_amount=Sum('amount'))['total_amount'] or Decimal(0)

        current_due_value = total_return_amount - total_income_earned
        twenty_percentage_of_value = total_return_amount * Decimal(0.20)

        if current_due_value > twenty_percentage_of_value:
            is_low_balance = False
        else:
            is_low_balance = True

        response = {
            'investment_amount': get_investment.amount,
            'is_working_id': is_working_id,
            'total_return_amount': total_return_amount,
            'total_income_earned': total_income_earned,
            'current_due_values': current_due_value,
            'is_low_balance': is_low_balance,
        }
        return Response(response, status=status.HTTP_200_OK)