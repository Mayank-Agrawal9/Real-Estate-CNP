import datetime
from decimal import Decimal

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Q, Sum
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, permissions, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.filters import SearchFilter
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Profile
from web_admin.models import ManualFund
from web_admin.serializers import ProfileSerializer, InvestmentSerializer, ManualFundSerializer
from agency.models import Investment, SuperAgency, Agency, FieldAgent, FundWithdrawal
from payment_app.models import UserWallet, Transaction


# Create your views here.

class IsStaffUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class StaffLoginAPIView(APIView):
    def post(self, request):
        username = request.data.get('email')
        password = request.data.get('password')

        if not username or not password:
            return Response({'error': 'Username and password are required'}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=username, password=password)

        if user is None:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)

        if not user.is_staff:
            return Response({'error': 'Access denied. Only staff users can log in.'},
                            status=status.HTTP_400_BAD_REQUEST)

        token, created = Token.objects.get_or_create(user=user)
        user_data = {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'token': token.key,
        }

        return Response({'profile': user_data}, status=status.HTTP_200_OK)


class VerifyKycAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        profile = Profile.objects.filter(is_kyc=True, is_kyc_verified=False)
        serializer = ProfileSerializer(profile, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        user_id = request.data.get('user_id')
        with transaction.atomic():
            profile = Profile.objects.filter(user=user_id).last()
            if profile.is_kyc and profile.is_kyc_verified:
                return Response({"message": "KYC is already verified for this user."},
                                status=status.HTTP_400_BAD_REQUEST)
            profile.is_kyc_verified = True
            profile.verified_by = request.user
            profile.verified_on = datetime.datetime.now()
            profile.save()
            return Response({'message': "User KYC verified successfully."}, status=status.HTTP_200_OK)


class InvestmentAPIView(APIView):
    permission_classes = [IsStaffUser]

    def update_user_commission_(self, user, sender, verify_by, remarks, commission_amount):
        wallet, _ = UserWallet.objects.get_or_create(user=user)
        wallet.in_app_wallet += commission_amount
        Transaction.objects.create(
            created_by=user,
            sender=sender,
            amount=commission_amount,
            transaction_type='commission',
            transaction_status='approved',
            verified_by=verify_by,
            verified_on=datetime.datetime.now(),
            remarks=remarks,
            payment_method='wallet'
        )
        wallet.save()

    def get(self, request):
        investment = Investment.objects.filter(is_approved=False).order_by('-date_created')
        serializer = InvestmentSerializer(investment, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        investment_id = request.data.get('investment_id')
        investment = Investment.objects.filter(id=investment_id, is_approved=False).last()
        if not investment:
            return Response({'error': 'Investment not found'}, status=status.HTTP_400_BAD_REQUEST)
        elif investment.is_approved:
            return Response({'error': 'Investment already approved'}, status=status.HTTP_400_BAD_REQUEST)
        elif not investment.user.profile.is_kyc:
            return Response({'error': 'User not do KYC, you cannot approve them.'},
                            status=status.HTTP_400_BAD_REQUEST)
        elif not investment.user.profile.is_kyc_verified:
            return Response({'error': 'Please first verify kyc.'}, status=status.HTTP_400_BAD_REQUEST)

        investment.is_approved = True
        investment.approved_by = request.user
        investment.approved_on = datetime.datetime.now()
        investment.save()

        wallet, _ = UserWallet.objects.get_or_create(user=investment.user)
        wallet.main_wallet_balance += investment.amount
        wallet.save()
        # if investment.user.profile.role == 'agency':
        #     agency = Agency.objects.filter(created_by=investment.user).last()
        #     if agency and agency.company:
        #         commission = Decimal(str(investment.amount * 0.25))
        #         self.update_user_commission_(
        #             user=agency.company.profile.user,
        #             sender=investment.user,
        #             verify_by=request.user,
        #             remarks='Commission added due to agency added.',
        #             commission_amount=commission
        #         )
        # elif investment.user.profile.role == 'field_agent':
        #     field_agent = FieldAgent.objects.filter(profile=investment.user.profile).last()
        #     if field_agent and field_agent.agency:
        #         commission = Decimal(str(investment.amount * 0.25))
        #         self.update_user_commission_(
        #             user=field_agent.agency.created_by,
        #             sender=investment.user,
        #             verify_by=request.user,
        #             remarks='Commission added due to field agent added.',
        #             commission_amount=commission
        #         )
        #         if field_agent.agency.company:
        #             commission = Decimal(str(investment.amount * 0.05))
        #             self.update_user_commission_(
        #                 user=field_agent.agency.company.profile.user,
        #                 sender=investment.user,
        #                 verify_by=request.user,
        #                 remarks='Commission added due to field agent added.',
        #                 commission_amount=commission
        #             )
        return Response({'message': 'Investment approved successfully'}, status=status.HTTP_200_OK)


class CreateManualInvestmentAPIView(APIView):
    permission_classes = [IsStaffUser]

    def post(self, request):
        user_id = request.data.get('user_id')
        amount = Decimal(request.data.get('amount'))
        password = request.data.get('password', None)
        user_profile = Profile.objects.filter(user=user_id).last()
        if not user_profile:
            return Response({'error': 'User id not found'}, status=status.HTTP_400_BAD_REQUEST)

        if password and password != request.user.profile.payment_password:
            return Response({'error': 'Incorrect Password'}, status=status.HTTP_400_BAD_REQUEST)

        wallet, _ = UserWallet.objects.get_or_create(user=user_profile.user)
        wallet.main_wallet_balance += amount
        wallet.save()

        Transaction.objects.create(
            created_by=user_profile.user,
            sender=user_profile.user,
            receiver=user_profile.user,
            amount=amount,
            transaction_type='deposit',
            transaction_status='approved',
            verified_by=request.user,
            verified_on=datetime.datetime.now(),
            payment_method='upi'
        )
        Investment.objects.create(
            created_by=user_profile.user,
            user=user_profile.user,
            amount=amount,
            investment_type='p2pmb',
            pay_method='new',
            gst=0,
            is_approved=True,
            approved_by=request.user,
            approved_on=datetime.datetime.now(),
        )
        ManualFund.objects.create(
            created_by=user_profile.user,
            added_to=user_profile.user,
            amount=amount
        )
        return Response({'message': 'Fund Deduct successfully.'}, status=status.HTTP_200_OK)


class DeductManualInvestmentAPIView(APIView):
    permission_classes = [IsStaffUser]

    def post(self, request):
        user_id = request.data.get('user_id')
        amount = Decimal(request.data.get('amount'))
        user_profile = Profile.objects.filter(user=user_id).last()
        if not user_profile:
            return Response({'error': 'User id not found'}, status=status.HTTP_400_BAD_REQUEST)

        wallet, _ = UserWallet.objects.get_or_create(user=user_profile.user)
        wallet.main_wallet_balance -= amount
        wallet.save()

        Transaction.objects.create(
            created_by=user_profile.user,
            sender=user_profile.user,
            receiver=user_profile.user,
            amount=amount,
            transaction_type='deduct',
            transaction_status='approved',
            verified_by=request.user,
            verified_on=datetime.datetime.now(),
            payment_method='wallet'
        )
        Investment.objects.create(
            created_by=user_profile.user,
            user=user_profile.user,
            amount=amount,
            investment_type='deduct',
            pay_method='new',
            gst=0,
            is_approved=True,
            approved_by=request.user,
            approved_on=datetime.datetime.now(),
        )
        ManualFund.objects.create(
            created_by=user_profile.user,
            added_to=user_profile.user,
            amount=amount,
            fund_type='deduct'
        )
        return Response({'message': 'Fund Deduct successfully.'}, status=status.HTTP_200_OK)


class GetUserAPIView(ListAPIView):
    permission_classes = [IsStaffUser]
    queryset = Profile.objects.filter(status='active', user__is_staff=False).order_by('-user__id')
    serializer_class = ProfileSerializer
    pagination_class = None


class ManualFundViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffUser]
    queryset = ManualFund.objects.filter(status='active').order_by('-date_created')
    serializer_class = ManualFundSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['amount', ]
    pagination_class = None


class DashboardCountAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        user_counts = User.objects.aggregate(
            all_user=Count("id"),
            active_user=Count("id", filter=Q(is_active=True)),
            inactive_user=Count("id", filter=Q(is_active=False)),
            staff_user=Count("id", filter=Q(is_staff=True)),
        )

        investment_data = Investment.objects.aggregate(
            investment_approved_user=Count("user", distinct=True, filter=Q(is_approved=True)),
            p2pmb_fund_added=Sum("amount", filter=Q(is_approved=True, investment_type="p2pmb")),
            super_agency_fund_added=Sum("amount", filter=Q(is_approved=True, investment_type="super_agency")),
            agency_fund_added=Sum("amount", filter=Q(is_approved=True, investment_type="agency")),
            field_agent_fund_added=Sum("amount", filter=Q(is_approved=True, investment_type="field_agent")),
            pending_approval_payment=Sum("amount", filter=Q(is_approved=False)),
        )

        fund_withdraw = FundWithdrawal.objects.aggregate(
            total_distinct_withdraw_user=Count("user", distinct=True),
            pending_withdraw_amount=Sum("withdrawal_amount", filter=Q(is_paid=False)),
            initiate_withdraw_amount=Sum("withdrawal_amount", filter=Q(is_paid=True)),
            total_withdraw_amount=Sum("withdrawal_amount"),
        )

        admin_paid_amount = ManualFund.objects.filter(status="active").aggregate(Sum("amount"))["amount__sum"]
        dashboard_count = {
            **user_counts,
            **investment_data,
            **fund_withdraw,
            "admin_paid_amount": admin_paid_amount or 0,
        }
        return Response(dashboard_count, status=status.HTTP_200_OK)


class UpdatePasswordView(APIView):
    permission_classes = [IsStaffUser]

    def post(self, request):
        user = request.user
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")

        if not old_password or not new_password or not confirm_password:
            return Response({"error": "All fields are required."}, status=status.HTTP_400_BAD_REQUEST)

        if not check_password(old_password, user.payment_password):
            return Response({"error": "Old password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_password:
            return Response({"error": "New password and confirm password do not match."},
                            status=status.HTTP_400_BAD_REQUEST)

        user.password = make_password(new_password)
        user.save()

        return Response({"message": "Password updated successfully."}, status=status.HTTP_200_OK)

