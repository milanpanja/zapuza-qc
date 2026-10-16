from django.conf import settings
from django.core import signing
from django.db import models
from django.utils import timezone


class Site(models.Model):
    name = models.CharField(max_length=80, unique=True)
    def __str__(self): return self.name


class Machine(models.Model):
    site = models.ForeignKey(Site, on_delete=models.PROTECT)
    code = models.CharField(max_length=30, unique=True)          # e.g. CNC-04
    name = models.CharField(max_length=80, blank=True)
    def __str__(self): return self.code

    @property
    def qr_payload(self):
        """Digitally signed text printed as the QR plate on the machine (tamper-proof)."""
        return signing.dumps(self.pk, salt="machine")


class Part(models.Model):
    part_number = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=100)
    def __str__(self): return f"{self.part_number} {self.name}"


class Gauge(models.Model):
    serial = models.CharField(max_length=30, unique=True)         # e.g. VC-104
    description = models.CharField(max_length=100, blank=True)
    calibration_expiry = models.DateField()
    def __str__(self): return self.serial

    @property
    def is_calibrated(self):
        return self.calibration_expiry >= timezone.localdate()


class MachinePMCheck(models.Model):
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE)
    date = models.DateField()
    completed = models.BooleanField(default=False)
    checked_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    class Meta:
        unique_together = ("machine", "date")
