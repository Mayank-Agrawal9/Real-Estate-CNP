COMPANY_TYPE = [
    ('private_company', 'Private Company'),
    ('one_person_company', 'One Person Company'),
    ('public_company', 'Public Company'),
    ('llp', 'LLP'),
    ('enterprise', 'Enterprise')
]

REFUND_CHOICES = [
    ('1_month', 'Refund within 1 month'),
    ('3_month', 'Refund within 3 months'),
    ('6_month', 'Refund within 6 months'),
    ('1_year', 'Refund within 1 year'),
    ('no_refund', 'No Refund after 1 year'),
]


REFUND_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected')
]


INVESTMENT_TYPE_CHOICES = [
    ('super_agency', 'Super Agency'),
    ('agency', 'Agency'),
    ('field_agent', 'Field Agent'),
    ('customer', 'Customer'),
    ('p2pmb', 'Person 2 Person'),
]


PAYMENT_CHOICES = [
    ('new', 'New'),
    ('main_wallet', 'Main Wallet'),
    ('app_wallet', 'App Wallet')
]

INVESTMENT_GUARANTEED_TYPE = [
    ('guaranteed_investment', 'Guaranteed Investment'),
    ('non_guaranteed_investment', 'Non Guaranteed Investment'),
]


REWARD_CHOICES = [
    ('android_mobile', 'Android Mobile'),
    ('goa_tour', 'Goa Tour'),
    ('bangkok_tour', 'Bangkok Tour'),
    ('dubai_tour', 'Dubai Tour'),
    ('bullet_bike', 'Bullet Bike'),
    ('car_fund', 'Car Fund'),
    ('foreign_trip', 'Foreign Trip'),
    ('fully_paid_vacation', 'Fully Paid Vacation'),
    ('studio_flat', 'Studio Flat'),
    ('car_fund_full_paid', 'Car Fund (Full Paid)'),
    ('villa', 'Villa'),
    ('helicopter', 'Helicopter'),
    ('yacht', 'Yacht'),
]