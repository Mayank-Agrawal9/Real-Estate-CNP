import datetime
import random
from decimal import Decimal
import requests

from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import transaction
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.helpers import generate_unique_referral_code, update_super_agency_profile, generate_qr_code_with_email, \
    update_agency_profile, update_field_agent_profile
from accounts.models import OTP, Profile, BankDetails, UserPersonalDocument, SoftwarePolicy, FAQ
from accounts.serializers import RequestOTPSerializer, VerifyOTPSerializer, ResendOTPSerializer, ProfileSerializer, \
    SuperAgencyKycSerializer, BasicDetailsSerializer, CompanyDetailsSerializer, BankDetailsSerializer, \
    DocumentSerializer, FAQSerializer
from agency.models import SuperAgency, FieldAgent, Agency, Investment
from payment_app.models import UserWallet, Transaction
from real_estate import settings


# Create your views here.

class RequestOTPView(APIView):
    def post(self, request):
        serializer = RequestOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp_code = str(random.randint(100000, 999999))
            OTP.objects.update_or_create(
                email=email,
                defaults={
                    "otp": otp_code,
                    "valid_until": datetime.datetime.now() + datetime.timedelta(minutes=10),
                },
            )
            send_mail(
                "Your OTP Code",
                f"Your OTP code is {otp_code}. It is valid for 10 minutes.",
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            return Response({"message": "OTP sent to your email.", "otp": otp_code}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyOTPView(APIView):
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp_code = serializer.validated_data['otp']

            try:
                otp_entry = OTP.objects.get(email=email)
            except Exception as e:
                return Response({"error": "Invalid email or OTP."}, status=status.HTTP_400_BAD_REQUEST)

            if not otp_entry.is_valid():
                return Response(
                    {"error": "OTP has expired. Please request a new OTP."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if otp_entry.otp != otp_code:
                return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

            otp_entry.delete()
            user, created = User.objects.get_or_create(username=email, defaults={"email": email})
            referral_code = generate_unique_referral_code()
            qr_code_file = generate_qr_code_with_email(email, user.id)

            profile, created = Profile.objects.get_or_create(user=user, defaults={
                "created_by": user,
                "referral_code": referral_code,
                "qr_code": qr_code_file,
            })

            if not created:
                profile.referral_code = referral_code
                profile.qr_code = qr_code_file
                profile.save()

            UserWallet.objects.get_or_create(user=user, created_by=user)
            token, _ = Token.objects.get_or_create(user=user)

            return Response({
                "message": "Login successful.",
                "token": token.key,
                "user_id": user.id,
                "picture": profile.picture if profile and profile.picture else None,
                "role": profile.role,
                "referral_code": referral_code,
                "name": user.get_full_name(),
                "email": user.email,
                "qr_code_url": profile.qr_code.url if profile.qr_code else None,
            }, status=status.HTTP_200_OK)


class ResendOTPView(APIView):
    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                otp_entry = OTP.objects.get(email=email)
            except Exception as e:
                return Response({"error": "Email not found. Please request a new OTP first."},
                                status=status.HTTP_404_NOT_FOUND)

            if not otp_entry.can_resend():
                return Response(
                    {"error": "You can only request a new OTP after 1 minute."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )

            new_otp = str(random.randint(100000, 999999))
            otp_entry.otp = new_otp
            otp_entry.valid_until = datetime.datetime.now() + datetime.timedelta(minutes=10)
            otp_entry.last_resend = datetime.datetime.now()
            otp_entry.save()
            # send_mail(
            #     subject="Your OTP Code",
            #     message=f"Your OTP code is {new_otp}. It is valid for 10 minutes.",
            #     from_email=settings.DEFAULT_FROM_EMAIL,
            #     recipient_list=[email],
            #     fail_silently=False,
            # )
            return Response({"message": "A new OTP has been sent to your email."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            token = Token.objects.get(user=request.user)
            token.delete()
            return Response({'message': 'Successfully logged out.'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': 'Invalid token or already logged out.'},
                            status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = Profile.objects.get(user=request.user)
            serializer = ProfileSerializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request):
        try:
            profile = Profile.objects.get(user=request.user)
            serializer = ProfileSerializer(profile, data=request.data, partial=False)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)


class UserKycAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile = Profile.objects.filter(user=user).first()

        if not profile:
            return Response({"error": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)

        basic_details = BasicDetailsSerializer(profile).data

        if profile.role == "field_agent":
            company_details_instance = None
        elif profile.role == "agency":
            company_details_instance = Agency.objects.filter(created_by=user).first()
        elif profile.role == "super_agency":
            company_details_instance = SuperAgency.objects.filter(profile=profile).first()
        else:
            company_details_instance = None

        company_details = (
            CompanyDetailsSerializer(company_details_instance).data
            if company_details_instance
            else None
        )

        bank_details = BankDetailsSerializer(
            BankDetails.objects.filter(user=user).first()
        ).data
        documents = DocumentSerializer(
            UserPersonalDocument.objects.filter(created_by=user), many=True
        ).data

        response_data = {
            "basic_details": basic_details,
            "company_details": company_details,
            "bank_details": bank_details,
            "documents_for_kyc": documents,
        }

        return Response(response_data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = SuperAgencyKycSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        user = request.user
        try:
            with transaction.atomic():
                basic_details = data["basic_details"]
                role = basic_details["role"]
                if role == "super_agency":
                    update_super_agency_profile(user, data, "super_agency")
                elif role == "agency":
                    update_agency_profile(user, data, "agency")
                elif role == "field_agent":
                    update_field_agent_profile(user, data, "field_agent")
            return Response({"message": "Data updated successfully!"}, status=status.HTTP_200_OK)

        except ValidationError as e:
            error_message = e.detail if isinstance(e.detail, str) else e.detail[0]
            return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "Something went wrong", "details": str(e)},
                            status=status.HTTP_400_BAD_REQUEST)


class VerifyAndUpdateProfile(APIView):
    permission_classes = [IsAuthenticated]

    def update_wallet_and_transaction_(self, user, verify_by, amount, remarks):
        wallet, _ = UserWallet.objects.get_or_create(user=user)
        wallet.app_wallet_balance += amount
        wallet.save()
        Transaction.objects.create(
            created_by=user,
            sender=user,
            amount=amount,
            transaction_type='commission',
            transaction_status='approved',
            verified_by=verify_by,
            verified_on=datetime.datetime.now(),
            remarks=remarks
        )

    def update_transaction_of_user_(self, transaction_instance, request_user):
        if transaction_instance and transaction_instance.transaction_id:
            transaction_instance.transaction_id.transaction_status = 'approved'
            transaction_instance.transaction_id.verified_by = request_user
            transaction_instance.transaction_id.verified_on = datetime.datetime.now()
            transaction_instance.transaction_id.save()

    def update_investment_of_user_(self, transaction_instance, request_user):
        if transaction_instance:
            transaction_instance.is_approved = True
            transaction_instance.updated_by = request_user
            transaction_instance.save()

    def post(self, request):
        user_id = request.data.get('user_id')
        investment_id = int(request.data.get('investment_id'))
        try:
            with transaction.atomic():
                profile = Profile.objects.filter(user=user_id).last()
                if profile.is_kyc and profile.is_kyc_verified:
                    return Response({"error": "KYC is already verified for this user."},
                                    status=status.HTTP_400_BAD_REQUEST)
                investment_instance = Investment.objects.filter(id=investment_id).last()
                if not investment_instance:
                    return Response({"error": "Invalid transaction id."}, status=status.HTTP_400_BAD_REQUEST)

                profile.is_kyc_verified = True
                profile.verified_by = request.user
                profile.verified_on = datetime.datetime.now()
                profile.save()
                self.update_transaction_of_user_(investment_instance, request.user)
                self.update_transaction_of_user_(investment_instance, request.user)

                if profile.role == 'agency':
                    super_agency = Agency.objects.filter(created_by=profile.user).last()
                    if super_agency and super_agency.company:
                        commission = Decimal(str(investment_instance.transaction_id.amount * 0.25))
                        self.update_wallet_and_transaction_(
                            super_agency.company.profile.user,
                            request.user,
                            commission,
                            'Commission added due to agency added.'
                        )
                elif profile.role == 'field_agent':
                    field_agent = FieldAgent.objects.filter(profile=profile).last()
                    if field_agent and field_agent.agency:
                        commission = Decimal(str(investment_instance.transaction_id.amount * 0.25))
                        self.update_wallet_and_transaction_(
                            field_agent.agency.created_by,
                            request.user,
                            commission,
                            'Commission added due to field agent added.'
                        )
                        if field_agent.agency.company:
                            commission = Decimal(str(investment_instance.transaction_id.amount * 0.05))
                            self.update_wallet_and_transaction_(
                                field_agent.agency.company.profile.user,
                                request.user,
                                commission,
                                'Commission added due to field agent added.'
                            )

                return Response({"message": "Profile verified and amounts distributed successfully."},
                                status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GetUserFriendReferralCodeDetails(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        friend_referral_code = request.data.get('friend_referral_code')

        if not friend_referral_code:
            return Response(
                {'status_code': 400, 'message': 'Referral Code is Required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        profile = Profile.objects.filter(referral_code=friend_referral_code, is_kyc=True,
                                         is_kyc_verified=True).first()

        if not profile:
            return Response({'status_code': 400, 'message': 'Invalid referral code or the user has not completed KYC.'
                }, status=status.HTTP_400_BAD_REQUEST)

        role_to_user_for = {
            'super_agency': 'agent',
            'agent': 'field_agent'
        }
        user_for = role_to_user_for.get(profile.role, 'customer')

        data = {
            'cnp_id': profile.user.username,
            'friend_role': profile.role,
            'user_for': user_for
        }
        return Response({
                'status_code': 200, 'message': 'Fetched data successfully.', 'friend_referral_data': data
            }, status=status.HTTP_200_OK)


class VerifyBankIFSCCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user_data = request.data
        ifsc_code = user_data.get('ifsc_code').upper()
        indication = user_data.get('indication', 'external')

        if not ifsc_code:
            return Response(
                {'status_code': 400, 'message': 'IFSC code is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            api_url = f"https://ifsc.razorpay.com/{ifsc_code}"
            api_resp = requests.get(api_url, timeout=5)
            api_resp.raise_for_status()
            bank_details = api_resp.json()
        except Exception as e:
            error_message = 'Invalid IFSC code'
            if indication == 'internal':
                return None
            return Response({'status_code': 400, 'message': error_message}, status=status.HTTP_400_BAD_REQUEST)

        # Extract bank details
        bank_name = bank_details.get('BANK')
        bank_address = bank_details.get('ADDRESS')

        response_data = {
            'status_code': 200,
            'message': 'data fetched successfully.',
            'bank_name': bank_name,
            'bank_address': bank_address,
            'ifsc_code': ifsc_code
        }
        if indication == 'internal':
            return response_data

        return Response(response_data, status=status.HTTP_200_OK)


# class RoleAndRewardsAPIView(APIView):
#     """
#     Handles role assignment, commissions, and rewards for SuperAgency, Agency, and Field Agent.
#     """
#
#     @transaction.atomic
#     def assign_super_agency(self, user):
#         """
#         Assigns the SuperAgency role and starts the rent refund.
#         """
#         profile = user.profile
#         profile.role = "super_agency"
#         profile.save()
#
#         # Schedule rent refunds (₹50k per month for 10 years)
#         today = datetime.datetime.now().date().today()
#         for i in range(120):
#             RentRefund.objects.create(
#                 user=user,
#                 amount=50000,
#                 due_date=today + datetime.timedelta(days=i * 30)
#             )
#
#         return {"message": f"{user.username} is now a SuperAgency with rent refunds initiated."}
#
#     @transaction.atomic
#     def assign_agency(self, user, referral_code):
#         """
#         Assigns the Agency role using a SuperAgency's referral code.
#         Adds a bonus of ₹1.25 lakh to the SuperAgency.
#         """
#         try:
#             # Validate referral code
#             referrer_profile = Profile.objects.get(referral_code=referral_code, role="super_agency")
#
#             # Assign role
#             profile = user.profile
#             profile.role = "agency"
#             profile.referral_by = referrer_profile.user
#             profile.save()
#
#             # Add ₹1.25 lakh to SuperAgency
#             company = referrer_profile.user.user_company
#             company.income += Decimal(125000)
#             company.save()
#
#             return {"message": f"{user.username} is now an Agency. SuperAgency {referrer_profile.user.username} received ₹1.25 lakh bonus."}
#         except Profile.DoesNotExist:
#             raise ValidationError({"error": "Invalid referral code or referrer is not a SuperAgency."})
#
#     @transaction.atomic
#     def assign_field_agent(self, user, referral_code):
#         """
#         Assigns the Field Agent role using an Agency's referral code.
#         Updates commissions for the referring Agency and SuperAgency.
#         """
#         try:
#             # Validate referral code
#             referrer_profile = Profile.objects.get(referral_code=referral_code, role="agency")
#             super_agency_profile = referrer_profile.referral_by.profile
#
#             # Assign role
#             profile = user.profile
#             profile.role = "field_agent"
#             profile.referral_by = referrer_profile.user
#             profile.save()
#
#             # Example Field Agent turnover
#             turnover = Decimal(100000)  # Example income
#
#             # Allocate 5% to SuperAgency
#             super_agency_income = turnover * Decimal(0.05)
#             super_agency_profile.user.user_company.income += super_agency_income
#             super_agency_profile.user.user_company.save()
#
#             # Allocate 0.25% of Agency turnover to SuperAgency
#             agency_income = turnover * Decimal(0.0025)
#             referrer_profile.user.user_company.income += agency_income
#             referrer_profile.user.user_company.save()
#
#             return {"message": f"{user.username} is now a Field Agent. Commissions distributed."}
#         except Profile.DoesNotExist:
#             raise ValidationError({"error": "Invalid referral code or referrer is not an Agency."})
#
#     def check_rewards(self, agency):
#         """
#         Assign rewards based on Agency turnover milestones.
#         """
#         turnover = agency.turnover
#         rewards = [
#             (Decimal(25_00_000), "Android mobile worth ₹10,000"),
#             (Decimal(50_00_000), "Goa trip (₹25,000)"),
#             (Decimal(1_00_00_000), "Bangkok trip (₹40,000)"),
#             (Decimal(2_50_00_000), "Dubai trip (5 nights, 6 days)"),
#             (Decimal(5_00_00_000), "Bullet bike down payment (₹1.5 lakh)"),
#             (Decimal(10_00_00_000), "Car fund down payment (₹3 lakh)"),
#             (Decimal(25_00_00_000), "Foreign trip (₹5 lakh)"),
#             (Decimal(50_00_00_000), "Vacation (₹10 lakh)"),
#             (Decimal(100_00_00_000), "Studio flat (₹25 lakh)"),
#             (Decimal(250_00_00_000), "2 BHK flat (₹50 lakh)"),
#             (Decimal(500_00_00_000), "Car fund (₹1 crore)"),
#             (Decimal(1_000_00_00_000), "6 BHK villa + Range Rover (₹5 crore)"),
#         ]
#
#         assigned_rewards = []
#         for milestone, reward in rewards:
#             if turnover >= milestone and not Reward.objects.filter(agency=agency, description=reward).exists():
#                 Reward.objects.create(agency=agency, description=reward, value=milestone)
#                 assigned_rewards.append(reward)
#
#         return assigned_rewards
#
#     def post(self, request, *args, **kwargs):
#         """
#         Handles role assignment and reward checking.
#         """
#         user = request.user
#         role = request.data.get("role")
#         referral_code = request.data.get("referral_code", None)
#
#         if not role:
#             return Response({"error": "Role is required."}, status=status.HTTP_400_BAD_REQUEST)
#
#         try:
#             if role == "super_agency":
#                 result = self.assign_super_agency(user)
#             elif role == "agency":
#                 if not referral_code:
#                     return Response({"error": "Referral code is required for Agency."}, status=status.HTTP_400_BAD_REQUEST)
#                 result = self.assign_agency(user, referral_code)
#             elif role == "field_agent":
#                 if not referral_code:
#                     return Response({"error": "Referral code is required for Field Agent."}, status=status.HTTP_400_BAD_REQUEST)
#                 result = self.assign_field_agent(user, referral_code)
#             else:
#                 return Response({"error": "Invalid role."}, status=status.HTTP_400_BAD_REQUEST)
#
#             if role == "agency":
#                 agency = user.user_agency
#                 assigned_rewards = self.check_rewards(agency)
#                 if assigned_rewards:
#                     result["rewards"] = assigned_rewards
#
#             return Response(result, status=status.HTTP_201_CREATED)
#         except ValidationError as e:
#             return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)


class SoftwarePolicyAPIView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            policy = SoftwarePolicy.objects.filter(is_enabled=True).last()
            if not policy:
                return Response({"detail": "No active software policy found."}, status=status.HTTP_404_NOT_FOUND)
            filter_type = request.query_params.get('filter', '').lower()

            if filter_type == 'terms_and_conditions':
                return Response({"terms_and_conditions": policy.terms_and_conditions}, status=status.HTTP_200_OK)
            elif filter_type == 'privacy_policy':
                return Response({"privacy_policy": policy.privacy_policy}, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"detail": "Invalid filter. Use 'terms_and_conditions' or 'privacy_policy'."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class FAQAPIView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            faqs = FAQ.objects.filter(is_enabled=True)
            serializer = FAQSerializer(faqs, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DeleteUser(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            user_data = User.objects.filter(username=request.user.username, is_active=True).last()

            if not user_data:
                return Response({"error": "This user does not exist"}, status=status.HTTP_400_BAD_REQUEST)

            user_data.is_active = False
            user_data.save()
            profile = request.user.profile
            profile.status = 'inactive'
            profile.save()

            return Response(
                {"message": "User account deactivated successfully."},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)