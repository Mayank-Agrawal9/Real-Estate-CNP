from import_export import resources

from agency.models import *


class SuperAgencyResource(resources.ModelResource):
    class Meta:
        model = SuperAgency
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')


class AgencyResource(resources.ModelResource):
    class Meta:
        model = Agency
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')


class FieldAgentResource(resources.ModelResource):
    class Meta:
        model = FieldAgent
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')


class InvestmentResource(resources.ModelResource):
    class Meta:
        model = Investment
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')


class CommissionResource(resources.ModelResource):
    class Meta:
        model = Commission
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')


class RefundPolicyResource(resources.ModelResource):
    class Meta:
        model = RefundPolicy
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')


class PPDModelResource(resources.ModelResource):
    class Meta:
        model = PPDAccount
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')


class FundWithdrawalResource(resources.ModelResource):
    class Meta:
        model = FundWithdrawal
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')


class RewardEarnedResource(resources.ModelResource):
    class Meta:
        model = RewardEarned
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')


class InvestmentInterestResource(resources.ModelResource):
    class Meta:
        model = InvestmentInterest
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')


class AgencyPackagePurchaseResource(resources.ModelResource):
    class Meta:
        model = AgencyPackagePurchase
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')