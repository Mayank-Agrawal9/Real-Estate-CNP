import datetime
from collections import deque
from decimal import Decimal

from django.db.models import Sum, Q, Max
from django.db.models.functions import TruncMonth
from django.utils.dateparse import parse_date
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.generics import ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from agency.models import Investment, RewardEarned, InvestmentInterest
from notification.models import InAppNotification
from p2pmb.calculation import (RoyaltyClubDistribute, DistributeDirectCommission, DistributeLevelIncome,
                               LifeTimeRewardIncome, ProcessMonthlyInterestP2PMB)
from p2pmb.cron import distribute_level_income, distribute_direct_income
from p2pmb.helpers import get_downline_count, count_all_descendants, get_levels_above_count, ExtraRewardFilter, \
    PackagePagination
from p2pmb.models import MLMTree, Package, Commission, ExtraReward, CoreIncomeEarned, P2PMBRoyaltyMaster, RoyaltyEarned, \
    ExtraRewardEarned, HoldLevelIncome, ROIOverride, LapsedAmount
from p2pmb.serializers import MLMTreeSerializer, MLMTreeNodeSerializer, PackageSerializer, CommissionSerializer, \
    ShowInvestmentDetail, GetP2PMBLevelData, GetMyApplyingData, MLMTreeNodeSerializerV2, MLMTreeParentNodeSerializerV2, \
    ExtraRewardSerializer, CoreIncomeEarnedSerializer, RoyaltyEarnedSerializer, P2PMBRoyaltyMasterSerializer, \
    CreateRoyaltyEarnedSerializer, TransactionSerializer, GetDirectUserSerializer, HoldLevelIncomeSerializer, \
    ROIOverRideSerializer, LapsedAmountSerializer, ROIOverrideListSerializer, InvestmentInterestSerializer
from payment_app.models import Transaction, UserWallet, TDSSubmissionLog


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


class DiIncomeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        distribute_direct_income()
        return Response({'m': 'Done'})


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
            return Response({"message": True}, status=status.HTTP_200_OK)
        else:
            return Response({"message": False}, status=status.HTTP_200_OK)


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
    permission_classes = [AllowAny]
    serializer_class = PackageSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name', 'applicable_for']
    filterset_fields = ['applicable_for']
    queryset = Package.objects.all()
    pagination_class = PackagePagination

    def get_queryset(self):
        return Package.objects.filter(status='active').order_by('amount')

    def get_serializer_context(self):
        """Pass the user context to the serializer"""
        context = super().get_serializer_context()
        user = self.request.user if self.request.user.is_authenticated else None
        print(user)
        context['user'] = user

        if user:
            max_amount = (
                Investment.objects.filter(user=user, status='active', package__isnull=False).select_related(
                    'package').aggregate(max_amount=Max('amount')).get('max_amount') or 0
            )
            print(max_amount, "max_amount")
        else:
            max_amount = 0

        context['max_bought_amount'] = max_amount
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
        queryset = self.filter_queryset(self.get_queryset())
        commission_type = request.query_params.get('commission_type')

        total_amount = 0
        if commission_type:
            total_amount = queryset.filter(commission_type=commission_type).aggregate(
                total_amount=Sum('amount')
            )['total_amount'] or 0

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
            response = self.get_paginated_response(serialized_data)
            if commission_type:
                response.data[f"total_{commission_type}_amount"] = total_amount
            return response

        response_data = {"results": serialized_data}
        if commission_type:
            response_data[f"total_{commission_type}_amount"] = total_amount

        return Response(response_data)


class ExtraRewardViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ExtraRewardSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    queryset = ExtraReward.objects.all()
    filterset_class = ExtraRewardFilter

    def get_queryset(self):
        return ExtraReward.objects.filter(status='active').order_by('turnover_amount')

    def get_serializer_context(self):
        """Pass the user context to the serializer"""
        context = super().get_serializer_context()
        context['user'] = self.request.user
        return context


class HoldLevelIncomeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = HoldLevelIncomeSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['level_type',]

    def get_queryset(self):
        return HoldLevelIncome.objects.filter(status='active',
                                              commission_to=self.request.user, release_status='on_hold').order_by(
            'date_created')


class ROIOverrideViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ROIOverRideSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['action_type',]

    def get_queryset(self):
        return ROIOverride.objects.filter(status='active').order_by('date_created')

    def get_serializer_class(self):
        if self.action == 'list':
            return ROIOverrideListSerializer
        return ROIOverRideSerializer

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        InAppNotification.objects.create(
            user=instance.user, message=instance.reason, created_by=self.request.user, notification_type='alert'
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class LapsedAmountViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = LapsedAmountSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['earned_type', 'user', 'date_created']

    def get_queryset(self):
        return LapsedAmount.objects.filter(status='active').order_by('date_created')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=False, methods=['get'], url_path='aggregate')
    def get_agreed_amount(self, request):
        month = request.query_params.get('month')
        year = request.query_params.get('year')

        earned_types = ['level_income', 'core_group_income', 'royalty']

        queryset = self.get_queryset().filter(earned_type__in=earned_types)

        if month:
            queryset = queryset.filter(date_created__month=month)
        if year:
            queryset = queryset.filter(date_created__year=year)

        response_data = {
            "month": month or "All",
            "year": year or "All"
        }

        for etype in earned_types:
            total = queryset.filter(earned_type=etype).aggregate(total_agreed=Sum('amount'))['total_agreed'] or 0
            response_data[etype] = total

        return Response(response_data)


class CoreIncomeEarnedViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CoreIncomeEarnedSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    queryset = CoreIncomeEarned.objects.active()
    filterset_fields = ['income_type', 'core_income', 'user', 'core_income__month', 'core_income__year']

    def get_queryset(self):
        return CoreIncomeEarned.objects.filter(status='active', user=self.request.user).order_by('income_earned')


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
    queryset = RoyaltyEarned.objects.filter(status='active')
    filterset_fields = ['club_type', 'is_paid']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']

    def get_queryset(self):
        return RoyaltyEarned.objects.filter(user=self.request.user, status='active').order_by('earned_date')

    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.default_serializer_class)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        total_royalty_income = queryset.aggregate(
            total=Sum('earned_amount'))['total'] or 0

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data['total_royalty_income'] = total_royalty_income
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "results": serializer.data,
            "total_royalty_income": total_royalty_income
        })


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
        ).order_by('-date_created')

        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if start_date:
            queryset = queryset.filter(created_at__date__gte=parse_date(start_date))
        if end_date:
            queryset = queryset.filter(created_at__date__lte=parse_date(end_date))

        return queryset


class ROIListView(ListAPIView):
    '''
    This API is used to get all the payout which we send to user.
    '''
    serializer_class = InvestmentInterestSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['interest_send_date', ]

    def get_queryset(self):
        interest = InvestmentInterest.objects.filter(status='active', investment__user=self.request.user)

        month = self.request.query_params.get("month")
        year = self.request.query_params.get("year")

        if month:
            interest = interest.filter(interest_send_date__month=month)
        if year:
            interest = interest.filter(interest_send_date__year=year)

        return interest

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        total_interest_income = queryset.aggregate(
            total=Sum('interest_amount'))['total'] or 0

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data['total_interest_amount'] = total_interest_income
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "results": serializer.data,
            "total_interest_amount": total_interest_income
        })


class GetParentLevelCountView(APIView):
    """
    API to get the count of parent and child levels.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get the count of parent and child levels.
        """
        user = MLMTree.objects.filter(child=self.request.user, status='active', is_show=True).last()
        if not user:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        upper_count = get_levels_above_count(user)
        lower_count = count_all_descendants(user.child)

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
        total_invested_amount = Investment.objects.filter(status='active', user=self.request.user,
                                                          package__isnull=False, investment_type='p2pmb').aggregate(
            total=Sum('amount'))['total'] or Decimal(0)
        check_working_id = MLMTree.objects.filter(referral_by=self.request.user).count()
        if check_working_id and check_working_id >= 2:
            is_working_id = True
            total_return_amount = total_invested_amount * Decimal('4.4')
        else:
            is_working_id = False
            total_return_amount = total_invested_amount * Decimal('2.1')

        total_commission_earned = (
                Commission.objects.filter(status="active", commission_to=request.user,
                                          commission_type__in=['direct', 'level'])
                .aggregate(total_amount=Sum("amount"))["total_amount"] or Decimal(0)
        )

        roi_earned = (
                InvestmentInterest.objects.filter(status="active", investment__user=request.user)
                .aggregate(total_amount=Sum("interest_amount"))["total_amount"] or Decimal(0)
        )

        royalty_earned = (
                RoyaltyEarned.objects.filter(status="active", user=request.user)
                .aggregate(total_amount=Sum("earned_amount"))["total_amount"] or Decimal(0)
        )

        reward_earned = (
                RewardEarned.objects.filter(status="active", user=request.user)
                .aggregate(total_amount=Sum("reward__gift_amount"))["total_amount"] or Decimal(0)
        )

        core_group_income = (
                CoreIncomeEarned.objects.filter(status="active", user=request.user)
                .aggregate(total=Sum("income_earned"))["total"] or Decimal(0)
        )

        extra_income = (
                ExtraRewardEarned.objects.filter(status="active", user=request.user)
                .aggregate(total=Sum("amount"))["total"] or Decimal(0)
        )

        total_income_earned = (
                total_commission_earned + roi_earned + royalty_earned +
                reward_earned + core_group_income + extra_income
        )

        current_due_value = total_return_amount - total_income_earned
        twenty_percentage_of_value = total_return_amount * Decimal(0.20)

        if current_due_value > twenty_percentage_of_value:
            is_low_balance = False
        else:
            is_low_balance = True

        response = {
            'investment_amount': total_invested_amount,
            'is_working_id': is_working_id,
            'total_return_amount': total_return_amount,
            'total_income_earned': total_income_earned,
            'current_due_values': current_due_value,
            'is_low_balance': is_low_balance,
        }
        return Response(response, status=status.HTTP_200_OK)


class GetAppDashboardAggregate(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        mlm_user_entry = MLMTree.objects.filter(is_show=True, child=user).last()
        referrals = MLMTree.objects.filter(is_show=True, referral_by=user).count()
        total_team_count = get_downline_count(user)
        investments = Investment.objects.filter(
            status='active', package__isnull=False, investment_type='p2pmb', user=user
        )
        latest_investment = investments.aggregate(total=Sum('amount'))['total'] or Decimal(0)
        latest_amount = latest_investment if latest_investment else Decimal('0.0')
        total_return_amount = latest_amount * Decimal('4.4' if referrals >= 2 else '2.1')

        commission_agg = Commission.objects.filter(status='active', commission_to=user).aggregate(
            total=Sum('amount'),
            level_total=Sum('amount', filter=Q(commission_type='level')),
            direct_total=Sum('amount', filter=Q(commission_type='direct'))
        )
        commission_amount = commission_agg['total'] or 0
        level_income = commission_agg['level_total'] or 0
        direct_income = commission_agg['direct_total'] or 0

        earned_reward = RewardEarned.objects.filter(
            status='active', user=user, reward__applicable_for='p2pmb'
        ).aggregate(total=Sum('reward__gift_amount'))['total'] or 0

        roi_interest = InvestmentInterest.objects.filter(
            status='active', investment__user=user
        ).aggregate(total=Sum('interest_amount'))['total'] or 0

        royalty_earned = RoyaltyEarned.objects.filter(
            status='active', is_paid=True, user=user
        ).aggregate(total=Sum('earned_amount'))['total'] or 0

        core_group_income = CoreIncomeEarned.objects.filter(
            status='active', user=user
        ).aggregate(total=Sum('income_earned'))['total'] or 0

        extra_income = ExtraRewardEarned.objects.filter(
            status='active', user=user
        ).aggregate(total=Sum('amount'))['total'] or 0

        total_roi_interest = InvestmentInterest.objects.filter(
            status='active', investment__user=user
        ).aggregate(total=Sum('interest_amount'))['total'] or 0

        upper_count = get_levels_above_count(mlm_user_entry)
        lower_count = count_all_descendants(mlm_user_entry.child)
        team_level_count = upper_count + lower_count

        total_earning = (
            commission_amount + earned_reward + roi_interest + royalty_earned + core_group_income + extra_income
        )

        data = {
            'total_team_member': total_team_count,
            'total_earning': total_earning,
            'total_id_value': total_return_amount,
            'total_direct_user_count': referrals,
            'team_level_count': team_level_count,
            'direct_income': direct_income,
            'level_income': level_income,
            'royalty_income': royalty_earned,
            'reward_income': earned_reward,
            'extra_reward_income': extra_income,
            'core_group_income': core_group_income,
            'total_top_up_count': investments.count(),
            'roi_income': total_roi_interest
        }
        return Response(data, status=status.HTTP_200_OK)


class GetUserRoyaltyClubStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    ROYALTY_CLUB_TYPE = (
        ('star', 'Star Club'),
        ('2_star', '2-Star Club'),
        ('3_star', '3-Star Club'),
        ('5_star', '5-Star Club'),
    )

    def get(self, request):
        earned_clubs = set(
            RoyaltyEarned.objects.filter(user=request.user).values_list('club_type', flat=True).distinct()
        )

        response_data = {}
        for club_type, _ in self.ROYALTY_CLUB_TYPE:
            key = f"{club_type}_royalty"
            response_data[key] = club_type in earned_clubs

        return Response(response_data)


class UserTDSAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        month = request.query_params.get("month")
        year = request.query_params.get("year")

        base_filters = {
            'created_by': user, 'transaction_type': 'transfer',
            'status': 'active', 'transaction_status': 'approved'
        }

        total_queryset = Transaction.objects.filter(**base_filters)

        total_tds_amount = total_queryset.aggregate(total_tds_amount=Sum('tds_amount'))['total_tds_amount'] or 0

        total_tds_submitted = (
                TDSSubmissionLog.objects.filter(submitted_for=user)
                .aggregate(total_paid_amount=Sum('amount'))['total_paid_amount'] or 0
        )

        total_tds_pending = total_tds_amount - total_tds_submitted

        monthly_queryset = Transaction.objects.filter(**base_filters)

        date_filters = {}
        if year:
            date_filters['date_created__year'] = year
        if month:
            date_filters['date_created__month'] = month

        if date_filters:
            monthly_queryset = monthly_queryset.filter(**date_filters)

        monthly_data = (
            monthly_queryset.annotate(month=TruncMonth('date_created'))
            .values('month').annotate(total_tds=Sum('tds_amount'))
            .order_by('-month')
        )

        monthly_data_list = list(monthly_data)

        paginator = LimitOffsetPagination()
        paginated_data = paginator.paginate_queryset(monthly_data_list, request)

        response_data = {
            'total_tds_amount': total_tds_amount,
            'total_tds_submitted': total_tds_submitted,
            'total_tds_pending': total_tds_pending,
            'data': paginated_data,
        }

        return paginator.get_paginated_response(response_data)
