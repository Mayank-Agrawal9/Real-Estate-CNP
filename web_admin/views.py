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
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Profile, BankDetails, UserPersonalDocument
from p2pmb.models import Commission
from property.models import Property
from web_admin.models import ManualFund, CompanyInvestment, ContactUsEnquiry, PropertyInterestEnquiry, \
    UserFunctionalityAccessPermission
from web_admin.serializers import ProfileSerializer, InvestmentSerializer, ManualFundSerializer, BankDetailSerializer, \
    UserDocumentSerializer, SuperAgencyCompanyDetailSerializer, AgencyCompanyDetailSerializer, \
    FieldAgentCompanyDetailSerializer, PropertyInterestEnquirySerializer, ContactUsEnquirySerializer, \
    GetPropertySerializer, PropertyDetailSerializer, UserCreateSerializer, LoginSerializer, \
    UserPermissionProfileSerializer
from agency.models import Investment, FundWithdrawal, SuperAgency, Agency, FieldAgent
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
    filterset_fields = ['is_kyc', 'is_kyc_verified', 'is_p2pmb']
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
    filterset_fields = ['created_by', ]

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
        user_id = request.query_params.get('user_id')
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
            Profile.objects.filter(user=user_id).update(kyc_remarks=remarks)
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
            funds = ManualFund.objects.filter(date_created__date__range=[start_date, end_date])
            funds_dict = {entry['date_created__date']: entry['total_amount'] for entry in funds.values('date_created__date').annotate(total_amount=Sum('amount'))}
            data = [{"date": date, "total_amount": funds_dict.get(date, 0)} for date in all_dates]

        elif filter_type == 'month_wise':
            months = range(1, 13)
            funds = ManualFund.objects.filter(date_created__year=current_year).values('date_created__month').annotate(
                total_amount=Sum('amount'))
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
                total = ManualFund.objects.filter(date_created__year=current_year,
                                                  date_created__month__gte=start_month,
                                                  date_created__month__lte=end_month).aggregate(Sum('amount'))['amount__sum'] or 0
                data.append({"quarter": quarter, "total_amount": total})

        elif filter_type == 'half_yearly':
            halves = {
                'H1 (Jan-Jun)': (1, 6),
                'H2 (Jul-Dec)': (7, 12)
            }
            for half, (start_month, end_month) in halves.items():
                total = ManualFund.objects.filter(date_created__year=current_year,
                                                  date_created__month__gte=start_month,
                                                  date_created__month__lte=end_month).aggregate(Sum('amount'))['amount__sum'] or 0
                data.append({"half_year": half, "total_amount": total})

        elif filter_type == 'yearly':
            for year in range(current_year - 1, current_year + 1):
                total = ManualFund.objects.filter(date_created__year=year).aggregate(Sum('amount'))['amount__sum'] or 0
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
                                               is_approved=True, pay_method='main_wallet').aggregate(
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
                                                   is_approved=True, pay_method='main_wallet').aggregate(
                total_amount=Sum('amount'))['total_amount'] or Decimal(0)
        elif applicable_for == 'agency':
            total_fund = Investment.objects.filter(**filters, investment_type='agency', package__isnull=False,
                                                   is_approved=True, pay_method='main_wallet').aggregate(
                total_amount=Sum('amount'))['total_amount'] or Decimal(0)
        elif applicable_for == 'field_agent':
            total_fund = Investment.objects.filter(**filters, investment_type='field_agent', package__isnull=False,
                                                   is_approved=True, pay_method='main_wallet').aggregate(
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
