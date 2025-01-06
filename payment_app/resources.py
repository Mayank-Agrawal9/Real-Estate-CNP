from import_export import resources
from payment_app.models import *

EXCLUDE_FOR_API = ('date_created', 'updated_by', 'date_updated', 'created_by')


class WalletResource(resources.ModelResource):
    class Meta:
        model = UserWallet
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by', 'picture')


class TransactionResource(resources.ModelResource):
    class Meta:
        model = Transaction
        import_id_fields = ('id',)
        exclude = EXCLUDE_FOR_API