from import_export import resources

from master.models import Country, State, City, BannerImage, GST, RewardMaster, CompanyBankDetailsMaster, RoyaltyMaster, \
    CoreGroupIncome, CoreGroupPhase


class CountryResource(resources.ModelResource):
    class Meta:
        model = Country
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')


class StateResource(resources.ModelResource):
    class Meta:
        model = State
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')


class CityResource(resources.ModelResource):
    class Meta:
        model = City
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')


class BannerImageResource(resources.ModelResource):
    class Meta:
        model = BannerImage
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')


class GSTResource(resources.ModelResource):
    class Meta:
        model = GST
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')


class RewardMasterResource(resources.ModelResource):
    class Meta:
        model = RewardMaster
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')


class CompanyBankDetailsMasterResource(resources.ModelResource):
    class Meta:
        model = CompanyBankDetailsMaster
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')


class RoyaltyMasterResource(resources.ModelResource):
    class Meta:
        model = RoyaltyMaster
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')


class CoreGroupPhaseResource(resources.ModelResource):
    class Meta:
        model = CoreGroupPhase
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')


class CoreGroupIncomeResource(resources.ModelResource):
    class Meta:
        model = CoreGroupIncome
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')