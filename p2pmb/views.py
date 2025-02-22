from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers, status, viewsets
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agency.models import Investment
from p2pmb.calculation import (RoyaltyClubDistribute, DistributeDirectCommission, DistributeLevelIncome,
                               LifeTimeRewardIncome)
from p2pmb.models import MLMTree, Package
from p2pmb.serializers import MLMTreeSerializer, MLMTreeNodeSerializer, PackageSerializer


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
        master_node = MLMTree.objects.filter(parent=None).first()
        if not master_node:
            return Response({"detail": "Error"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = MLMTreeNodeSerializer(master_node)
        return Response(serializer.data)


class PackageViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PackageSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name',]
    queryset = Package.objects.all()

    def get_queryset(self):
        return Package.objects.filter(status='active')


class DistributeLevelIncomeAPIView(APIView):
    """
    API to distribute level income.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_id = request.data.get('user_id')
        investment_id = request.data.get('investment_id')
        investment_instance = Investment.objects.filter(id=investment_id, status='active', is_approved=True).last()
        instance = MLMTree.objects.filter(status='active', child=user_id).last()
        if not instance or not investment_instance:
            return Response({'message': "Either you did not do investment or your investment in progress"},
                            status=status.HTTP_400_BAD_REQUEST)
        elif instance.send_level_income:
            return Response({'message': "We already send commission to this user."},
                            status=status.HTTP_400_BAD_REQUEST)
        amount = investment_instance.amount if investment_instance.amount else 0
        DistributeLevelIncome.distribute_level_income(instance, amount)
        return Response({'message': "Payment of Level Income Distribute successfully."},
                        status=status.HTTP_400_BAD_REQUEST)


class DistributeDirectIncome(APIView):
    """
    API to distribute level income.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_id = request.data.get('user_id')
        investment_id = request.data.get('investment_id')
        investment_instance = Investment.objects.filter(id=investment_id, status='active', is_approved=True).last()
        instance = MLMTree.objects.filter(status='active', child=user_id).last()
        if not instance or not investment_instance:
            return Response({'message': "Invalid id"}, status=status.HTTP_400_BAD_REQUEST)
        elif instance.send_direct_income:
            return Response({'message': "We already send commission to this user."}, status=status.HTTP_400_BAD_REQUEST)
        DistributeDirectCommission.distribute_p2pmb_commission(instance, investment_instance.amount)
        return Response({'message': 'Payment of Direct Income Distribute successfully.'}, status=status.HTTP_200_OK)


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
        # process_monthly_reward_payments()
        return Response({"message": "Royalty income distribute successfully."})