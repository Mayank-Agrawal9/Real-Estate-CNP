import datetime
import random
import string
from io import BytesIO

import qrcode
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from rest_framework.exceptions import ValidationError

from accounts.models import Profile, BankDetails, UserPersonalDocument, OTP
from agency.models import SuperAgency, Agency, FieldAgent
from p2pmb.models import MLMTree
from real_estate import settings


def generate_unique_referral_code():
    prefix = "CNP"
    code_length = 7

    while True:
        unique_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=code_length))
        referral_code = prefix + unique_code
        if not Profile.objects.filter(referral_code=referral_code).exists():
            return referral_code


def generate_unique_image_code():
    while True:
        image_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        if not Profile.objects.filter(image_code=image_code).exists():
            return image_code


def generate_qr_code_with_email(email, user_id):
    """
    Generates a QR code containing the user's email and returns it as an in-memory file.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(email)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return ContentFile(buffer.read(), name=f"{user_id}_qr_code.png")


def update_super_agency_profile(user, data, role):
    profile = update_profile(user, data["basic_details"], role)
    update_super_agency(user, profile, data["company_details"])
    update_bank_details(user, data["bank_details"])
    update_user_documents(user, data.get("documents_for_kyc", []))


def update_agency_profile(user, data, role):
    id, referral_by = validate_referral_code(data["basic_details"], role)
    update_profile(user, data["basic_details"], role, referral_by)
    update_agency(user, data["company_details"], id)
    update_bank_details(user, data["bank_details"])
    update_user_documents(user, data.get("documents_for_kyc", []))


def update_field_agent_profile(user, data, role):
    id, referral_by = validate_referral_code(data["basic_details"], role)
    profile = update_profile(user, data["basic_details"], role, referral_by)
    update_field_agent(user, profile, id)
    update_bank_details(user, data["bank_details"])
    update_user_documents(user, data.get("documents_for_kyc", []))


def validate_referral_code_for_p2pmb(user):
    request_user_profile = Profile.objects.filter(user=user).last()
    if not request_user_profile:
        raise ValidationError("Invalid user.")

    get_mlm_referral = MLMTree.objects.filter(child=request_user_profile.user).last()
    if not get_mlm_referral or not get_mlm_referral.referral_by:
        return None
    return request_user_profile


def update_p2pmb_profile(user, data, role):
    referral_by = validate_referral_code_for_p2pmb(user)
    update_profile(user, data["basic_details"], role, referral_by)
    update_bank_details(user, data["bank_details"])
    update_user_documents(user, data.get("documents_for_kyc", []))


def validate_referral_code(basic_details, role):
    """
    Validates the referral code and checks the hierarchy and KYC status.

    Args:
        basic_details (dict): The referral code to be validated.
        role (str): The role of the user using the referral code.

    Returns:
        Profile: The profile associated with the referral code if valid.

    Raises:
        ValidationError: If the referral code is invalid or hierarchy rules are broken.
    """
    referral_by = Profile.objects.filter(referral_code=basic_details["referral_code"]).last()
    if not referral_by:
        raise ValidationError("Invalid referral code.")

    if referral_by.role == role:
        raise ValidationError("Referral code should be your upper-level user.")

    if not (referral_by.is_kyc and referral_by.is_kyc_verified):
        raise ValidationError("Referral user has not completed their KYC.")

    if referral_by.role == 'super_agency':
        super_agency = SuperAgency.objects.filter(profile=referral_by, status='active').last()
        if not super_agency:
            raise ValidationError("Referral code should be your upper-level user.")

        return super_agency, referral_by

    elif referral_by.role == 'agency':
        agency_ = Agency.objects.filter(created_by=referral_by.user, status='active').last()
        if not agency_:
            raise ValidationError("Referral code should be your upper-level user.")
        return agency_, referral_by

    elif referral_by.role == 'field_agent':
        agent_ = FieldAgent.objects.filter(profile=referral_by, status='active').last()
        if not agent_:
            raise ValidationError("Referral code should be your upper-level user.")
        return agent_, referral_by

    elif referral_by.role == 'p2pmb':
        return

    else:
        raise ValidationError(f"You cannot use the referral code of {referral_by.role}.")


def update_profile(user, basic_details, role, referral_by=None):
    profile = Profile.objects.filter(user=user).first()
    if not profile:
        raise ValidationError("Profile not found for the user.")

    full_name = basic_details.get("full_name", "").strip()
    name_parts = full_name.split(" ", 1)
    profile.user.first_name = name_parts[0] if name_parts else ""
    profile.user.last_name = name_parts[1] if len(name_parts) > 1 else ""

    profile.pan_remarks = basic_details.get("pan_remarks", profile.pan_remarks)
    profile.kyc_video = basic_details.get("kyc_video", profile.kyc_video)
    profile.father_name = basic_details.get("father_name", profile.father_name)
    profile.mobile_number = basic_details.get("mobile_number", profile.mobile_number)
    profile.mobile_number1 = basic_details.get("mobile_number1", profile.mobile_number1)
    profile.mobile_number2 = basic_details.get("mobile_number2", profile.mobile_number2)
    profile.pan_number = basic_details.get("pan_number", profile.pan_number)
    profile.aadhar_number = basic_details.get("aadhar_number", profile.aadhar_number)
    profile.other_email = basic_details.get("other_email", profile.other_email)
    profile.voter_number = basic_details.get("voter_number", profile.voter_number)
    profile.pan_remarks = basic_details.get("pan_remarks", profile.pan_remarks)
    profile.pin_code = basic_details.get("pin_code", profile.pin_code)
    profile.city = basic_details.get("city", profile.city)
    profile.state = basic_details.get("state", profile.state)

    profile.referral_by = referral_by.user if hasattr(referral_by, "user") else None

    if role == 'super_agency':
        profile.is_super_agency = True
    elif role == 'agency':
        profile.is_agency = True
    elif role == 'field_agent':
        profile.is_field_agent = True
    elif role == 'p2pmb':
        profile.is_p2pmb = True

    profile.role = role
    profile.is_kyc = True

    profile.user.save()
    profile.save()
    return profile


def update_super_agency(user, profile, company_details):
    SuperAgency.objects.update_or_create(
        profile=profile,
        defaults={
            "created_by": user,
            "name": company_details["name"],
            "type": company_details["type"],
            "phone_number": company_details.get("phone_number"),
            "pan_number": company_details.get("pan_number"),
            "gst_number": company_details.get("gst_number"),
            "email": company_details["email"],
            "office_address": company_details.get("office_address"),
            "office_area": company_details.get("office_area")
        }
    )


def update_agency(user, company_details, id):
    Agency.objects.update_or_create(
        created_by=user,
        defaults={
            "name": company_details["name"],
            "type": company_details["type"],
            "phone_number": company_details.get("phone_number"),
            "pan_number": company_details.get("pan_number"),
            "gst_number": company_details.get("gst_number"),
            "email": company_details["email"],
            "office_address": company_details.get("office_address"),
            "office_area": company_details.get("office_area"),
            "company": id
        }
    )


def update_field_agent(user, profile, id):
    FieldAgent.objects.update_or_create(
        profile=profile,
        defaults={
            "created_by": user,
            "agency": id
        }
    )


def update_p2pmb(user, id, referral_by):
    MLMTree.objects.update_or_create(
        child=user,
        defaults={
            "created_by": user,
            "status": 'inactive',
            "agency": id,
            "referral_by": referral_by
        }
    )


def update_bank_details(user, bank_details):
    BankDetails.objects.update_or_create(
        user=user,
        defaults={
            "created_by": user,
            "account_number": bank_details["account_number"],
            "account_holder_name": bank_details["account_holder_name"],
            "ifsc_code": bank_details["ifsc_code"],
            "bank_name": bank_details["bank_name"],
            "bank_address": bank_details.get("bank_address"),
        }
    )


def update_user_documents(user, documents):
    for doc in documents:
        UserPersonalDocument.objects.update_or_create(
            created_by=user,
            attachment=doc["attachment"],
            defaults={"type": doc["type"]},
        )


def generate_otp_and_send_email(email, user, type):
    otp_code = str(random.randint(100000, 999999))
    valid_until = datetime.datetime.now() + datetime.timedelta(minutes=10)
    OTP.objects.create(otp=otp_code, valid_until=valid_until, type=type, created_by=user)
    send_mail(
        "Your OTP Code",
        f"Your OTP code is {otp_code}. It is valid for 10 minutes.",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
    return otp_code
