from import_export import resources

from p2pmb.models import MLMTree


class MLMTreeResource(resources.ModelResource):
    class Meta:
        model = MLMTree
        import_id_fields = ('id',)
        exclude = ('date_created', 'updated_by', 'date_updated', 'created_by')