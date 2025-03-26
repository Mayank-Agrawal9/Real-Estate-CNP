from import_export import resources

from p2pmb.models import MLMTree, Package, ScheduledCommission, RoyaltyClub, P2PMBRoyaltyMaster, ExtraReward


class MLMTreeResource(resources.ModelResource):
    class Meta:
        model = MLMTree
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')


class PackageResource(resources.ModelResource):
    class Meta:
        model = Package
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')


class ScheduledCommissionResource(resources.ModelResource):
    class Meta:
        model = ScheduledCommission
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')


class RoyaltyClubResource(resources.ModelResource):
    class Meta:
        model = RoyaltyClub
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')


class RewardResource(resources.ModelResource):
    class Meta:
        model = RoyaltyClub
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')


class CommissionResource(resources.ModelResource):
    class Meta:
        model = RoyaltyClub
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')


class P2PMBRoyaltyMasterResource(resources.ModelResource):
    class Meta:
        model = P2PMBRoyaltyMaster
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')


class ExtraRewardResource(resources.ModelResource):
    class Meta:
        model = ExtraReward
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')


class CoreIncomeEarnedResource(resources.ModelResource):
    class Meta:
        model = ExtraReward
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')