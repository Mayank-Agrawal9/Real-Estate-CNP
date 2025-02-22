from decimal import Decimal

from django.db.models import F

DIRECT_INCOME_PERCENT = Decimal('4.50')
LEVEL_INCOME_PERCENT = Decimal('4.50')
LIFETIME_REWARD_PERCENT = Decimal('2.00')
ROYALTY_TURNOVER_PERCENT = Decimal('1.00')
MAX_LEVELS_ABOVE = 20
MAX_LEVELS_BELOW = 10
WITHDRAWAL_DEDUCTION_BEFORE_3_YEARS = Decimal('0.30')
WITHDRAWAL_DEDUCTION_BEFORE_6_YEARS = Decimal('0.20')
REFERRAL_MULTIPLIER_5_REFERRALS = Decimal('1.5')
REFERRAL_MULTIPLIER_10_REFERRALS = Decimal('2.0')
REFERRAL_MULTIPLIER_10_REFERRALS_AND_5_TEAM = Decimal('5.0')
ACCOUNT_WITHDRAWAL_CHARGE = Decimal('0.10')
P2P_WITHDRAWAL_CHARGE = Decimal('0.05')
TDS_PERCENT = Decimal('0.05')
TURNOVER_LEG_1 = Decimal('0.40')
TURNOVER_LEG_2 = Decimal('0.30')
TURNOVER_LEG_3 = Decimal('0.20')
TURNOVER_LEG_4 = Decimal('0.10')

TURNOVER_DISTRIBUTION = [40, 30, 20, 10]

royalty_levels = [
    {"club": "star", "direct": 10, "level1": 0, "level2": 0,
        "turnover": F('turnover'), "gift": 1000000,
    },
    {
        "club": "2_star", "direct": 10, "level1": 5, "level2": 25,
        "turnover": 2500000, "gift": 2500000,
    },
    {
        "club": "3_star",
        "direct": 10,
        "level1": 25,
        "level2": 125,
        "turnover": 5000000,
        "gift": 5000000,
    },
    {
        "club": "5_star",
        "direct": 10,
        "level1": 100,
        "level2": 500,
        "turnover": 10000000,
        "gift": 10000000,
    },
]