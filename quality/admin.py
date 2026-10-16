from django.contrib import admin
from .models import (Concession, Inspection, InspectionTemplate, Measurement, MRBDisposition, TemplateField, DefectPhoto)


class FieldInline(admin.TabularInline):
    model = TemplateField
    extra = 1
    def _open(self, obj): return not (obj and obj.is_released)
    def has_add_permission(self, request, obj=None): return self._open(obj)
    def has_change_permission(self, request, obj=None): return self._open(obj)
    def has_delete_permission(self, request, obj=None): return self._open(obj)


@admin.register(InspectionTemplate)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ("part", "revision", "is_released", "approved_by")
    readonly_fields = ("is_released", "released_at", "approved_by")
    inlines = [FieldInline]
    def has_change_permission(self, request, obj=None): return not (obj and obj.is_released)
    def has_delete_permission(self, request, obj=None): return not (obj and obj.is_released)


class ReadOnly(admin.ModelAdmin):
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

admin.site.register(Inspection, ReadOnly)
admin.site.register(Measurement, ReadOnly)
admin.site.register([Concession, MRBDisposition, DefectPhoto])
