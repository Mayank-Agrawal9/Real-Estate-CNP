import django_filters
from .models import Property


class PropertyFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr='lte')
    category = django_filters.NumberFilter(field_name="category__id")
    city = django_filters.NumberFilter(field_name="city__id")
    state = django_filters.NumberFilter(field_name="state__id")
    country = django_filters.NumberFilter(field_name="country__id")
    property_type = django_filters.CharFilter(field_name="property_type", lookup_expr='iexact')

    class Meta:
        model = Property
        fields = ['category', 'city', 'state', 'country', 'property_type']