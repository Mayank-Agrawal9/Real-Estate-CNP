from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from accounts.admin import CustomModelAdminMixin
from p2pmb.models import MLMTree
from p2pmb.resources import MLMTreeResource


# Register your models here.
@admin.register(MLMTree)
class MLMTreeAdmin(CustomModelAdminMixin, ImportExportModelAdmin):
    resource_class = MLMTreeResource
    raw_id_fields = ('created_by', 'updated_by', 'parent', 'child', 'referral_by')
    list_filter = ('status', )