TRANSACTION_TYPE_CHOICES = [
    ('investment', 'Investment'),
    ('deposit', 'Deposit'),
    ('withdraw', 'Withdraw'),
    ('send', 'Send'),
    ('receive', 'Receive'),
    ('transfer', 'Transfer'),
    ('reward', 'Reward'),
    ('commission', 'Commission'),
    ('refund', 'Refund'),
    ('rent', 'Rent'),
    ('interest', 'Interest')
]

TRANSACTION_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
]

PAYMENT_METHOD = [
    ('neft', 'NEFT'),
    ('rtgs', 'RTGS'),
    ('upi', 'UPI'),
    ('cards', 'Cards'),
    ('imps', 'IMPS'),
    ('wallet', 'Wallet'),
    ('bank_transfer', 'Bank transfer'),
    ('cheque', 'Cheque'),
]