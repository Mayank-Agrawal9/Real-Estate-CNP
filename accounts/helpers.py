import random
import string

from rest_framework.exceptions import ValidationError

from accounts.models import Profile, BankDetails, UserPersonalDocument
from agency.models import SuperAgency


def generate_unique_referral_code():
    prefix = "CNP"
    code_length = 7

    while True:
        unique_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=code_length))
        referral_code = prefix + unique_code
        if not Profile.objects.filter(referral_code=referral_code).exists():
            return referral_code


def update_super_agency_profile(user, data, role):
    profile = update_profile(user, data["basic_details"], role)
    update_super_agency(user, profile, data["company_details"])
    update_bank_details(user, data["bank_details"])
    update_user_documents(user, data.get("documents_for_kyc", []))


def update_profile(user, basic_details, role):
    profile = Profile.objects.filter(user=user).first()
    if not profile:
        raise ValidationError("Profile not found for the user.")

    profile.father_name = basic_details["father_name"]
    profile.mobile_number = basic_details["mobile_number"]
    profile.pan_number = basic_details["pan_number"]
    profile.aadhar_number = basic_details["aadhar_number"]
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
