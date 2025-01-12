import random
import string
from io import BytesIO

import qrcode
from django.core.files.base import ContentFile
from rest_framework.exceptions import ValidationError

from accounts.models import Profile, BankDetails, UserPersonalDocument
from agency.models import SuperAgency, Agency, FieldAgent


def generate_unique_referral_code():
    prefix = "CNP"
    code_length = 7

    while True:
        unique_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=code_length))
        referral_code = prefix + unique_code
        if not Profile.objects.filter(referral_code=referral_code).exists():
            return referral_code


def generate_qr_code_with_email(email):
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
    return ContentFile(buffer.read(), name=f"{email}_qr_code.png")


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
        super_agency = SuperAgency.objects.filter(profile=referral_by).last()
        if not super_agency:
            raise ValidationError("Referral code should be your upper-level user.")
        return super_agency, referral_by

    elif referral_by.role == 'agency':
        agency_ = Agency.objects.filter(created_by=referral_by.user).last()
        if not agency_:
            raise ValidationError("Referral code should be your upper-level user.")
        return agency_, referral_by

    else:
        raise ValidationError(f"You cannot use the referral code of {referral_by.role}.")


def update_profile(user, basic_details, role, referral_by=None):
    profile = Profile.objects.filter(user=user).first()
    if not profile:
        raise ValidationError("Profile not found for the user.")

    profile.father_name = basic_details["father_name"]
    profile.mobile_number = basic_details["mobile_number"]
    profile.pan_number = basic_details["pan_number"]
    profile.aadhar_number = basic_details["aadhar_number"]
    profile.referral_by = referral_by.user
    profile.role = role
    profile.is_kyc = True
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
            "email": company_details["email"],
            "office_address": company_details.get("office_address"),
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
            "email": company_details["email"],
            "office_address": company_details.get("office_address"),
            "company": id,
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
