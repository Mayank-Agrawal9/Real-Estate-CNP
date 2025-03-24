from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers, status, viewsets
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agency.models import Investment
from p2pmb.calculation import (RoyaltyClubDistribute, DistributeDirectCommission, DistributeLevelIncome,
                               LifeTimeRewardIncome, ProcessMonthlyInterestP2PMB)
from p2pmb.cron import distribute_level_income
from p2pmb.models import MLMTree, Package, Commission
from p2pmb.serializers import MLMTreeSerializer, MLMTreeNodeSerializer, PackageSerializer, CommissionSerializer, \
    ShowInvestmentDetail, GetP2PMBLevelData, GetMyApplyingData, MLMTreeNodeSerializerV2, MLMTreeParentNodeSerializerV2


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
        context['user'] = self.request.user
        return context


class CommissionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CommissionSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    queryset = Commission.objects.all()
    filterset_fields = ['commission_type', 'commission_to', 'commission_by']

    def get_queryset(self):
        return Commission.objects.filter(status='active', commission_to=self.request.user).order_by('-date_created')

    def list(self, request, *args, **kwargs):
        """ Add MLM levels only if `commission_type` is 'level'. """
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serialized_data = self.get_serializer(page, many=True).data
        else:
            serialized_data = self.get_serializer(queryset, many=True).data

        for item in serialized_data:
            if item["commission_type"] == "level":
                commission_by_user = item["commission_by"]
                mlm_entry = MLMTree.objects.filter(child=commission_by_user, status='active', is_show=True).first()

                if mlm_entry:
                    item["show_level"] = mlm_entry.show_level
                else:
                    item["show_level"] = None

        if page is not None:
            return self.get_paginated_response(serialized_data)

        return Response(serialized_data)


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


class RoyaltyIncome(APIView):
    """
    API to distribute level income.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        RoyaltyClubDistribute.check_royalty_club_membership()
        return Response({"message": "Royalty income distribute successfully."})


class SendMonthlyInterestIncome(APIView):
    """
    API to distribute level income.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ProcessMonthlyInterestP2PMB.process_p2pmb_monthly_interest()
        return Response({"message": "Monthly Interest distribute successfully."})


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