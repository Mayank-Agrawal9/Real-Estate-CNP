from import_export import resources

from property.models import Property, Media, PropertyEnquiry, PropertyBooking, PropertyBookmark, PropertyFeature, \
    NearbyFacility, PropertyReview, Feature, PropertyCategory

EXCLUDE_FOR_API = ('updated_by', 'date_updated', 'created_by')


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


class PropertyEnquiryResource(resources.ModelResource):
    class Meta:
        model = PropertyEnquiry
        import_id_fields = ('id',)
        exclude = EXCLUDE_FOR_API


class BookingResource(resources.ModelResource):
    class Meta:
        model = PropertyBooking
        import_id_fields = ('id',)
        exclude = EXCLUDE_FOR_API


class PropertyBookmarkResource(resources.ModelResource):
    class Meta:
        model = PropertyBookmark
        import_id_fields = ('id',)
        exclude = EXCLUDE_FOR_API


class PropertyFeatureResource(resources.ModelResource):
    class Meta:
        model = PropertyFeature
        import_id_fields = ('id',)
        exclude = EXCLUDE_FOR_API


class PropertyCategoryResource(resources.ModelResource):
    class Meta:
        model = PropertyCategory
        import_id_fields = ('id',)
        exclude = EXCLUDE_FOR_API


class NearbyFacilityResource(resources.ModelResource):
    class Meta:
        model = NearbyFacility
        import_id_fields = ('id',)
        exclude = EXCLUDE_FOR_API


class PropertyReviewResource(resources.ModelResource):
    class Meta:
        model = PropertyReview
        import_id_fields = ('id',)
        exclude = EXCLUDE_FOR_API


class FeatureResource(resources.ModelResource):
    class Meta:
        model = Feature
        import_id_fields = ('id',)
        exclude = EXCLUDE_FOR_API