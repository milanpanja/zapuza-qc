from django.contrib import admin
from .models import JobTraveler, Operation, SerialNumber, ProductionRun, ShiftHandover


class OperationInline(admin.TabularInline):
    model = Operation
    extra = 3

@admin.register(JobTraveler)
class JobTravelerAdmin(admin.ModelAdmin):
    list_display = ("work_order", "part", "raw_lot", "status")
    inlines = [OperationInline]

admin.site.register([SerialNumber, ProductionRun, ShiftHandover])
