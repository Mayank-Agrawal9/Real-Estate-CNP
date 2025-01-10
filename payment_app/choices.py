TRANSACTION_TYPE_CHOICES = [
    ('investment', 'Investment'),
    ('deposit', 'Deposit'),
    ('withdraw', 'Withdraw'),
    ('send', 'Send'),
    ('transfer', 'Transfer'),
    ('reward', 'Reward'),
    ('commission', 'Commission'),
    ('refund', 'Refund'),
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
    ('wallet', 'Wallet'),
    ('bank_transfer', 'Bank transfer'),
    ('cheque', 'Cheque'),
]