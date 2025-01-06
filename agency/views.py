from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import User, Investment, Commission, Reward, RefundPolicy, FundWithdrawal, SuperAgency, Agency, FieldAgent, \
    PPDModel, RewardEarned
from .serializers import (InvestmentSerializer, CommissionSerializer, RewardSerializer,
                          RefundPolicySerializer, FundWithdrawalSerializer, SuperAgencySerializer, AgencySerializer,
                          FieldAgentSerializer, PPDModelSerializer, RewardEarnedSerializer)


class SuperAgencyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = SuperAgency.objects.all()
    serializer_class = SuperAgencySerializer


class AgencyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Agency.objects.all()
    serializer_class = AgencySerializer


class FieldAgentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = FieldAgent.objects.all()
    serializer_class = FieldAgentSerializer


class InvestmentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Investment.objects.all()
    serializer_class = InvestmentSerializer


class CommissionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Commission.objects.all()
    serializer_class = CommissionSerializer


class RewardViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Reward.objects.all()
    serializer_class = RewardSerializer


class RefundViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = RefundPolicy.objects.all()
    serializer_class = RefundPolicySerializer


class PPDModelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = PPDModel.objects.all()
    serializer_class = PPDModelSerializer


class FundWithdrawalViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = FundWithdrawal.objects.all()
    serializer_class = FundWithdrawalSerializer


class RewardEarnedViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = RewardEarned.objects.all()
    serializer_class = RewardEarnedSerializer
