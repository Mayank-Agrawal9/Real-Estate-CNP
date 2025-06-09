import datetime
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

from accounts.models import Profile, BankDetails, UserPersonalDocument
from master.models import CoreGroupIncome
from p2pmb.models import Commission, MLMTree, CoreIncomeEarned
from property.models import Property
from web_admin.models import ManualFund, CompanyInvestment, ContactUsEnquiry, PropertyInterestEnquiry, \
    UserFunctionalityAccessPermission
from web_admin.serializers import ProfileSerializer, InvestmentSerializer, ManualFundSerializer, BankDetailSerializer, \
    UserDocumentSerializer, SuperAgencyCompanyDetailSerializer, AgencyCompanyDetailSerializer, \
    FieldAgentCompanyDetailSerializer, PropertyInterestEnquirySerializer, ContactUsEnquirySerializer, \
    GetPropertySerializer, PropertyDetailSerializer, UserCreateSerializer, LoginSerializer, \
    UserPermissionProfileSerializer, ListWithDrawRequest, UserWithWorkingIDSerializer, GetAllCommissionSerializer, \
    CompanyInvestmentSerializer, TransactionDetailSerializer
from agency.models import Investment, FundWithdrawal, SuperAgency, Agency, FieldAgent, InvestmentInterest
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
        profiles = Profile.objects.filter(is_kyc=True, is_kyc_verified=False)
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

        admin_paid_amount = ManualFund.objects.filter(status="active").aggregate(Sum("amount"))["amount__sum"]
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
        commission_filter = {}

        if month:
            filters['date_created__month'] = month
            investment_filter['initiated_date__month'] = month
            commission_filter['date_created__month'] = month
        if year:
            filters['date_created__year'] = year
            investment_filter['initiated_date__year'] = year
            commission_filter['date_created__year'] = year

        total_fund = Investment.objects.filter(**filters, investment_type='p2pmb', package__isnull=False,
                                               is_approved=True, pay_method='main_wallet').distinct().aggregate(
            total_amount=Sum('amount'))['total_amount'] or Decimal(0)

        fund_initiated = CompanyInvestment.objects.filter(**investment_filter)
        commissions = Commission.objects.filter(**commission_filter)

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
        investments = Investment.objects.filter(
            status='active', investment_type='p2pmb', is_approved=True,
            package__isnull=False, pay_method='main_wallet'
        ).values('user_id').annotate(total_amount=Sum('amount'))

        investment_map = {item['user_id']: item['total_amount'] for item in investments}
        referrals = MLMTree.objects.filter(is_show=True).values_list('referral_by_id', 'child_id')
        referral_map = {}
        for referral_by_id, child_id in referrals:
            referral_map.setdefault(referral_by_id, []).append(child_id)

        working_ids = set()
        for user_id, user_investment in investment_map.items():
            if user_investment == 0:
                continue
            referral_ids = referral_map.get(user_id, [])
            eligible_referrals = [
                rid for rid in referral_ids
                if investment_map.get(rid, Decimal('0')) >= user_investment
            ]
            if len(eligible_referrals) >= 2:
                working_ids.add(user_id)

        total_return_amount = Decimal('0')
        for user_id, amount in investment_map.items():
            multiplier = 4 if user_id in working_ids else 2
            total_return_amount += amount * Decimal(multiplier)

        total_investment = Investment.objects.filter(status='active').aggregate(
            total_amount=Sum("amount", filter=Q(
                is_approved=True, investment_type="p2pmb", package__isnull=False, pay_method='main_wallet'
            ))
        )['total_amount'] or Decimal(0)

        total_income_earned = Commission.objects.filter(status='active').aggregate(
            total_amount=Sum('amount'))['total_amount'] or Decimal(0)

        total_interest_earned = InvestmentInterest.objects.filter(status='active').aggregate(
            total_amount=Sum('interest_amount'))['total_amount'] or Decimal(0)

        core_group_earned = CoreIncomeEarned.objects.filter(status='active').aggregate(
            total_amount=Sum('income_earned'))['total_amount'] or Decimal(0)

        result = {
            'total_investment': total_investment,
            'total_return_amount': total_income_earned + total_interest_earned + core_group_earned,
            'total_send_amount': total_return_amount,
        }
        return Response(result, status=status.HTTP_200_OK)


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

        withdraw = FundWithdrawal.objects.filter(id=withdraw_id)

        if not withdraw:
            return Response({"error": "Invalid withdraw Id."}, status=status.HTTP_400_BAD_REQUEST)

        if action == "approved":
            # Add Logic For Send Money and add interest
            deducted_amount = withdraw.withdrawal_amount * 0.95
            taxable_amount = withdraw.withdrawal_amount - deducted_amount
            Transaction.objects.create(
                sender=withdraw.user, receiver=withdraw.user, amount=deducted_amount,
                transaction_type='receive', transaction_status='deposit', payment_method='upi',
                remarks='Added remarks', verified_by=self.request.user, verified_on=datetime.datetime.now(),
                taxable_amount=taxable_amount
            )
            wallet_amount = UserWallet.objects.filter(user=withdraw.user).last()
            wallet_amount -= withdraw.withdrawal_amount
            wallet_amount.save()
            withdraw.update(withdrawal_status="approved", rejection_reason=None, is_paid=True, action_date=datetime.datetime.now())
        elif action == "rejected":
            withdraw.update(withdrawal_status="rejected", rejection_reason=rejection_reason, action_date=datetime.datetime.now())

        return Response({"detail": f"Withdraw {action} successfully."})


class UserWithWorkingIDListView(ListAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = UserWithWorkingIDSerializer

    def get_queryset(self):
        queryset = MLMTree.objects.filter(is_show=True).select_related('child', 'parent').all()
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
        ).values('user_id').annotate(total_amount=Sum('amount'))

        investment_map = {item['user_id']: item['total_amount'] for item in investments}

        referrals = MLMTree.objects.filter(is_show=True).values_list('referral_by_id', 'child_id')
        referral_map = {}
        for referral_by_id, child_id in referrals:
            referral_map.setdefault(referral_by_id, []).append(child_id)

        working_ids = set()
        for user_id, user_investment in investment_map.items():
            if user_investment == 0:
                continue
            referral_ids = referral_map.get(user_id, [])
            eligible_referrals = [
                rid for rid in referral_ids
                if investment_map.get(rid, Decimal('0')) >= user_investment
            ]
            if len(eligible_referrals) >= 2:
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
        is_working = request.query_params.get('working', None)

        if not user_id:
            return Response({'message': 'User ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        get_investment = Investment.objects.filter(status='active', package__isnull=False, investment_type='p2pmb',
                                                   user=user_id).last()
        if is_working:
            is_working_id = True
            total_return_amount = (get_investment.amount or 0) * 4
        else:
            is_working_id = False
            total_return_amount = (get_investment.amount or 0) * 2

        total_income_earned = Commission.objects.filter(commission_to=user_id, status='active').aggregate(
            total_amount=Sum('amount'))['total_amount'] or Decimal(0)

        total_interest_earned = InvestmentInterest.objects.filter(investment__user=user_id, status='active').aggregate(
            total_amount=Sum('interest_amount'))['total_amount'] or Decimal(0)

        core_group_earned = CoreIncomeEarned.objects.filter(status='active').aggregate(
            total_amount=Sum('income_earned'))['total_amount'] or Decimal(0)

        current_due_value = total_return_amount - total_income_earned - total_interest_earned - core_group_earned
        twenty_percentage_of_value = total_return_amount * Decimal(0.20)

        if current_due_value > twenty_percentage_of_value:
            is_low_balance = False
        else:
            is_low_balance = True

        response = {
            'investment_amount': get_investment.amount,
            'is_working_id': is_working_id,
            'total_return_amount': total_return_amount,
            'total_income_earned': total_income_earned + total_interest_earned + core_group_earned,
            'current_due_values': current_due_value,
            'is_low_balance': is_low_balance,
        }
        return Response(response, status=status.HTTP_200_OK)


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
        transactions = Transaction.objects.filter(status='active', transaction_type='transfer').order_by('-id')
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

        paginator = LimitOffsetPagination()
        paginated_transactions = paginator.paginate_queryset(transactions, request)
        serializer = TransactionDetailSerializer(paginated_transactions, many=True)
        return paginator.get_paginated_response(serializer.data)


class AppTransferSumAmount(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        transactions = Transaction.objects.filter(status='active', transaction_type='transfer')

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
