from import_export import resources

from master.models import Country, State, City, BannerImage, GST, RewardMaster


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