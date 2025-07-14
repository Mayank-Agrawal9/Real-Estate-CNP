import datetime
import json
import requests
from real_estate import settings


def add_cashfree_beneficiary(bank_detail):
    headers = {
        "X-Client-Id": settings.PAYOUT_CLIENT_ID,
        "X-Client-Secret": settings.PAYOUT_SECRET_ID,
        "Content-Type": "application/json",
        'x-api-version': '2024-01-01',
    }

    payload = {
        "beneficiary_id": f"user_{bank_detail.user.id}",
        "beneficiary_name": bank_detail.user.get_full_name(),
        "beneficiary_instrument_details": {
            "bank_account_number": '026291800001191',
            "bank_ifsc": 'YESB0000262',
            # "vpa": bank_detail.upi_id if hasattr(bank_detail, 'upi_id') else None
        },
        "beneficiary_contact_details": {
            "beneficiary_email": bank_detail.user.email,
            "beneficiary_phone": bank_detail.user.profile.mobile_number or 1234567891,
            "beneficiary_country_code": "+91",
            "beneficiary_address": "User Address",
            "beneficiary_city": "City",
            "beneficiary_state": "State",
            "beneficiary_postal_code": "123456"
        }
    }

    payload = json.dumps(payload, separators=(',', ':'), sort_keys=True)

    response = requests.post(
        "https://sandbox.cashfree.com/payout/beneficiary",
        headers=headers, data=payload
    )
    if response.status_code == 200 and response.json().get("status") == "SUCCESS":
        bank_detail.beneficiary_id = payload['beneId']
        bank_detail.save()
        return False, payload['beneId']
    else:
        return True, response.json()


def send_cashfree_payout(beneficiary_id, amount, withdraw_id, transfer_mode="banktransfer", remarks="Withdrawal Payout"):
    """
    Send payout via Cashfree using bank transfer.

    Parameters:
        user: User object with cashfree_bene_id
        amount: Amount to transfer (float or Decimal)
        withdraw_id: Unique ID from FundWithdrawal
        transfer_mode: Transfer mode (default is 'banktransfer')
        remarks: Transfer remarks

    Returns:
        dict: {
            "success": bool,
            "data": response_json,
            "transfer_id": str
        }
    """
    headers = {
        "X-Client-Id": settings.CASHFREE_APP_ID,
        "X-Client-Secret": settings.CASHFREE_SECRET_KEY,
        "X-api-version": '2024-01-01',
        "Content-Type": "application/json"
    }

    transfer_id = f"TXN{withdraw_id}{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

    payload = {
        "beneId": beneficiary_id,
        "amount": str(amount),
        "transferId": transfer_id,
        "transferMode": transfer_mode,
        "remarks": remarks
    }

    try:
        response = requests.post(
            'https://payout-api.cashfree.com/payout/v1/requestTransfer',
            headers=headers, json=payload
        )
        response_data = response.json()
        return {
            "success": response.status_code == 200 and response_data.get("status") == "SUCCESS",
            "data": response_data,
            "transfer_id": transfer_id
        }
    except requests.RequestException as e:
        return {
            "success": False,
            "data": {"error": str(e)},
            "transfer_id": transfer_id
        }