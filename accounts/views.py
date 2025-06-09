import datetime
import random
import string
from decimal import Decimal
import requests

from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets, parsers
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.helpers import generate_unique_referral_code, update_super_agency_profile, generate_qr_code_with_email, \
    update_agency_profile, update_field_agent_profile, update_p2pmb_profile, generate_unique_image_code, \
    generate_otp_and_send_email
from accounts.models import OTP, Profile, BankDetails, UserPersonalDocument, SoftwarePolicy, FAQ, ChangeRequest
from accounts.serializers import (RequestOTPSerializer, VerifyOTPSerializer, ResendOTPSerializer, ProfileSerializer,
                                  SuperAgencyKycSerializer, BasicDetailsSerializer, CompanyDetailsSerializer,
                                  BankDetailsSerializer, FAQSerializer,
                                  ChangeRequestSerializer, UserPersonalDocumentSerializer, UpdateUserProfileSerializer,
                                  BankDetailsSerializerV2, LoginSerializer, OTPSerializer, UserRegistrationSerializer)
from agency.models import SuperAgency, FieldAgent, Agency, Investment
from p2pmb.models import MLMTree
from payment_app.models import UserWallet, Transaction
from real_estate import settings


# Create your views here.

class RequestOTPView(APIView):
    def post(self, request):
        serializer = RequestOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email'].lower()
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


class RegisterUserView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Registration successful. OTP sent to email."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token, _ = Token.objects.get_or_create(user=serializer.validated_data['user'])
        profile = serializer.validated_data['user'].profile
        if not profile:
            return Response({'message': 'User Does Not have profile, Please connect to support team'},
                            status=status.HTTP_400_BAD_REQUEST)
        # push_data = DeviceInfo.objects.filter(created_by=serializer.validated_data['user']).last()
        # if push_data:
        #     push_data.device_uid = self.request.data['device_uid']
        #     push_data.device_model_name = self.request.data['device_model_name']
        #     push_data.device_os = self.request.data['device_os']
        #     push_data.device_version = self.request.data['device_version']
        #     push_data.device_token = self.request.data['device_token']
        #     push_data.updated_by = serializer.validated_data['user']
        #     push_data.save()
        # else:
        #     DeviceInfo.objects.create(created_by=serializer.validated_data['user'],
        #                               device_uid=self.request.data['device_uid'],
        #                               device_model_name=self.request.data['device_model_name'],
        #                               device_os=self.request.data['device_os'],
        #                               device_version=self.request.data['device_version'],
        #                               device_token=self.request.data['device_token'])
        res = {
            "message": "Login successful.",
            'key': token.key,
            'basic': {
                'name': profile.full_name,
                'email': profile.user.email,
                'profile_id': profile.id,
                'user_id': profile.user.id,
                'picture': profile.picture.url if profile and profile.picture else None,
                "role": profile.role,
                "referral_code": profile.referral_code,
                "qr_code_url": profile.qr_code.url if profile.qr_code else None,
                "is_vendor": profile.is_vendor if profile and profile.is_vendor else None,
                "is_super_agency": profile.is_super_agency if profile and profile.is_super_agency else None,
                "is_agency": profile.is_agency if profile and profile.is_agency else None,
                "is_field_agent": profile.is_field_agent if profile and profile.is_field_agent else None,
                "is_p2pmb": profile.is_p2pmb if profile and profile.is_p2pmb else None,
            }
        }
        return Response(res)


class VerifyOptAPI(APIView):
    '''This API is used to verify OPT'''
    permission_classes = (AllowAny,)

    def put(self, request):
        username = request.data.get('username')
        otp_value = int(request.data.get('otp'))
        otp_type = request.data.get('type')

        if not username or not otp_value or not otp_type:
            return Response({'message': 'Incomplete request data.'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(Q(username=username) | Q(email=username), is_active=True).last()

        if not user:
            return Response({'message': 'There is no user registered with this username.'},
                            status=status.HTTP_400_BAD_REQUEST)

        query_otp = OTP.objects.filter(created_by=user, type=otp_type).last()
        if not query_otp:
            return Response({'message': 'Please send OTP first.'}, status=status.HTTP_400_BAD_REQUEST)

        if otp_value != query_otp.otp:
            return Response({'message': 'The OTP you entered is not valid.'}, status=status.HTTP_400_BAD_REQUEST)

        query_data = {'is_verify': 'true'}
        query_update = OTPSerializer(query_otp, data=query_data, partial=True)
        if query_update.is_valid():
            query_update.save()
            return Response({'message': 'You have successfully verified the OTP.'}, status=status.HTTP_200_OK)
        return Response({'message': query_update.errors}, status=status.HTTP_400_BAD_REQUEST)


class OptResendAPIView(APIView):
    """This API is used to resend the OPT once user is registered."""
    permission_classes = (AllowAny,)

    def post(self, request):
        if not request.data or 'username' not in request.data:
            return Response({'status': False, 'message': 'Need to pass username.'},
                            status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(Q(username=request.data['username']) | Q(email=request.data['username'])).last()
        if not user:
            return Response({'status': False, 'message': 'There is no user register with this email.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not user.email:
            return Response({'status': False, 'message': 'This user has not having email, '
                                                         'First update email for receiving OTP.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if request.data.get('type'):
            generate_otp_and_send_email(email=user.email, user=user, type=request.data.get('type'))
        else:
            generate_otp_and_send_email(email=user.email, user=user, type="register")
        return Response({'status': True, 'message': 'We send mail, Please verify once.'},
                        status=status.HTTP_200_OK)


class ForgotPasswordChangeAPI(APIView):
    '''When user is register then it will be able to change the password.'''
    permission_classes = (AllowAny,)

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        confirm_password = request.data.get("confirm_password")
        type = request.data.get("type")
        if not password and confirm_password and username:
            return Response({'error': 'Password and confirm password and username should be mandatory.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if password != confirm_password:
            return Response({'error': 'Invalid Password! Password does not match.'},
                            status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(Q(username=username) | Q(email=username)).last()
        if not user:
            return Response({'status': False, 'message': 'There is no user register with this email.'},
                            status=status.HTTP_400_BAD_REQUEST)
        verify_otp = OTP.objects.filter(created_by=user, verify='true', type=type).last()
        if not verify_otp:
            return Response({'status': False, 'message': 'First You need to verify OTP.'},
                            status=status.HTTP_400_BAD_REQUEST)
        user.set_password(password)
        user.save()
        return Response({'status': True, 'message': 'Password changed successfully! '}, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email'].lower()
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
            image_code = generate_unique_image_code()
            qr_code_file = generate_qr_code_with_email(email, user.id)

            profile, created = Profile.objects.get_or_create(user=user, defaults={
                "created_by": user,
                "referral_code": referral_code,
                "qr_code": qr_code_file,
                "image_code": image_code,
            })

            if not created:
                profile.qr_code = qr_code_file
                profile.save()

            UserWallet.objects.get_or_create(user=user, created_by=user)
            token, _ = Token.objects.get_or_create(user=user)

            return Response({
                "message": "Login successful.",
                "token": token.key,
                "user_id": user.id,
                "picture": profile.picture.url if profile and profile.picture else None,
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
            email = serializer.validated_data['email'].lower()
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
        documents = UserPersonalDocumentSerializer(
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
                elif role == "p2pmb":
                    update_p2pmb_profile(user, data, "p2pmb")
                return Response({"message": "Data updated successfully!"}, status=status.HTTP_200_OK)

        except ValidationError as e:
            error_message = e.detail if isinstance(e.detail, str) else e.detail[0]
            return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "Something went wrong", "details": str(e)},
                            status=status.HTTP_400_BAD_REQUEST)


class UpdateUserBasicDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        try:
            profile = Profile.objects.filter(user=request.user).last()

            if not profile:
                return Response(
                    {"message": "You are not mapped with profile, Please contact with admin."},
                    status=status.HTTP_404_NOT_FOUND
                )

            serializer = UpdateUserProfileSerializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": "Something went wrong", "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def post(self, request):
        try:
            profile = Profile.objects.filter(user=request.user).last()

            if not profile:
                return Response(
                    {"message": "You are not mapped with profile, Please contact with admin."},
                    status=status.HTTP_200_OK
                )

            full_name = request.data.get("full_name")
            if full_name:
                parts = full_name.strip().split(" ", 1)
                request.user.first_name = parts[0]
                request.user.last_name = parts[1] if len(parts) > 1 else ""
                request.user.save()

            serializer = UpdateUserProfileSerializer(profile, data=request.data, partial=True)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            serializer.save()
            return Response({"message": "Basic Detail updated successfully!"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": "Something went wrong", "details": str(e)},
                            status=status.HTTP_400_BAD_REQUEST)


class UserCompanyDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            pass
        except Exception as e:
            return Response({"error": "Something went wrong", "details": str(e)},
                            status=status.HTTP_400_BAD_REQUEST)


class UserDocumentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            pass
        except Exception as e:
            return Response({"error": "Something went wrong", "details": str(e)},
                            status=status.HTTP_400_BAD_REQUEST)


class VerifyAndUpdateProfile(APIView):
    permission_classes = [IsAuthenticated]

    def update_wallet_and_transaction_(self, user, verify_by, amount, remarks, commission_amount, is_not_super_agency=False):
        wallet, _ = UserWallet.objects.get_or_create(user=user)
        wallet.main_wallet_balance += amount
        if is_not_super_agency:
            wallet.in_app_wallet += commission_amount
            Transaction.objects.create(
                created_by=user,
                sender=user,
                amount=commission_amount,
                transaction_type='commission',
                transaction_status='approved',
                verified_by=verify_by,
                verified_on=datetime.datetime.now(),
                remarks=remarks,
                payment_method='wallet'
            )
        wallet.save()

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

                if profile.role == 'super_agency':
                    super_agency = SuperAgency.objects.filter(profile=profile).last()
                    if super_agency:
                        self.update_wallet_and_transaction_(
                            super_agency.company.profile.user,
                            request.user,
                            investment_instance.transaction_id.amount,
                            'Commission added due to agency added.',
                            0,
                            is_not_super_agency=True
                        )
                elif profile.role == 'agency':
                    agency = Agency.objects.filter(created_by=profile.user).last()
                    if agency and agency.company:
                        commission = Decimal(str(investment_instance.transaction_id.amount * 0.25))
                        self.update_wallet_and_transaction_(
                            agency.company.profile.user,
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
                # elif profile.role == 'p2pmb':

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

        profile = Profile.objects.filter(referral_code=friend_referral_code).first()
        #
        # if not profile:
        #     return Response({'status_code': 400, 'message': 'Invalid referral code or the user has not completed KYC.'
        #         }, status=status.HTTP_400_BAD_REQUEST)

        role_to_user_for = {
            'super_agency': 'agent',
            'agent': 'field_agent',
            'customer': 'customer'
        }
        user_for = role_to_user_for.get(profile.role, 'p2pmb')

        data = {
            'cnp_id': profile.user.username,
            'friend_role': profile.role,
            'user_for': user_for
        }
        return Response({
                'status_code': 200, 'message': 'Fetched data successfully.', 'friend_referral_data': data
            }, status=status.HTTP_200_OK)


class GetReferralCode(APIView):
    permission_classes = [IsAuthenticated]
    ROLE_MAPPING = {
        'agency': 'super_agency',
        'field_agent': 'agency'
    }

    def post(self, request, *args, **kwargs):
        city = request.data.get('city')
        role = request.data.get('role')
        mapped_role = self.ROLE_MAPPING.get(role, role)
        profile = Profile.objects.filter(city=city, is_kyc=True, is_kyc_verified=True,
                                         role=mapped_role).first()
        if profile:
            profile_dict = {
                'referral_code': profile.referral_code,
                'first_name': profile.user.first_name,
                'last_name': profile.user.last_name,
                'email': profile.user.email,
                'username': profile.user.username
            }
            return Response(profile_dict, status=status.HTTP_200_OK)
        else:
            profile = Profile.objects.filter(is_kyc=True, is_kyc_verified=True, role=mapped_role,
                                             user__is_staff=True).first()
            profile_dict = {
                'referral_code': profile.referral_code,
                'first_name': profile.user.first_name,
                'last_name': profile.user.last_name,
                'email': profile.user.email,
                'username': profile.user.username
            }
            return Response(profile_dict, status=status.HTTP_200_OK)


class GetPPDReferralCode(APIView):
    '''This API is used to get the ppd referral code.'''
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        get_user_referral = Profile.objects.filter(user=self.request.user).last()
        if get_user_referral and get_user_referral.referral_by:
            profile_dict = {
                'referral_code': get_user_referral.referral_by.profile.referral_code,
                'first_name': get_user_referral.referral_by.first_name,
                'last_name': get_user_referral.referral_by.last_name,
                'email': get_user_referral.referral_by.email,
                'username': get_user_referral.referral_by.username
            }
            return Response(profile_dict, status=status.HTTP_200_OK)
        mlm = MLMTree.objects.filter(level=12, position=1, is_show=True).last()
        if not mlm:
            profile_dict = {
                'referral_code': 'CNPPB007700',
                'first_name': 'Click N Pay',
                'last_name': 'Real Estate',
                'email': 'clicknpayrealestate@gmail.com',
                'username': 'clicknpayrealestate@gmail.com'
            }
            return Response(profile_dict, status=status.HTTP_200_OK)
        profile_dict = {
            'referral_code': mlm.child.profile.referral_code,
            'first_name': mlm.child.first_name,
            'last_name': mlm.child.last_name,
            'email': mlm.child.email,
            'username': mlm.child.username
        }
        return Response(profile_dict, status=status.HTTP_200_OK)


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


class GenerateUniqueNumber(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        profile = Profile.objects.filter(user=request.user).only('image_code').last()
        if not profile:
            return Response({'message': "You don't have profile, Please connect to admin"},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({"image_code": profile.image_code})


class GeneratePreviousUniqueCode(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        profiles = Profile.objects.filter(image_code__isnull=True)
        for profile in profiles:
            image_code = generate_unique_image_code()
            profile.image_code = image_code
            profile.save()
        return Response({"image_code": "Updated code for previous, Person."})


class ChangeRequestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ChangeRequest.objects.filter(status='active')
    serializer_class = ChangeRequestSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['phone_number', 'email', 'verified_by']

    def get_queryset(self):
        return ChangeRequest.objects.filter(created_by=self.request.user, status='active')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class UserBankDetailsViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = BankDetails.objects.filter(status='active')
    serializer_class = BankDetailsSerializerV2
    pagination_class = None
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['account_number', 'user__username']

    def get_queryset(self):
        return BankDetails.objects.filter(user=self.request.user, status='active')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, user=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class UserPersonalDocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = UserPersonalDocument.objects.filter(status='active')
    serializer_class = UserPersonalDocumentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['created_by', 'type', 'approval_status']
    pagination_class = None

    def get_queryset(self):
        return UserPersonalDocument.objects.filter(created_by=self.request.user, status='active')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=False, methods=['post'], url_path='bulk-create', parser_classes=[parsers.MultiPartParser])
    def bulk_create(self, request):
        attachment = request.FILES.getlist('attachment[]')
        types = request.data.getlist('type[]')

        if len(attachment) != len(types):
            return Response({'detail': 'Number of files and types must match.'}, status=status.HTTP_400_BAD_REQUEST)

        created = []
        errors = []

        for i, (file, doc_type) in enumerate(zip(attachment, types)):
            data = {
                'attachment': file,
                'type': doc_type,
            }

            serializer = self.get_serializer(data=data)
            if serializer.is_valid():
                serializer.save(created_by=request.user)
                created.append(serializer.data)
            else:
                errors.append({f'document_{i}': serializer.errors})

        if errors:
            return Response({'created': created, 'errors': errors}, status=status.HTTP_207_MULTI_STATUS)

        return Response({'message': 'File Uploaded Successfully.'}, status=status.HTTP_201_CREATED)


class ShowUserDetail(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            referral_code = request.GET.get('referral_code')
            if not referral_code:
                return Response({'error': 'Need to pass referral code.'}, status=status.HTTP_400_BAD_REQUEST)
            check_referral = Profile.objects.filter(referral_code=referral_code).last()
            if not check_referral:
                return Response({'error': 'Invalid referral code.'}, status=status.HTTP_400_BAD_REQUEST)
            profile_dict = {
                'referral_code': check_referral.referral_code,
                'first_name': check_referral.user.first_name,
                'last_name': check_referral.user.last_name,
                'email': check_referral.user.email,
                'username': check_referral.user.username
            }
            return Response(profile_dict, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UpdateROIStatus(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, user_id):
        profile = Profile.objects.filter(user=user_id).last()
        if not profile:
            return Response({"message": "User don't having profile, Please create first profile."},
                            status=status.HTTP_200_OK)
        if profile.is_roi_send:
            profile.is_roi_send = False
            profile.save()
        else:
            profile.is_roi_send = True
            profile.save()
        return Response({"message": "ROI status updated successfully."}, status=status.HTTP_200_OK)