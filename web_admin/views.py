import datetime
from collections import defaultdict
from datetime import timedelta, date
from decimal import Decimal

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.db.models import Count, Q, Sum
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, permissions, viewsets, generics
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.generics import ListAPIView, GenericAPIView
from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Profile, BankDetails, UserPersonalDocument, ChangeRequest
from master.models import CoreGroupIncome, RewardMaster
from notification.models import InAppNotification
from p2pmb.helpers import get_downline_count
from p2pmb.models import Commission, MLMTree, CoreIncomeEarned, RoyaltyEarned, ExtraRewardEarned, ExtraReward, Reward
from property.models import Property
from web_admin.helpers import add_cashfree_beneficiary
from web_admin.models import ManualFund, CompanyInvestment, ContactUsEnquiry, PropertyInterestEnquiry, \
    UserFunctionalityAccessPermission, ROIUpdateLog, TDSPercentage
from web_admin.serializers import ProfileSerializer, InvestmentSerializer, ManualFundSerializer, BankDetailSerializer, \
    UserDocumentSerializer, SuperAgencyCompanyDetailSerializer, AgencyCompanyDetailSerializer, \
    FieldAgentCompanyDetailSerializer, PropertyInterestEnquirySerializer, ContactUsEnquirySerializer, \
    GetPropertySerializer, PropertyDetailSerializer, UserCreateSerializer, LoginSerializer, \
    UserPermissionProfileSerializer, ListWithDrawRequest, UserWithWorkingIDSerializer, GetAllCommissionSerializer, \
    CompanyInvestmentSerializer, TransactionDetailSerializer, AdminChangeRequestSerializer, RewardEarnedAdminSerializer, \
    GetAllMLMChildSerializer, RoyaltyEarnedAdminSerializer, ExtraRewardEarnedAdminSerializer, ROIEarnedAdminSerializer, \
    UserWalletSerializer, TDSPercentageSerializer, TDSPercentageListSerializer
from agency.models import Investment, FundWithdrawal, SuperAgency, Agency, FieldAgent, InvestmentInterest, RewardEarned
from payment_app.models import UserWallet, Transaction
from web_admin.choices import main_dashboard

# Create your views here.

class IsStaffUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


# class StaffLoginAPIView(APIView):
#     def post(self, request):
#         username = request.data.get('email')
#         password = request.data.get('password')
#
#         if not username or not password:
#             return Response({'error': 'Username and password are required'}, status=status.HTTP_400_BAD_REQUEST)
#
#         user = authenticate(username=username, password=password)
#
#         if user is None:
#             return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
#
#         if not user.is_staff:
#             return Response({'error': 'Access denied. Only staff users can log in.'},
#                             status=status.HTTP_400_BAD_REQUEST)
#
#         token, created = Token.objects.get_or_create(user=user)
#         user_data = {
#             'first_name': user.first_name,
#             'last_name': user.last_name,
#             'email': user.email,
#             'token': token.key,
#         }
#
#         return Response({'profile': user_data}, status=status.HTTP_200_OK)


class StaffLoginAPIView(generics.CreateAPIView):
    """This API is used to login via phone_number or email and returns permissions."""
    permission_classes = (permissions.AllowAny,)
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)
        profile = user.profile

        perm = UserFunctionalityAccessPermission.objects.select_related('permission') \
            .filter(user=user).only('permission').last()

        if not perm:
            return Response(
                {'detail': 'User does not have permissions yet, Please connect to admin.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        permissions_data = []
        if perm and perm.permission:
            for module_name, actions in main_dashboard:
                sub_modules = []
                has_permission = False
                module_permissions = list(getattr(perm.permission, "main_dashboard", []))

                for action_name, action_label in actions:
                    has_access = action_name in module_permissions

                    if has_access:
                        has_permission = True
                    sub_modules.append({
                        'name': action_label,
                        'is_allowed': has_access
                    })

                if has_permission:
                    permissions_data.append({
                        'module_name': module_name,
                        'sub_modules': sub_modules
                    })

        res = {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'profile_id': profile.id,
            'user_id': user.id,
            'picture': profile.picture.url if profile.picture else None,
            'admin_role': profile.admin_role if profile and profile.admin_role else None,
            'mobile_number': profile.mobile_number,
            'token': token.key,
            'permissions': permissions_data
        }

        return Response(res, status=status.HTTP_200_OK)


class VerifyKycAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        is_kyc = request.query_params.get('is_kyc')
        is_kyc_verified = request.query_params.get('is_kyc_verified')
        is_kyc_rejected = request.query_params.get('is_kyc_rejected')

        if is_kyc is None:
            is_kyc = True
        else:
            is_kyc = is_kyc.lower() == 'true'
        if is_kyc_verified is None:
            is_kyc_verified = False
        else:
            is_kyc_verified = is_kyc_verified.lower() == 'true'
        if is_kyc_rejected is None:
            is_kyc_rejected = False
        else:
            is_kyc_rejected = is_kyc_rejected.lower() == 'true'

        profiles = Profile.objects.filter(is_kyc=is_kyc, is_kyc_verified=is_kyc_verified,
                                          is_kyc_reprocess=is_kyc_rejected).select_related('user')
        paginator = PageNumberPagination()
        paginated_profiles = paginator.paginate_queryset(profiles, request)
        serializer = ProfileSerializer(paginated_profiles, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        user_id = request.data.get('user_id')
        profile = Profile.objects.filter(user=user_id).last()
        if not profile:
            return Response({"message": "User does not have profile."}, status=status.HTTP_400_BAD_REQUEST)
        if profile.is_kyc and profile.is_kyc_verified:
            return Response({"message": "KYC is already verified for this user."},
                            status=status.HTTP_400_BAD_REQUEST)
        profile.is_kyc = True
        profile.is_kyc_verified = True
        profile.verified_by = request.user
        profile.verified_on = datetime.datetime.now()
        if profile.role == 'p2pmb':
            profile.is_p2pmb = True
        elif profile.role == 'field_agent':
            profile.is_field_agent = True
        elif profile.role == 'agency':
            profile.is_agency = True
        elif profile.role == 'super_agency':
            profile.is_super_agency = True
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
        investments = Investment.objects.filter(is_approved=False).order_by('-date_created')
        paginator = PageNumberPagination()
        paginated_investments = paginator.paginate_queryset(investments, request)
        serializer = InvestmentSerializer(paginated_investments, many=True)
        return paginator.get_paginated_response(serializer.data)

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
        wallet_type = request.data.get('wallet_type')
        amount = Decimal(request.data.get('amount'))
        user_profile = Profile.objects.filter(status='active', user=user_id).last()
        if not user_profile:
            return Response({'error': 'User id not found'}, status=status.HTTP_400_BAD_REQUEST)

        if wallet_type not in ['main_wallet', 'app_wallet']:
            return Response({'error': 'Invalid Payment Type, Please select main_wallet or app_wallet'},
                            status=status.HTTP_400_BAD_REQUEST)

        wallet, _ = UserWallet.objects.get_or_create(user=user_profile.user)
        if wallet_type == 'main_wallet':
            wallet.main_wallet_balance -= amount
        elif wallet_type == 'app_wallet':
            wallet.main_wallet_balance -= amount
        else:
            return Response({'error': 'Invalid wallet Type, Please select main_wallet or app_wallet'},
                            status=status.HTTP_400_BAD_REQUEST)
        wallet.save()

        Transaction.objects.create(
            created_by=user_profile.user,
            sender=user_profile.user, receiver=user_profile.user,
            amount=amount, transaction_type='deduct',
            transaction_status='approved', verified_by=request.user,
            verified_on=datetime.datetime.now(), payment_method='wallet', remarks='Amount Deducted by Admin.'
        )
        ManualFund.objects.create(
            created_by=self.request.user, added_to=user_profile.user,
            amount=amount, fund_type='deduct'
        )
        return Response({'message': 'Fund Deduct successfully.'}, status=status.HTTP_200_OK)


class GetUserAPIView(ListAPIView):
    permission_classes = [IsStaffUser]
    queryset = Profile.objects.filter(status='active', user__is_staff=False).order_by('-user__id')
    serializer_class = ProfileSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['is_kyc', 'is_kyc_verified', 'is_p2pmb', 'is_roi_send']
    search_fields = ['user__username', 'referral_code', 'user__first_name', 'user__email']


class GetUserWithPermissionAPIView(ListAPIView):
    permission_classes = [IsStaffUser]
    queryset = Profile.objects.filter(status='active', user__is_staff=False).order_by('-date_created')
    serializer_class = UserPermissionProfileSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['is_kyc', 'is_kyc_verified', 'is_p2pmb']
    search_fields = ['user__username', 'referral_code', 'user__first_name', 'user__email']


class CreateUserWithPermissionAPIView(generics.CreateAPIView):
    """API to create a new user with a profile and assign permissions."""
    permission_classes = [IsStaffUser]
    serializer_class = UserCreateSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data

        user = User.objects.create_user(
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            is_staff=True
        )

        permission = validated_data.get('permission')
        UserFunctionalityAccessPermission.objects.create(user=user, permission=permission)
        Profile.objects.create(
            user=user,
            mobile_number=validated_data['mobile_number'],
            city=validated_data['city'],
            state=validated_data['state'],
            pin_code=validated_data['pin_code'],
            gender=validated_data['gender'],
            date_of_birth=validated_data['date_of_birth'],
            picture=validated_data.get('picture'),
        )
        return Response({"message": "User created successfully!"}, status=status.HTTP_201_CREATED)


class UserDocumentAPIView(ListAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = UserDocumentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['created_by', 'approval_status']

    def get_queryset(self):
        user_id = self.request.query_params.get('user_id')

        if not user_id:
            raise ValidationError({"error": "user_id is a required query parameter."})

        return UserPersonalDocument.objects.filter(
            created_by=user_id, status='active'
        ).order_by('-id')


class UserBankDetailAPIView(ListAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = BankDetailSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['user']
    search_fields = ['account_number']

    def get_queryset(self):
        user_id = self.request.query_params.get('user_id')

        if not user_id:
            raise ValidationError({"error": "user_id is a required query parameter."})

        return BankDetails.objects.filter(
            user=user_id, status='active'
        ).order_by('-id')


class UserCompanyDetailAPIView(ListAPIView):
    permission_classes = [IsStaffUser]
    filter_backends = [DjangoFilterBackend, SearchFilter]

    def get_queryset(self):
        user_id = self.request.query_params.get('user_id')

        if not user_id:
            raise ValidationError({"error": "user_id is a required query parameter."})

        user = User.objects.filter(id=user_id).last()

        if not user:
            raise ValidationError({"error": "User does not exist."})

        user_profile = user.profile

        if user_profile.is_super_agency:
            self.queryset = SuperAgency.objects.filter(profile__user=user, status='active')
            self.serializer_class = SuperAgencyCompanyDetailSerializer
        elif user_profile.is_agency:
            self.queryset = Agency.objects.filter(created_by=user, status='active')
            self.serializer_class = AgencyCompanyDetailSerializer
        elif user_profile.is_field_agent:
            self.queryset = FieldAgent.objects.filter(profile__user=user, status='active')
            self.serializer_class = FieldAgentCompanyDetailSerializer
        else:
            raise ValidationError({"error": "User does not have a valid role."})

        return self.queryset

    def get_serializer_class(self):
        """
        Dynamically returns the serializer class based on the queryset selection.
        """
        return self.serializer_class


class RejectKYCStatusAPIView(APIView):
    permission_classes = [IsStaffUser]

    def post(self, request):
        user_id = request.data.get('user_id')
        remarks = request.data.get('remarks', None)

        if not user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        Profile.objects.filter(user=user_id).update(is_kyc=False, is_kyc_verified=False, is_super_agency=False,
                                                    is_agency=False, is_field_agent=False, is_p2pmb=False)
        SuperAgency.objects.filter(profile__user=user_id).update(status='inactive')
        Agency.objects.filter(created_by=user_id).update(status='inactive')
        FieldAgent.objects.filter(profile__user=user_id).update(status='inactive')
        UserPersonalDocument.objects.filter(created_by=user_id).update(status='inactive', approval_status='rejected')
        BankDetails.objects.filter(user=user_id).update(status='inactive')
        if remarks:
            Profile.objects.filter(user=user_id).update(remarks=remarks)
        return Response({'message': 'User KYC and status updated successfully'}, status=status.HTTP_200_OK)


class ManualFundViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffUser]
    queryset = ManualFund.objects.filter(status='active').order_by('-date_created')
    serializer_class = ManualFundSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['amount', 'added_to']
    search_fields = ['added_to__username', 'added_to__first_name', 'added_to__email']


class ContactUsEnquiryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffUser]
    queryset = ContactUsEnquiry.objects.all().order_by('-date_created')
    serializer_class = ContactUsEnquirySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['first_name', 'last_name', 'email', 'phone', 'subject']
    search_fields = ['first_name', 'last_name', 'email', 'phone']

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsStaffUser()]


class PropertyInterestEnquiryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffUser]
    queryset = PropertyInterestEnquiry.objects.all().order_by('-date_created')
    serializer_class = PropertyInterestEnquirySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['name', 'email', 'phone', 'property']
    search_fields = ['name', 'email', 'phone']

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsStaffUser()]


class CompanyInvestmentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffUser]
    queryset = CompanyInvestment.objects.all().order_by('-initiated_date')
    serializer_class = CompanyInvestmentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['applicable_for', 'investment_type', 'initiated_date']


class TDSPercentageViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffUser]
    queryset = TDSPercentage.objects.all().order_by('date_created')
    serializer_class = TDSPercentageSerializer

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return TDSPercentageListSerializer
        return super().get_serializer_class()

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


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
            p2pmb_fund_added=Sum("amount", filter=Q(is_approved=True, investment_type="p2pmb",
                                                    package__isnull=False, status='active', pay_method='main_wallet')),
            super_agency_fund_added=Sum("amount", filter=Q(is_approved=True, investment_type="super_agency",
                                                           package__isnull=False, status='active', pay_method='main_wallet')),
            agency_fund_added=Sum("amount", filter=Q(is_approved=True, investment_type="agency",
                                                     package__isnull=False, status='active', pay_method='main_wallet')),
            field_agent_fund_added=Sum("amount", filter=Q(is_approved=True, investment_type="field_agent",
                                                          package__isnull=False, status='active', pay_method='main_wallet')),
            pending_approval_payment=Sum("amount", filter=Q(is_approved=False)),
            send_direct_income=Sum("user", distinct=True, filter=Q(send_direct_income=True)),
            send_level_income=Sum("user", distinct=True, filter=Q(send_level_income=True)),
            interest_send_user=Sum("user", distinct=True, filter=Q(is_interest_send=True)),
        )

        fund_withdraw = FundWithdrawal.objects.aggregate(
            total_unique_withdraw_user=Count("user", distinct=True),
            pending_withdraw_user=Sum("user", distinct=True, filter=Q(is_paid=False)),
            pending_withdraw_amount=Sum("withdrawal_amount", filter=Q(is_paid=False)),
            approve_withdraw_user=Sum("user", distinct=True, filter=Q(is_paid=True)),
            approve_withdraw_amount=Sum("withdrawal_amount", filter=Q(is_paid=True)),
            total_withdraw_amount=Sum("withdrawal_amount"),
        )

        admin_paid_amount = ManualFund.objects.filter(status="active", fund_type='deposit').aggregate(Sum("amount")
                                                                                                      )["amount__sum"]
        dashboard_count = {
            **user_counts,
            **investment_data,
            **fund_withdraw,
            "admin_paid_amount": admin_paid_amount or 0,
        }
        return Response(dashboard_count, status=status.HTTP_200_OK)


class ManualFundGraphAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        filter_type = request.GET.get('filter_type', 'date_wise')
        today = datetime.datetime.now().date()
        current_year = today.year
        month = int(request.GET.get('month', today.month))
        data = []

        if filter_type == 'date_wise':
            start_date = date(current_year, month, 1)
            end_date = today if month == today.month else (start_date.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            all_dates = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
            funds = Investment.objects.filter(date_created__date__range=[start_date, end_date],
                                              investment_type='p2pmb', package__isnull=False,
                                              is_approved=True, pay_method='main_wallet')
            # funds = ManualFund.objects.filter(date_created__date__range=[start_date, end_date])
            funds_dict = {entry['date_created__date']: entry['total_amount'] for entry in funds.values('date_created__date').annotate(total_amount=Sum('amount'))}
            data = [{"date": date, "total_amount": funds_dict.get(date, 0)} for date in all_dates]

        elif filter_type == 'month_wise':
            months = range(1, 13)
            # funds = ManualFund.objects.filter(date_created__year=current_year).values('date_created__month').annotate(
            #     total_amount=Sum('amount'))
            funds = Investment.objects.filter(date_created__year=current_year, investment_type='p2pmb',
                                              package__isnull=False, is_approved=True, pay_method='main_wallet'
                                              ).values('date_created__month').annotate(total_amount=Sum('amount'))
            funds_dict = {entry['date_created__month']: entry['total_amount'] for entry in funds}
            data = [{"month": month, "total_amount": funds_dict.get(month, 0)} for month in months]

        elif filter_type == 'quarterly':
            quarters = {
                'Q1 (Jan-Mar)': (1, 3),
                'Q2 (Apr-Jun)': (4, 6),
                'Q3 (Jul-Sep)': (7, 9),
                'Q4 (Oct-Dec)': (10, 12)
            }
            for quarter, (start_month, end_month) in quarters.items():
                # total = ManualFund.objects.filter(date_created__year=current_year,
                #                                   date_created__month__gte=start_month,
                #                                   date_created__month__lte=end_month).aggregate(Sum('amount'))['amount__sum'] or 0
                total = Investment.objects.filter(date_created__year=current_year, date_created__month__gte=start_month,
                                                  date_created__month__lte=end_month, investment_type='p2pmb',
                                                  package__isnull=False, is_approved=True, pay_method='main_wallet'
                                                  ).values('date_created__month').aggregate(Sum('amount'))['amount__sum'] or 0
                data.append({"quarter": quarter, "total_amount": total})

        elif filter_type == 'half_yearly':
            halves = {
                'H1 (Jan-Jun)': (1, 6),
                'H2 (Jul-Dec)': (7, 12)
            }
            for half, (start_month, end_month) in halves.items():
                # total = ManualFund.objects.filter(date_created__year=current_year,
                #                                   date_created__month__gte=start_month,
                #                                   date_created__month__lte=end_month).aggregate(Sum('amount'))['amount__sum'] or 0
                total = Investment.objects.filter(date_created__year=current_year, date_created__month__gte=start_month,
                                                  date_created__month__lte=end_month, investment_type='p2pmb',
                                                  package__isnull=False, is_approved=True, pay_method='main_wallet'
                                                  ).values('date_created__month').aggregate(Sum('amount'))['amount__sum'] or 0
                data.append({"half_year": half, "total_amount": total})

        elif filter_type == 'yearly':
            for year in range(current_year - 1, current_year + 1):
                # total = ManualFund.objects.filter(date_created__year=year).aggregate(Sum('amount'))['amount__sum'] or 0
                total = Investment.objects.filter(date_created__year=year, investment_type='p2pmb',
                                                  package__isnull=False, is_approved=True, pay_method='main_wallet'
                                                  ).values('date_created__month').aggregate(Sum('amount'))['amount__sum'] or 0
                data.append({"year": year, "total_amount": total})

        return Response({"filter_type": filter_type, "data": data})


class ManualFundDistributionAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        month = request.GET.get('month')
        year = request.GET.get('year')

        month = int(month) if month else None
        year = int(year) if year else None

        filters = {}
        investment_filter = {'applicable_for': 'p2pmb'}

        if month:
            filters['date_created__month'] = month
            investment_filter['initiated_date__month'] = month
        if year:
            filters['date_created__year'] = year
            investment_filter['initiated_date__year'] = year

        total_fund = Investment.objects.filter(
            **filters, investment_type='p2pmb', package__isnull=False, is_approved=True, pay_method='main_wallet'
        ).distinct().aggregate(total_amount=Sum('amount'))['total_amount'] or Decimal(0)

        fund_initiated = CompanyInvestment.objects.filter(**investment_filter)

        distribution = {
            "direct_income": {
                "name": "Direct Income",
                "expected_spending": Decimal("4.5"),
                "sum_field": "amount",
                "model": Commission,
                "filter": lambda m, y: {
                    "commission_type": "direct",
                    **({"date_created__month": m} if m else {}),
                    **({"date_created__year": y} if y else {}),
                },
            },
            "level": {
                "name": "Level Income",
                "expected_spending": Decimal("4.5"),
                "model": Commission,
                "sum_field": "amount",
                "filter": lambda m, y: {
                    "commission_type": "level",
                    **({"date_created__month": m} if m else {}),
                    **({"date_created__year": y} if y else {}),
                },
            },
            "reward": {
                "name": "Reward",
                "expected_spending": Decimal("2"),
                "model": RewardEarned,
                "sum_field": "reward__gift_amount",
                "filter": lambda m, y: {
                    **({"earned_at__month": m} if m else {}),
                    **({"earned_at__year": y} if y else {}),
                },
            },
            "royalty": {
                "name": "Royalty",
                "expected_spending": Decimal("1"),
                "model": RoyaltyEarned,
                "sum_field": "earned_amount",
                "filter": lambda m, y: {
                    **({"earned_date__month": m} if m else {}),
                    **({"earned_date__year": y} if y else {}),
                },
            },
            "core_team": {
                "name": "Core Team",
                "expected_spending": Decimal("1"),
                "model": CoreIncomeEarned,
                "sum_field": "income_earned",
                "filter": lambda m, y: {
                    **({"date_created__month": m} if m else {}),
                    **({"date_created__year": y} if y else {}),
                },
            },
            "company_extra_expenses": {
                "name": "Company Extra Expenses",
                "expected_spending": Decimal("3"),
                "model": CompanyInvestment,
                "sum_field": "amount",
                "filter": lambda m, y: {
                    "investment_type": "company_expense",
                    **({"initiated_date__month": m} if m else {}),
                    **({"initiated_date__year": y} if y else {}),
                },
            },
            "diwali_gift": {
                "name": "Diwali Gift",
                "expected_spending": Decimal("3"),
                "model": CompanyInvestment,
                "sum_field": "amount",
                "filter": lambda m, y: {
                    "investment_type": "diwali_gift",
                    **({"initiated_date__month": m} if m else {}),
                    **({"initiated_date__year": y} if y else {}),
                },
            },
            "donate": {
                "name": "Donation",
                "expected_spending": Decimal("1"),
                "model": CompanyInvestment,
                "sum_field": "amount",
                "filter": lambda m, y: {
                    "investment_type": "donate",
                    **({"initiated_date__month": m} if m else {}),
                    **({"initiated_date__year": y} if y else {}),
                },
            },
            "interest": {
                "name": "Interest",
                "expected_spending": Decimal("20"),
                "model": InvestmentInterest,
                "sum_field": "interest_amount",
                "filter": lambda m, y: {
                    **({"interest_send_date__month": m} if m else {}),
                    **({"interest_send_date__year": y} if y else {}),
                },
            },
            "properties": {
                "name": "Property Investment",
                "expected_spending": Decimal("50"),
                "model": CompanyInvestment,
                "sum_field": "amount",
                "filter": lambda m, y: {
                    "investment_type": "property",
                    **({"initiated_date__month": m} if m else {}),
                    **({"initiated_date__year": y} if y else {}),
                },
            },
            "crypto": {
                "name": "Crypto",
                "expected_spending": Decimal("10"),
                "model": CompanyInvestment,
                "sum_field": "amount",
                "filter": lambda m, y: {
                    "investment_type": "crypto",
                    **({"initiated_date__month": m} if m else {}),
                    **({"initiated_date__year": y} if y else {}),
                },
            },
        }

        response_data = []

        for key, cfg in distribution.items():
            expected_spending = (total_fund * cfg["expected_spending"] / Decimal(100)).quantize(Decimal("0.01"))

            investment_amount = fund_initiated.filter(investment_type=key
                                                      ).aggregate(total=Sum('amount'))['total'] or Decimal(0)

            income_model = cfg["model"]
            model_filter = cfg["filter"](month, year)

            commission_amount = income_model.objects.filter(**model_filter).aggregate(
                total=Sum(cfg["sum_field"])
            )['total'] or Decimal(0)

            total_spend_amount = (investment_amount + commission_amount).quantize(Decimal("0.01"))
            total_spend_per = ((total_spend_amount / total_fund) * 100).quantize(Decimal("0.01")) if total_fund else Decimal("0.00")
            left_in_bank = (expected_spending - total_spend_amount).quantize(Decimal("0.01"))

            response_data.append({
                "name": cfg["name"],
                "total_spend_amount": float(total_spend_amount),
                "left_in_bank": float(left_in_bank),
                "total_spend_per": float(total_spend_per),
                "expected_spending_per": float(cfg["expected_spending"]),
                "expected_spending_amount": float(expected_spending),
            })

        return Response(response_data)


class ManualFundDistributionAgencyAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        month = request.GET.get('month')
        year = request.GET.get('year')
        applicable_for = request.GET.get('applicable_for')

        month = int(month) if month else None
        year = int(year) if year else None

        filters = {}
        if applicable_for == 'super_agency':
            investment_filter = {'applicable_for': 'super_agency'}
        elif applicable_for == 'agency':
            investment_filter = {'applicable_for': 'agency'}
        elif applicable_for == 'field_agent':
            investment_filter = {'applicable_for': 'field_agent'}
        else:
            return Response({'message': 'Invalid Filter'}, status=status.HTTP_400_BAD_REQUEST)
        commission_filter = {}

        if month:
            filters['date_created__month'] = month
            investment_filter['initiated_date__month'] = month
            commission_filter['date_created__month'] = month
        if year:
            filters['date_created__year'] = year
            investment_filter['initiated_date__year'] = year
            commission_filter['date_created__year'] = year

        if applicable_for == 'super_agency':
            total_fund = Investment.objects.filter(**filters, investment_type='super_agency', package__isnull=False,
                                                   is_approved=True, pay_method='main_wallet').distinct().aggregate(
                total_amount=Sum('amount'))['total_amount'] or Decimal(0)
        elif applicable_for == 'agency':
            total_fund = Investment.objects.filter(**filters, investment_type='agency', package__isnull=False,
                                                   is_approved=True, pay_method='main_wallet').distinct().aggregate(
                total_amount=Sum('amount'))['total_amount'] or Decimal(0)
        elif applicable_for == 'field_agent':
            total_fund = Investment.objects.filter(**filters, investment_type='field_agent', package__isnull=False,
                                                   is_approved=True, pay_method='main_wallet').distinct().aggregate(
                total_amount=Sum('amount'))['total_amount'] or Decimal(0)

        fund_initiated = CompanyInvestment.objects.filter(**investment_filter)
        commissions = Commission.objects.filter(**commission_filter)

        key_to_investment_type = {
            "direct_income": "direct",
            "interest": "interest",
            "crypto": "crypto",
            "properties": "property",
            "core_team": "core_team",
            "company_extra_expenses": "company_expense",
            "diwali_gift": "diwali_gift",
            "donate": "donation"
        }
        distribution = {
            "direct_income": {"name": "Trading + P2PMB", "expected_spending": Decimal("12")},
            "interest": {"name": "Interest", "expected_spending": Decimal("38")},
            "crypto": {"name": "Crypto", "expected_spending": Decimal("20")},
            "properties": {"name": "Property Investment", "expected_spending": Decimal("20")},
            "core_team": {"name": "Core Team", "expected_spending": Decimal("1")},
            "company_extra_expenses": {"name": "Company Extra Expenses", "expected_spending": Decimal("5")},
            "diwali_gift": {"name": "Diwali Gift", "expected_spending": Decimal("3")},
            "donate": {"name": "Donation", "expected_spending": Decimal("1")},
        }

        response_data = []

        for key, config in distribution.items():
            investment_type = key_to_investment_type.get(key)
            expected_spending = (total_fund * config["expected_spending"] / Decimal(100)).quantize(Decimal("0.01"))

            investment_amount = fund_initiated.filter(
                investment_type=investment_type
            ).aggregate(total=Sum('amount'))['total'] or Decimal(0)

            commission_amount = Decimal(0)
            if key in ['direct_income', 'level', 'reward', 'royalty']:
                commission_amount = commissions.filter(
                    commission_type=investment_type
                ).aggregate(total=Sum('amount'))['total'] or Decimal(0)

            total_spend_amount = (investment_amount + commission_amount).quantize(Decimal("0.01"))
            total_spend_per = ((total_spend_amount / total_fund) * 100).quantize(Decimal("0.01")) if (
                total_fund) else Decimal("0.00")
            left_in_bank = (expected_spending - total_spend_amount).quantize(Decimal("0.01"))

            response_data.append({
                "name": config["name"],
                "total_spend_amount": float(total_spend_amount),
                "left_in_bank": float(left_in_bank),
                "total_spend_per": float(total_spend_per),
                "expected_spending_per": float(config["expected_spending"]),
                "expected_spending_amount": float(expected_spending),
            })

        return Response(response_data)


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


class ApproveRejectDocumentsAPIView(APIView):
    permission_classes = [IsAuthenticated,]

    def post(self, request, *args, **kwargs):
        document_ids = request.data.get("document_ids", [])
        action = request.data.get("action")
        rejection_reason = request.data.get("rejection_reason", "")

        if not document_ids or action not in ["approve", "reject"]:
            return Response({"detail": "Invalid input."}, status=status.HTTP_400_BAD_REQUEST)

        documents = UserPersonalDocument.objects.filter(id__in=document_ids)

        if action == "approve":
            documents.update(approval_status="approved", rejection_reason=None)
        elif action == "reject":
            documents.update(approval_status="rejected", rejection_reason=rejection_reason)

        return Response({"detail": f"Documents {action}d successfully."})


class GetAllPropertyAPIView(GenericAPIView):
    serializer_class = GetPropertySerializer

    def get_queryset(self):
        queryset = Property.objects.filter(status='active').order_by('-id')
        request = self.request
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        country = request.query_params.get('country')
        state = request.query_params.get('state')
        city = request.query_params.get('city')
        category = request.query_params.get('category')
        property_type = request.query_params.get('property_type')
        is_featured = request.query_params.get('is_featured')
        features = request.query_params.getlist('features')

        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        if country:
            queryset = queryset.filter(country_id=country)
        if state:
            queryset = queryset.filter(state_id=state)
        if city:
            queryset = queryset.filter(city_id=city)
        if category:
            queryset = queryset.filter(category_id=category)
        if property_type:
            queryset = queryset.filter(property_type_id=property_type)
        if is_featured in ['true', 'false']:
            queryset = queryset.filter(is_featured=is_featured.lower() == 'true')

        if features:
            for feature_name in features:
                queryset = queryset.filter(
                    features__feature__name__iexact=feature_name.strip()
                )

        return queryset.distinct().order_by('-id')

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class PropertyDetailAPIView(APIView):

    def get(self, request, id):
        property_instance = Property.objects.filter(id=id, status='active').last()
        if not property_instance:
            return Response({'message': 'Invalid property Id'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = PropertyDetailSerializer(property_instance)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserWiseFundDistributionAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request, id):
        user_account = MLMTree.objects.filter(status='active', child__id=id, is_show=True).last()
        if not user_account:
            return Response({'message': 'User not enrolled in P2PMB Model.'}, status=status.HTTP_400_BAD_REQUEST)

        total_fund = Investment.objects.filter(
            user__id=id, investment_type='p2pmb', package__isnull=False,
            is_approved=True, pay_method='main_wallet'
        ).aggregate(total_amount=Sum('amount'))['total_amount'] or Decimal(0)

        total_fund = Decimal(total_fund)

        commissions = Commission.objects.filter(commission_to__id=id)

        key_to_investment_type = {
            "direct_income": "direct",
            "level": "level",
            "reward": "reward",
            "royalty": "royalty",
            "core_team": "core_team",
            "company_extra_expenses": "company_expense",
            "diwali_gift": "diwali_gift",
            "donate": "donation",
            "interest": "interest",
            "properties": "property",
            "crypto": "crypto",
        }

        distribution = {
            "direct_income": {"name": "Direct Income", "expected_spending": Decimal("4.5")},
            "level": {"name": "Level Income", "expected_spending": Decimal("4.5")},
            "reward": {"name": "Reward", "expected_spending": Decimal("2")},
            "royalty": {"name": "Royalty", "expected_spending": Decimal("1")},
            "core_team": {"name": "Core Team", "expected_spending": Decimal("1")},
            "company_extra_expenses": {"name": "Company Extra Expenses", "expected_spending": Decimal("3")},
            "diwali_gift": {"name": "Diwali Gift", "expected_spending": Decimal("3")},
            "donate": {"name": "Donation", "expected_spending": Decimal("1")},
            "interest": {"name": "Interest", "expected_spending": Decimal("20")},
            "properties": {"name": "Property Investment", "expected_spending": Decimal("50")},
            "crypto": {"name": "Crypto", "expected_spending": Decimal("10")},
        }

        response_data = []

        for key, config in distribution.items():
            investment_type = key_to_investment_type.get(key)
            expected_spending = (total_fund * config["expected_spending"] / Decimal(100)).quantize(Decimal("0.01"))

            investment_amount = Decimal(0)

            commission_amount = Decimal(0)
            if key in ['direct_income', 'level', 'reward', 'royalty']:
                commission_amount = commissions.filter(
                    commission_type=investment_type
                ).aggregate(total=Sum('amount'))['total'] or Decimal(0)

            total_spend_amount = (investment_amount + commission_amount).quantize(Decimal("0.01"))
            total_spend_per = ((total_spend_amount / total_fund) * Decimal(100)).quantize(
                Decimal("0.01")) if total_fund else Decimal("0.00")
            left_in_bank = (expected_spending - total_spend_amount).quantize(Decimal("0.01"))

            response_data.append({
                "name": config["name"],
                "total_spend_amount": float(total_spend_amount),
                "left_in_bank": float(left_in_bank),
                "total_spend_per": float(total_spend_per),
                "expected_spending_per": float(config["expected_spending"]),
                "expected_spending_amount": float(expected_spending),
            })

        return Response(response_data)


class CompanyLiabilityStatsAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        filter_type = request.query_params.get('type')
        search_query = request.query_params.get('search', '').strip()

        filtered_investments = Investment.objects.filter(
            status='active', investment_type='p2pmb',
            is_approved=True, package__isnull=False, pay_method='main_wallet'
        ).select_related('user')

        if search_query:
            filtered_investments = filtered_investments.filter(
                Q(user__username__icontains=search_query)
            )

        user_investments = filtered_investments.values('user_id', 'user__username').annotate(
            total_amount=Sum('amount')
        )
        investment_map = {
            item['user_id']: {
                'username': item['user__username'], 'amount': item['total_amount']
            }
            for item in user_investments
        }

        referrals = MLMTree.objects.filter(is_show=True).values_list('referral_by_id', 'child_id')
        referral_map = defaultdict(list)
        for referral_by_id, child_id in referrals:
            referral_map[referral_by_id].append(child_id)

        working_ids = {
            user_id for user_id in investment_map
            if len(referral_map.get(user_id, [])) >= 2
        }

        if filter_type == 'working':
            filtered_user_ids = working_ids
            filtered_investments = filtered_investments.filter(user__in=filtered_user_ids)
        elif filter_type == 'non-working':
            filtered_user_ids = set(investment_map.keys()) - working_ids
            filtered_investments = filtered_investments.filter(user__in=filtered_user_ids)
        else:
            filtered_user_ids = set(investment_map.keys())

        total_return_amount = Decimal('0')
        for user_id in filtered_user_ids:
            data = investment_map[user_id]
            multiplier = Decimal('4.4') if user_id in working_ids else Decimal('2.1')
            total_return_amount += data['amount'] * multiplier

        total_investment = filtered_investments.aggregate(
            total_amount=Sum('amount')
        )['total_amount'] or Decimal('0')

        total_income_earned = Commission.objects.filter(status='active', commission_to__in=filtered_user_ids).aggregate(
            total_amount=Sum('amount')
        )['total_amount'] or Decimal('0')

        total_interest_earned = InvestmentInterest.objects.filter(status='active',
                                                                  investment__user__in=filtered_user_ids).aggregate(
            total_amount=Sum('interest_amount')
        )['total_amount'] or Decimal('0')

        core_group_earned = CoreIncomeEarned.objects.filter(status='active', user__in=filtered_user_ids).aggregate(
            total_amount=Sum('income_earned')
        )['total_amount'] or Decimal('0')

        royalty_earned = RoyaltyEarned.objects.filter(status='active', user__in=filtered_user_ids).aggregate(
            total_amount=Sum('earned_amount')
        )['total_amount'] or Decimal('0')

        reward_earned = RewardEarned.objects.filter(status='active', user__in=filtered_user_ids).select_related(
            'reward').aggregate(total_amount=Sum('reward__gift_amount')
        )['total_amount'] or Decimal('0')

        extra_reward_earned = ExtraRewardEarned.objects.filter(status='active', user__in=filtered_user_ids).aggregate(
            total_amount=Sum('amount')
        )['total_amount'] or Decimal('0')

        total_send_amount = (royalty_earned + total_income_earned + total_interest_earned + core_group_earned +
                             extra_reward_earned + reward_earned)
        return Response({
            'total_investment': total_investment,
            'total_return_amount': total_send_amount,
            'total_send_amount': total_return_amount,
            'working_user_count': len(working_ids),
            'non_working_user_count': len(investment_map.keys() - working_ids),
        }, status=status.HTTP_200_OK)


class WithDrawRequest(ListAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = ListWithDrawRequest

    def get_queryset(self):
        queryset = FundWithdrawal.objects.filter(status='active').order_by('-id')
        user_id = self.request.query_params.get('user')
        status = self.request.query_params.get('withdraw_status')
        search = self.request.query_params.get('search')

        if user_id:
            queryset = queryset.filter(user__id=user_id)

        if status in ['pending', 'approved', 'rejected']:
            queryset = queryset.filter(withdrawal_status=status)

        if search:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search) | Q(user__last_name__icontains=search) |
                Q(user__email__icontains=search) | Q(user__username__icontains=search)
            )

        return queryset


class ApproveRejectWithDrawAPIView(APIView):
    permission_classes = [IsStaffUser,]

    def post(self, request, *args, **kwargs):
        withdraw_id = request.data.get("id", None)
        action = request.data.get("action")
        rejection_reason = request.data.get("rejection_reason", "")

        if not withdraw_id or action not in ["approved", "rejected"]:
            return Response({"error": "Invalid input."}, status=status.HTTP_400_BAD_REQUEST)

        withdraw = FundWithdrawal.objects.filter(id=withdraw_id).last()

        if not withdraw:
            return Response({"error": "Invalid withdraw Id."}, status=status.HTTP_400_BAD_REQUEST)

        if action == "approved":
            deducted_amount = withdraw.withdrawal_amount * Decimal('0.95')
            taxable_amount = withdraw.withdrawal_amount - deducted_amount
            Transaction.objects.create(
                sender=withdraw.user, receiver=withdraw.user, amount=deducted_amount,
                transaction_type='receive', transaction_status='deposit', payment_method='upi',
                remarks='Withdraw Request approved.', verified_by=self.request.user, verified_on=datetime.datetime.now(),
                taxable_amount=taxable_amount
            )
            wallet = UserWallet.objects.filter(user=withdraw.user).last()
            # bank_details = BankDetails.objects.filter(user=withdraw.user).last()
            # if not bank_details or bank_details.account_number or bank_details.ifsc_code:
            #     return Response({"detail": f"Need to update account number or ifsc code of the user."},
            #                     status=status.HTTP_400_BAD_REQUEST)
            # elif not bank_details.beneficiary_id:
            #     err, beneficiary_id = add_cashfree_beneficiary(bank_details)
            #     if err:
            #         return Response({"detail": beneficiary_id}, status=status.HTTP_400_BAD_REQUEST)
            # else:
            #     beneficiary_id = bank_details.beneficiary_id

            wallet.main_wallet_balance -= withdraw.withdrawal_amount
            wallet.save()
            withdraw.withdrawal_status = "approved"
            withdraw.rejection_reason = None
            withdraw.is_paid = True
            withdraw.action_date = datetime.datetime.now()
            withdraw.action_taken_by = self.request.user
            withdraw.save()
        elif action == "rejected":
            withdraw.withdrawal_status = "rejected"
            withdraw.rejection_reason = rejection_reason
            withdraw.action_date = datetime.datetime.now()
            withdraw.action_taken_by = self.request.user
            withdraw.save()
        return Response({"detail": f"Withdraw {action} successfully."})


class UserWithWorkingIDListView(ListAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = UserWithWorkingIDSerializer

    def get_queryset(self):
        queryset = MLMTree.objects.filter(is_show=True).select_related('child', 'parent')
        is_working_id = self.request.query_params.get('is_working_id')
        sort_order = self.request.query_params.get('sort', 'desc')
        search = self.request.query_params.get('search', '').strip().lower()

        if search:
            queryset = queryset.filter(
                Q(child__first_name__icontains=search) |
                Q(child__last_name__icontains=search) |
                Q(child__username__icontains=search) |
                Q(parent__first_name__icontains=search) |
                Q(parent__last_name__icontains=search) |
                Q(parent__username__icontains=search)
            )

        if is_working_id in ['true', 'True', '1', 'false', 'False', '0']:
            working_ids = self._get_working_ids()
            if is_working_id.lower() in ['true', '1']:
                queryset = queryset.filter(child_id__in=working_ids)
            else:
                queryset = queryset.exclude(child_id__in=working_ids)

        if sort_order == 'asc':
            queryset = queryset.order_by('id')
        else:
            queryset = queryset.order_by('-id')
        return queryset

    def _get_working_ids(self):
        investments = Investment.objects.filter(status='active', investment_type='p2pmb', is_approved=True,
                                                package__isnull=False, pay_method='main_wallet'
        ).select_related('user').values('user_id').annotate(total_amount=Sum('amount'))

        investment_map = {item['user_id']: item['total_amount'] for item in investments}

        referrals = MLMTree.objects.filter(is_show=True).select_related('referral_by', 'child').values_list(
            'referral_by_id', 'child_id')
        referral_map = {}
        for referral_by_id, child_id in referrals:
            referral_map.setdefault(referral_by_id, []).append(child_id)

        working_ids = set()
        for user_id, user_investment in investment_map.items():
            if user_investment == 0:
                continue
            referral_ids = referral_map.get(user_id, [])
            if len(referral_ids) >= 2:
                working_ids.add(user_id)

        return working_ids


class WithdrawDashboard(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        user_id = request.query_params.get('user')
        manual_funds = ManualFund.objects.filter(status='active').order_by('-id')
        withdraw_request = FundWithdrawal.objects.filter(status='active').order_by('-id')

        if user_id:
            manual_funds = manual_funds.filter(added_to=user_id)
            withdraw_request = withdraw_request.filter(user=user_id)

        total_investment = manual_funds.aggregate(total_amount=Sum('amount'))['total_amount'] or Decimal(0)
        credit_withdraw = withdraw_request.filter(is_paid=True).aggregate(
            total_amount=Sum('withdrawal_amount'))['total_amount'] or Decimal(0)
        pending_withdraw = withdraw_request.filter(is_paid=False).aggregate(
            total_amount=Sum('withdrawal_amount'))['total_amount'] or Decimal(0)

        response = {
            'total_investment': total_investment,
            'credit_withdraw': credit_withdraw,
            'pending_withdraw': pending_withdraw,
        }
        return Response(response, status=status.HTTP_200_OK)


class WithdrawDashboardV2(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        user_id = request.query_params.get('user_id')
        is_working = request.query_params.get('working')
        month = request.query_params.get('month')
        year = request.query_params.get('year')

        if not user_id:
            return Response({'message': 'User ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        date_filters = {}
        if month and year:
            date_filters['date_created__month'] = month
            date_filters['date_created__year'] = year

        get_investment = Investment.objects.filter(
            status='active', investment_type='p2pmb',
            is_approved=True, package__isnull=False,
            pay_method='main_wallet', user=user_id
        ).aggregate(total=Sum('amount'))['total'] or Decimal(0)

        is_working_id = bool(is_working)
        total_return_amount = get_investment * (Decimal('4.4') if is_working_id else Decimal('2.1'))

        total_income_earned = Commission.objects.filter(
            status='active', commission_to=user_id, **date_filters
        ).aggregate(total=Sum('amount'))['total'] or Decimal(0)

        interest_filters = Q(status='active', investment__user=user_id)
        if month and year:
            interest_filters &= Q(interest_send_date__month=month, interest_send_date__year=year)

        total_interest_earned = InvestmentInterest.objects.filter(interest_filters).aggregate(
            total=Sum('interest_amount'))['total'] or Decimal(0)

        core_income_filters = Q(status='active', user=user_id)

        core_group_earned = CoreIncomeEarned.objects.filter(core_income_filters, **date_filters).aggregate(
            total=Sum('income_earned'))['total'] or Decimal(0)

        royalty_filters = Q(status='active', user=user_id)
        if month and year:
            royalty_filters &= Q(earned_date__month=month, earned_date__year=year)

        royalty_earned = RoyaltyEarned.objects.filter(royalty_filters).aggregate(
            total=Sum('earned_amount'))['total'] or Decimal(0)

        reward_filters = Q(status='active', user=user_id)
        if month and year:
            reward_filters &= Q(earned_at__month=month, earned_at__year=year)

        reward_earned = RewardEarned.objects.filter(reward_filters).select_related('reward').aggregate(
            total=Sum('reward__gift_amount'))['total'] or Decimal(0)

        extra_reward_earned = ExtraRewardEarned.objects.filter(
            status='active', user=user_id, **date_filters
        ).aggregate(total=Sum('amount'))['total'] or Decimal(0)

        total_send_amount = (
            total_income_earned +
            total_interest_earned +
            core_group_earned +
            royalty_earned +
            reward_earned +
            extra_reward_earned
        )

        current_due_value = total_return_amount - total_send_amount + royalty_earned + reward_earned + extra_reward_earned
        twenty_percent_value = total_return_amount * Decimal('0.20')
        is_low_balance = current_due_value <= twenty_percent_value

        return Response({
            'investment_amount': get_investment,
            'is_working_id': is_working_id,
            'total_return_amount': total_return_amount,
            'total_income_earned': total_send_amount,
            'current_due_values': current_due_value,
            'is_low_balance': is_low_balance,
        }, status=status.HTTP_200_OK)


class CommissionListView(APIView):
    permission_classes = [IsStaffUser]
    pagination_class = LimitOffsetPagination()

    def get(self, request):
        user_id = request.query_params.get('user_id')
        investment_type = request.query_params.get('commission_type')

        commission_qs = Commission.objects.filter(status='active')
        interest_qs = InvestmentInterest.objects.filter(status='active')
        core_group_earned = CoreIncomeEarned.objects.filter(status='active')

        if user_id:
            commission_qs = commission_qs.filter(commission_to=user_id)
            interest_qs = interest_qs.filter(investment__user=user_id)
            core_group_earned = core_group_earned.filter(user=user_id)

        if investment_type == 'interest':
            commission_qs = Commission.objects.none()
            core_group_earned = CoreIncomeEarned.objects.none()
        elif investment_type == 'core_team':
            interest_qs = InvestmentInterest.objects.none()
            commission_qs = Commission.objects.none()
            core_group_earned = core_group_earned.filter(income_type='income')
        elif investment_type == 'tour':
            interest_qs = InvestmentInterest.objects.none()
            commission_qs = Commission.objects.none()
            core_group_earned = core_group_earned.filter(income_type='tour')
        elif investment_type:
            interest_qs = InvestmentInterest.objects.none()
            core_group_earned = CoreIncomeEarned.objects.none()
            commission_qs = commission_qs.filter(commission_type=investment_type)

        commission_data = [
            {
                "id": entry.id,
                "user_id": entry.commission_to.id,
                "name": entry.commission_to.get_full_name(),
                "email": entry.commission_to.email,
                "amount": entry.amount,
                "status": entry.status,
                "commission_type": entry.commission_type,
                "description": entry.description,
                "date_created": entry.date_created
            }
            for entry in commission_qs
        ]

        core_group_data = [
            {
                "id": entry.id,
                "user_id": entry.user.id,
                "name": entry.user.get_full_name(),
                "email": entry.user.email,
                "amount": entry.income_earned,
                "status": entry.status,
                "commission_type": "core_group",
                "description": f"You have earned a core group income of ₹{entry.income_earned}.",
                "date_created": entry.date_created
            }
            for entry in core_group_earned
        ]

        interest_data = [
            {
                "id": entry.id,
                "user_id": entry.investment.user.id,
                "name": entry.investment.user.get_full_name(),
                "email": entry.investment.user.email,
                "amount": entry.interest_amount,
                "status": "active",
                "commission_type": "interest",
                "description": f"Interest Send On {entry.interest_send_date}",
                "date_created": entry.date_created
            }
            for entry in interest_qs
        ]

        combined_data = commission_data + interest_data + core_group_data
        combined_data.sort(key=lambda x: x['date_created'], reverse=True)
        paginator = self.pagination_class
        page = paginator.paginate_queryset(combined_data, request)
        return paginator.get_paginated_response(page)


class AppTransferTransaction(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        transaction_type = request.query_params.get('transaction_type', 'transfer')

        transactions = Transaction.objects.filter(
            status='active', transaction_type=transaction_type
        ).select_related('sender', 'receiver').order_by('-id')

        month = request.query_params.get('month')
        year = request.query_params.get('year')
        if month and year:
            transactions = transactions.filter(date_created__month=month, date_created__year=year)

        search = request.query_params.get('search')
        if search:
            transactions = transactions.filter(
                Q(sender__first_name__icontains=search) |
                Q(sender__last_name__icontains=search) |
                Q(sender__email__icontains=search) |
                Q(sender__username__icontains=search) |
                Q(receiver__first_name__icontains=search) |
                Q(receiver__last_name__icontains=search) |
                Q(receiver__email__icontains=search) |
                Q(receiver__username__icontains=search)
            )

        paginator = LimitOffsetPagination()
        paginated_transactions = paginator.paginate_queryset(transactions, request)
        serializer = TransactionDetailSerializer(paginated_transactions, many=True)
        return paginator.get_paginated_response(serializer.data)


class ChangeRequestListAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        change_request = ChangeRequest.objects.filter(status='active').order_by('-id')
        request_status = request.query_params.get('request_status')
        if request_status:
            change_request = change_request.filter(request_status=request_status)

        search = request.query_params.get('search')
        if search:
            change_request = change_request.filter(
                Q(created_by__first_name__icontains=search) | Q(created_by__last_name__icontains=search) |
                Q(created_by__email__icontains=search) | Q(created_by__username__icontains=search)
            )

        paginator = LimitOffsetPagination()
        paginated_transactions = paginator.paginate_queryset(change_request, request)
        serializer = AdminChangeRequestSerializer(paginated_transactions, many=True)
        return paginator.get_paginated_response(serializer.data)


class AppTransferSumAmount(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        transaction_type = request.query_params.get('transaction_type', 'transfer')
        transactions = Transaction.objects.filter(status='active', transaction_type=transaction_type).order_by('-id')

        month = request.query_params.get('month')
        year = request.query_params.get('year')
        if month and year:
            transactions = transactions.filter(date_created__month=month, date_created__year=year)

        search = request.query_params.get('search')
        if search:
            transactions = transactions.filter(
                Q(sender__first_name__icontains=search) | Q(sender__last_name__icontains=search) |
                Q(sender__email__icontains=search) | Q(sender__username__icontains=search) |
                Q(receiver__first_name__icontains=search) | Q(receiver__last_name__icontains=search) |
                Q(receiver__email__icontains=search) | Q(receiver__username__icontains=search)
            )

        totals = transactions.aggregate(
            total_transaction_amount=Sum('amount'), total_taxable_amount=Sum('taxable_amount')
        )

        total_transaction_amount = totals['total_transaction_amount'] or 0
        total_taxable_amount = totals['total_taxable_amount'] or 0

        response_data = {
            "total_transaction_amount": total_transaction_amount,
            "taxable_amount": total_taxable_amount / 2,
            "admin_amount": total_taxable_amount / 2
        }

        return Response(response_data, status=status.HTTP_200_OK)


class WithdrawSummaryAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request, *args, **kwargs):
        queryset = FundWithdrawal.objects.filter(status='active')
        user_id = request.query_params.get('user')
        search = request.query_params.get('search')

        if user_id:
            queryset = queryset.filter(user__id=user_id)

        if search:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__email__icontains=search) |
                Q(user__username__icontains=search)
            )
        total_amount = queryset.aggregate(total=Sum('withdrawal_amount'))['total'] or 0
        approved_amount = queryset.filter(withdrawal_status='approved').aggregate(total=Sum('withdrawal_amount'))['total'] or 0
        rejected_amount = queryset.filter(withdrawal_status='rejected').aggregate(total=Sum('withdrawal_amount'))['total'] or 0
        pending_amount = queryset.filter(withdrawal_status='pending').aggregate(total=Sum('withdrawal_amount'))['total'] or 0
        taxable_amount = queryset.aggregate(taxable=Sum('withdrawal_amount'))['taxable'] or 0
        taxable_amount = round(taxable_amount * Decimal(0.05), 2)
        return Response({
            'total_amount': total_amount,
            'approved_amount': approved_amount,
            'rejected_amount': rejected_amount,
            'pending_amount': pending_amount,
            'taxable_amount': taxable_amount
        })


class AggregateChangeRequestAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        change_request_count = ChangeRequest.objects.aggregate(
            all_request=Count("id"),
            pending_request=Count("id", filter=Q(request_status='pending')),
            approved_request=Count("id", filter=Q(request_status='approved')),
            rejected_request=Count("id", filter=Q(request_status='rejected')),
        )
        return Response(change_request_count, status=status.HTTP_200_OK)


class AppBeneficiaryAPI(APIView):

    def get(self, request):
        bank_details = BankDetails.objects.filter(id=25).last()
        err, res = add_cashfree_beneficiary(bank_details)
        return Response({'error': err, 'res': res})


class ROIAggregateAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        month = int(request.query_params.get("month", datetime.datetime.now().month))
        year = int(request.query_params.get("year", datetime.datetime.now().year))
        user_id = request.query_params.get("user")

        investment = InvestmentInterest.objects.filter(
            interest_send_date__month=month, interest_send_date__year=year
        ).select_related('investment', 'investment__user')

        if user_id:
            investment = investment.filter(investment__user__id=user_id)

        total_user = investment.values('investment__user').distinct().count()
        total_amount = investment.aggregate(total=Sum('interest_amount'))['total'] or 0

        return Response({
            'total_user': total_user,
            'total_send_amount': round(total_amount, 2)
        })


class CoreGroupIncomeAggregateAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        month = int(request.query_params.get("month", datetime.datetime.now().month))
        year = int(request.query_params.get("year", datetime.datetime.now().year))
        user_id = request.query_params.get("user")

        investment = CoreIncomeEarned.objects.filter(
            date_created__month=month, date_created__year=year
        ).select_related('investment', 'investment__user')

        if user_id:
            investment = investment.filter(user__id=user_id)

        total_user = investment.values('user').distinct().count()
        total_amount = investment.aggregate(total=Sum('income_earned'))['total'] or 0

        return Response({
            'total_user': total_user,
            'total_send_amount': round(total_amount, 2)
        })


class RewardAggregateAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        month = int(request.query_params.get("month", datetime.datetime.now().month))
        year = int(request.query_params.get("year", datetime.datetime.now().year))
        user_id = request.query_params.get("user")

        rewards = RewardEarned.objects.filter(
            earned_at__month=month, earned_at__year=year
        ).select_related('reward', 'user')

        if user_id:
            rewards = rewards.filter(user__id=user_id)

        total_user = rewards.values('user').distinct().count()
        total_amount = rewards.aggregate(total=Sum('reward__gift_amount'))['total'] or 0

        return Response({
            'total_user': total_user,
            'total_reward_earned': round(total_amount, 2)
        })


class ExtraRewardAggregateAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        month = int(request.query_params.get("month", datetime.datetime.now().month))
        year = int(request.query_params.get("year", datetime.datetime.now().year))
        user_id = request.query_params.get("user")

        extra_rewards = ExtraRewardEarned.objects.filter(
            date_created__month=month, date_created__year=year
        ).select_related('extra_reward', 'user')

        if user_id:
            extra_rewards = extra_rewards.filter(user__id=user_id)

        total_user = extra_rewards.values('user').distinct().count()
        total_amount = extra_rewards.aggregate(total=Sum('amount'))['total'] or 0

        return Response({
            'total_user': total_user,
            'total_reward_earned': round(total_amount, 2)
        })


class LevelIncomeEarnedAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        month = int(request.query_params.get("month", datetime.datetime.now().month))
        year = int(request.query_params.get("year", datetime.datetime.now().year))
        user_id = request.query_params.get("user")
        type = request.query_params.get("type")

        commissions = Commission.objects.filter(
            date_created__month=month, date_created__year=year, commission_type=type
        ).select_related('commission_to', 'commission_by')

        if user_id:
            commissions = commissions.filter(commission_to__id=user_id)

        total_user = commissions.values('commission_to').distinct().count()
        total_amount = commissions.aggregate(total=Sum('amount'))['total'] or 0

        return Response({
            'total_user': total_user,
            'total_income_earned': round(total_amount, 2)
        })


class RoyaltyEarnedAggregateAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        month = int(request.query_params.get("month", datetime.datetime.now().month))
        year = int(request.query_params.get("year", datetime.datetime.now().year))
        user_id = request.query_params.get("user")

        royaltys = RoyaltyEarned.objects.filter(
            earned_date__month=month, earned_date__year=year
        ).select_related('royalty', 'user')

        if user_id:
            royaltys = royaltys.filter(user__id=user_id)

        total_user = royaltys.values('user').distinct().count()
        total_amount = royaltys.aggregate(total=Sum('earned_amount'))['total'] or 0

        return Response({
            'total_user': total_user,
            'total_amount_earned': round(total_amount, 2)
        })


class RewardEarnedAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        month = int(request.query_params.get("month", datetime.datetime.now().month))
        year = int(request.query_params.get("year", datetime.datetime.now().year))
        user_id = request.query_params.get("user")
        queryset = RewardEarned.objects.filter(status='active')
        if user_id:
            queryset = queryset.filter(user=user_id)
        if month and year:
            queryset = queryset.filter(earned_at__month=month, earned_at__year=year)
        paginator = LimitOffsetPagination()
        paginated_transactions = paginator.paginate_queryset(queryset, request)
        serializer = RewardEarnedAdminSerializer(paginated_transactions, many=True)
        return paginator.get_paginated_response(serializer.data)


class CommissionEarnedAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        month = request.query_params.get("month")
        year = request.query_params.get("year")
        user_id = request.query_params.get("user")
        commission_type = request.query_params.get("commission_type")
        queryset = Commission.objects.filter(status='active')

        if user_id:
            queryset = queryset.filter(commission_to=user_id)

        if commission_type:
            queryset = queryset.filter(commission_type=commission_type)

        if month and year:
            month = int(month)
            year = int(year)
            queryset = queryset.filter(date_created__month=month, date_created__year=year)

        paginator = LimitOffsetPagination()
        paginated_transactions = paginator.paginate_queryset(queryset, request)
        serializer = GetAllCommissionSerializer(paginated_transactions, many=True)
        return paginator.get_paginated_response(serializer.data)


class GetMLMUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        search = request.query_params.get("search")
        queryset = MLMTree.objects.filter(status='active', is_show=True)
        if search:
            queryset = queryset.filter(Q(child__username=search) | Q(child__first_name=search) |
                                       Q(child__last_name=search) | Q(child__profile__referral_code=search))
        paginator = LimitOffsetPagination()
        paginated_transactions = paginator.paginate_queryset(queryset, request)
        serializer = GetAllMLMChildSerializer(paginated_transactions, many=True)
        return paginator.get_paginated_response(serializer.data)


class GetAppDashboardAggregate(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        user = request.query_params.get("user_id", None)
        if not user:
            return Response({'message': 'User ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

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

        total_earning = (
            commission_amount + earned_reward + roi_interest + royalty_earned + core_group_income + extra_income
        )

        data = {
            'total_team_member': total_team_count,
            'total_earning': total_earning,
            'total_id_value': total_return_amount,
            'total_direct_user_count': referrals,
            'direct_income': direct_income,
            'level_income': level_income,
            'royalty_income': royalty_earned,
            'reward_income': earned_reward,
            'extra_reward_income': extra_income,
            'core_group_income': core_group_income,
            'total_top_up_count': investments.count(),
        }
        return Response(data, status=status.HTTP_200_OK)


class RoyaltyEarnedAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        month = int(request.query_params.get("month", datetime.datetime.now().month))
        year = int(request.query_params.get("year", datetime.datetime.now().year))
        user_id = request.query_params.get("user")
        queryset = RoyaltyEarned.objects.filter(status='active')
        if user_id:
            queryset = queryset.filter(user=user_id)
        if month and year:
            queryset = queryset.filter(earned_date__month=month, earned_date__year=year)
        paginator = LimitOffsetPagination()
        paginated_transactions = paginator.paginate_queryset(queryset, request)
        serializer = RoyaltyEarnedAdminSerializer(paginated_transactions, many=True)
        return paginator.get_paginated_response(serializer.data)


class ExtraRewardEarnedAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        month = int(request.query_params.get("month", datetime.datetime.now().month))
        year = int(request.query_params.get("year", datetime.datetime.now().year))
        user_id = request.query_params.get("user")
        queryset = ExtraRewardEarned.objects.filter(status='active')
        if user_id:
            queryset = queryset.filter(user=user_id)
        if month and year:
            queryset = queryset.filter(date_created__month=month, date_created__year=year)
        paginator = LimitOffsetPagination()
        paginated_transactions = paginator.paginate_queryset(queryset, request)
        serializer = ExtraRewardEarnedAdminSerializer(paginated_transactions, many=True)
        return paginator.get_paginated_response(serializer.data)


class ROIEarnedListAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        month = int(request.query_params.get("month", datetime.datetime.now().month))
        year = int(request.query_params.get("year", datetime.datetime.now().year))
        user_id = request.query_params.get("user")
        queryset = InvestmentInterest.objects.filter(status='active').select_related('investment', 'investment__user')
        if user_id:
            queryset = queryset.filter(investment__user=user_id)
        if month and year:
            queryset = queryset.filter(interest_send_date__month=month, interest_send_date__year=year)
        paginator = LimitOffsetPagination()
        paginated_transactions = paginator.paginate_queryset(queryset, request)
        serializer = ROIEarnedAdminSerializer(paginated_transactions, many=True)
        return paginator.get_paginated_response(serializer.data)


class ActiveUserWalletListView(ListAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = UserWalletSerializer

    def get_queryset(self):
        return UserWallet.objects.active().select_related('user')


class StopSendingROIListView(APIView):
    permission_classes = [IsStaffUser]

    def post(self, request, user_id):
        user_profile = Profile.objects.filter(status='active', user=user_id).last()

        if not user_profile:
            return Response({'message': 'Invalid User ID.'}, status=status.HTTP_400_BAD_REQUEST)

        if not user_profile.is_roi_send:
            return Response({'message': 'You cannot perform any action, we already stop ROI to this user.'},
                            status=status.HTTP_400_BAD_REQUEST)

        user_profile.is_roi_send = False
        user_profile.save()
        ROIUpdateLog.objects.create(created_by=self.request.user, action_for=user_profile.user, roi_status='stop')
        return Response({'message': 'ROI status updated successfully.'}, status=status.HTTP_200_OK)


class StartSendingROIListView(APIView):
    permission_classes = [IsStaffUser]

    def post(self, request, user_id):
        user_profile = Profile.objects.filter(status='active', user=user_id).last()

        if not user_profile:
            return Response({'message': 'Invalid User ID.'}, status=status.HTTP_400_BAD_REQUEST)

        if user_profile.is_roi_send:
            return Response({'message': 'You cannot perform any action, we already start ROI to this user.'},
                            status=status.HTTP_400_BAD_REQUEST)

        user_profile.is_roi_send = True
        user_profile.save()
        ROIUpdateLog.objects.create(created_by=self.request.user, action_for=user_profile.user, roi_status='start')
        return Response({'message': 'ROI status updated successfully.'}, status=status.HTTP_200_OK)


class SendExtraRewardAPIView(APIView):
    permission_classes = [IsStaffUser]

    def post(self, request):
        user_id = self.request.POST.get('user_id')
        extra_reward_id = self.request.POST.get('reward_id')
        amount = self.request.POST.get('amount')
        description = self.request.POST.get('description')

        get_user = User.objects.filter(id=user_id).last()
        get_extra_reward = ExtraReward.objects.filter(id=extra_reward_id).last()

        if not get_user:
            return Response({'message': 'Invalid User ID.'}, status=status.HTTP_400_BAD_REQUEST)
        if not get_extra_reward:
            return Response({'message': 'Invalid Reward ID.'}, status=status.HTTP_400_BAD_REQUEST)

        is_already_earned = ExtraRewardEarned.objects.filter(
            status='active', user=get_user, extra_reward=get_extra_reward
        ).exists()

        if is_already_earned:
            return Response({'message': 'User Already earned this extra reward.'}, status=status.HTTP_400_BAD_REQUEST)

        ExtraRewardEarned.objects.create(
            created_by=self.request.user, extra_reward=get_extra_reward,
            user=get_user, amount=amount,
            description=description or f'Congratulation! You earned extra reward worth {amount}'
        )

        Transaction.objects.create(
            sender=get_user, receiver=get_user, amount=amount, transaction_type='reward',
            transaction_status='approved',
            payment_method='wallet', verified_by=self.request.user, verified_on=datetime.datetime.now()
        )

        InAppNotification.objects.create(created_by=self.request.user, user=get_user,
                                         message='Bonus unlocked! Your extra reward has been successfully credited.',
                                         notification_type='alert')

        return Response({'message': 'Extra Reward send successfully.'}, status=status.HTTP_200_OK)


class SendRewardAPIView(APIView):
    permission_classes = [IsStaffUser]

    def post(self, request):
        user_id = self.request.POST.get('user_id')
        extra_reward_id = self.request.POST.get('reward_id')
        description = self.request.POST.get('description')

        get_user = User.objects.filter(id=user_id).last()
        get_reward = RewardMaster.objects.filter(id=extra_reward_id).last()

        if not get_user:
            return Response({'message': 'Invalid User ID.'}, status=status.HTTP_400_BAD_REQUEST)
        if not get_reward:
            return Response({'message': 'Invalid Reward ID.'}, status=status.HTTP_400_BAD_REQUEST)

        is_already_earned = RewardEarned.objects.filter(
            status='active', user=get_user, reward=get_reward
        ).exists()

        if is_already_earned:
            return Response({'message': 'User Already earned this reward.'}, status=status.HTTP_400_BAD_REQUEST)

        RewardEarned.objects.create(
            created_by=self.request.user, reward=get_reward, user=get_user, turnover_at_earning=get_reward.gift_amount,
            description=description or f'Congratulation! You earned reward worth {get_reward.gift_amount}',
            earned_at=datetime.datetime.now().today().replace(day=1), is_paid=True, is_p2p=True,
            total_month=get_reward.total_paid_month,
            last_payment_send=datetime.datetime.now().today().replace(day=1), total_installment_paid=get_reward.total_paid_month-1
        )

        wallet, _ = UserWallet.objects.get_or_create(user=get_user)
        wallet.app_wallet_balance += get_reward.gift_amount
        wallet.save()

        Transaction.objects.create(
            sender=get_user, receiver=get_user, amount=get_reward.gift_amount, transaction_type='reward',
            transaction_status='approved',
            payment_method='wallet', verified_by=self.request.user, verified_on=datetime.datetime.now(),
            remarks=f'Congratulation! You earned reward worth {get_reward.gift_amount}'
        )

        return Response({'message': 'Reward send successfully.'}, status=status.HTTP_200_OK)


class InvestmentDelete(APIView):
    permission_classes = [IsStaffUser]

    def delete(self, request, id):
        Investment.objects.filter(id=id).delete()
        return Response({'message': 'Investment deleted successfully.'}, status=status.HTTP_200_OK)


class GetAllTopUpList(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        paginator = PageNumberPagination()
        paginator.page_size = int(request.query_params.get("page_size", 20))

        users = MLMTree.objects.filter(status='active', is_show=True).order_by('-id')
        paginated_users = paginator.paginate_queryset(users, request)

        data = []
        for user in paginated_users:
            total_invested_amount = (
                Investment.objects.filter(
                    status="active", user=user.child,
                    package__isnull=False, investment_type="p2pmb"
                )
                .aggregate(total=Sum("amount"))["total"] or Decimal(0)
            )

            check_working_id = MLMTree.objects.filter(referral_by=user.child).count()
            if check_working_id >= 2:
                is_working_id = True
                total_return_amount = total_invested_amount * Decimal("4.4")
            else:
                is_working_id = False
                total_return_amount = total_invested_amount * Decimal("2.1")

            total_commission_earned = (
                Commission.objects.filter(status="active", commission_to=user.child,
                                          commission_type__in=['direct', 'level'])
                .aggregate(total_amount=Sum("amount"))["total_amount"] or Decimal(0)
            )

            roi_earned = (
                InvestmentInterest.objects.filter(status="active", investment__user=user.child)
                .aggregate(total_amount=Sum("interest_amount"))["total_amount"] or Decimal(0)
            )

            royalty_earned = (
                RoyaltyEarned.objects.filter(status="active", user=user.child)
                .aggregate(total_amount=Sum("earned_amount"))["total_amount"] or Decimal(0)
            )

            reward_earned = (
                RewardEarned.objects.filter(status="active", user=user.child)
                .aggregate(total_amount=Sum("reward__gift_amount"))["total_amount"] or Decimal(0)
            )

            core_group_income = (
                CoreIncomeEarned.objects.filter(status="active", user=user.child)
                .aggregate(total=Sum("income_earned"))["total"] or Decimal(0)
            )

            extra_income = (
                ExtraRewardEarned.objects.filter(status="active", user=user.child)
                .aggregate(total=Sum("amount"))["total"] or Decimal(0)
            )

            total_income_earned = (
                total_commission_earned + roi_earned + royalty_earned +
                reward_earned + core_group_income + extra_income
            )

            current_due_value = total_return_amount - total_income_earned
            fifty_percentage_of_value = total_return_amount * Decimal("0.50")

            is_low_balance = current_due_value <= fifty_percentage_of_value

            data.append({
                "investment_amount": total_invested_amount,
                "is_working_id": is_working_id,
                "total_return_amount": total_return_amount,
                "total_income_earned": total_income_earned,
                "current_due_values": current_due_value,
                "is_low_balance": is_low_balance,
                "user": {
                    'id': user.child.id,
                    'name': user.child.get_full_name(),
                    'username': user.child.username,
                    'referral_code': user.child.profile.referral_code,
                    'email': user.child.email
                },
            })

        return paginator.get_paginated_response(data)