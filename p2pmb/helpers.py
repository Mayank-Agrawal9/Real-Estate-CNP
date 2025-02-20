import datetime

from p2pmb.models import Commission
from payment_app.models import Transaction


def create_commission_entry(commission_to, commission_by, commission_type, amount, description):
    Commission.objects.create(
        created_by=commission_to,
        commission_by=commission_by,
        commission_to=commission_to,
        commission_type=commission_type,
        amount=amount,
        description=description
    )


def create_transaction_entry(sender, receiver, amount, transaction_type, transaction_status, remarks):
    Transaction.objects.create(
        created_by=sender,
        sender=sender,
        receiver=receiver,
        amount=amount,
        transaction_type=transaction_type,
        transaction_status=transaction_status,
        payment_method='wallet',
        remarks=remarks,
        verified_on=datetime.datetime.now()
    )