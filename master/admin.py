from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from accounts.admin import CustomModelAdminMixin
from agency.resources import RewardEarnedResource
from master.models import Country, State, GST, BannerImage, City
from master.resources import CountryResource, StateResource, CityResource, BannerImageResource, GSTResource


# Register your models here.


@admin.register(Country)
class CountryAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = CountryResource
    raw_id_fields = ('created_by', 'updated_by')
    list_filter = ('status', )


@admin.register(State)
class StateAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = StateResource
    raw_id_fields = ('created_by', 'updated_by', 'country')
    list_filter = ('status', )


@admin.register(City)
class CityAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = CityResource
    raw_id_fields = ('created_by', 'updated_by', 'state')
    list_filter = ('status', )


@admin.register(BannerImage)
class BannerImageAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = BannerImageResource
    raw_id_fields = ('created_by', 'updated_by')
    list_filter = ('status', )


@admin.register(GST)
class GSTAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = GSTResource
    raw_id_fields = ('created_by', 'updated_by')
    list_filter = ('status', )