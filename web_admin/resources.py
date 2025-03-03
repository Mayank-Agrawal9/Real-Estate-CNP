from import_export import resources
from accounts.resources import EXCLUDE_FOR_API
from web_admin.models import ManualFund


class ManualFundResource(resources.ModelResource):
    class Meta:
        model = ManualFund
        import_id_fields = ('id',)
        exclude = EXCLUDE_FOR_API