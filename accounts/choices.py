STATUS_CHOICES = (
    ('active', 'Active'),
    ('inactive', 'Inactive'),
    ('blocked', 'Blocked')
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
    ('enterprise', 'Enterprise')
)

USER_ROLE = (
    ('customer', 'Customer'),
    ('field_agent', 'Field Agent'),
    ('agent', 'Agent'),
    ('super_agency', 'Super Agency'),
    ('p2pmb', 'Person to Person'),
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
)