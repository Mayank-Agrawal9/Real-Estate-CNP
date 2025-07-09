STATUS_CHOICES = (
    ('active', 'Active'),
    ('inactive', 'Inactive'),
    ('blocked', 'Blocked')
)

OTP_TYPE = (
    ('register', 'Register'),
    ('login', 'Login'),
    ('forgot', 'Forgot'),
    ('delete', 'Delete'),
    ('resend', 'Resend'),
)

GENDER_CHOICE = (
    ('Male', 'Male'),
    ('Female', 'Female'),
    ('transgender', 'Transgender'),
    ('other', 'Other'),
)

COMPANY_TYPE = (
    ('private_company', 'Private Company'),
    ('one_person_company', 'One Person Company'),
    ('public_company', 'Public Company'),
    ('llp', 'LLP'),
    ('ngo', 'NGO'),
    ('enterprise', 'Enterprise')
)

USER_ROLE = (
    ('customer', 'Customer'),
    ('field_agent', 'Field Agent'),
    ('agency', 'Agency'),
    ('super_agency', 'Super Agency'),
    ('p2pmb', 'Person to Person'),
)

ADMIN_ROLE = (
    ('kyc', 'KYC'),
    ('god', 'GOD'),
    ('vendor_listing', 'Vendor Listing'),
    ('accounting', 'Accounting')
)

DOCUMENT_TYPE = (
    ('pan_card', 'Pan Card'),
    ('aadhar_front', 'Aadhar Card Front'),
    ('aadhar_back', 'Aadhar Card Back'),
    ('passbook', 'Passbook'),
    ('cancelled_cheque', 'Cancelled Cheque'),
    ('company_registration', 'Company Registration'),
    ('shop_image', 'Shop Image'),
    ('shop_agreement', 'Shop Agreement'),
    ('kyc_photo', 'KYC Photo'),
)


CHANGE_REQUEST_CHOICE = (
    ('pending', 'Pending'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
)