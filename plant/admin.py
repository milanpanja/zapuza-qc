from django.contrib import admin
from .models import Site, Machine, Part, Gauge, MachinePMCheck

admin.site.register([Site, Part, MachinePMCheck])
@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin): list_display = ("code", "name", "site")
@admin.register(Gauge)
class GaugeAdmin(admin.ModelAdmin): list_display = ("serial", "description", "calibration_expiry")
