import logging

from agency.calculation import distribute_monthly_rent_for_super_agency, distribute_monthly_rent_for_agency, \
    process_monthly_rentals_for_ppd_interest, calculate_super_agency_rewards, calculate_agency_rewards, calculate_field_agent_rewards
from p2pmb.calculation import calculate_lifetime_reward_income_task, process_monthly_reward_payments, \
    check_royalty_club_membership


def monthly_task():
    distribute_monthly_rent_for_super_agency()  # Office Setup and Rent For Super Agency
    distribute_monthly_rent_for_agency()  # Office Setup and Rent For Agency
    calculate_super_agency_rewards()  # Get Rewards as per agency and field agent turnover
    calculate_agency_rewards()  # Get Rewards field agent turnover
    calculate_field_agent_rewards()     # Get Rewards for own turnover


def daily_task():
    process_monthly_rentals_for_ppd_interest()  # Run Daily for get interest once in a month
    calculate_lifetime_reward_income_task()     #todo: Need to test this
    process_monthly_reward_payments()       #todo: Need to test this
    check_royalty_club_membership()         #todo: Need to test this