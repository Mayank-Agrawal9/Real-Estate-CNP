from import_export import resources

from property.models import Property, Media

EXCLUDE_FOR_API = ('date_created', 'updated_by', 'date_updated', 'created_by')


class PropertyResource(resources.ModelResource):
    class Meta:
        model = Property
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by', 'user')


class MediaResource(resources.ModelResource):
    class Meta:
        model = Media
        import_id_fields = ('id',)
        exclude = EXCLUDE_FOR_API