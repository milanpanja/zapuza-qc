from django.conf import settings
from django.core import signing
from django.db import models


class RawMaterialLot(models.Model):
    class Status(models.TextChoices):
        IN_LAB = "LAB", "In Lab Testing"
        CLEARED = "OK", "Cleared"
        QUARANTINE = "QUAR", "Supplier Quarantine"

    supplier = models.CharField(max_length=100)
    po_number = models.CharField(max_length=50)
    grade = models.CharField(max_length=50)
    heat_number = models.CharField(max_length=50, db_index=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    mtc_file = models.FileField(upload_to="mtc/")                 # mandatory
    requires_lab_test = models.BooleanField(default=False)
    status = models.CharField(max_length=5, choices=Status.choices, default=Status.CLEARED)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self): return f"{self.heat_number} ({self.grade})"

    @property
    def qr_payload(self):
        return signing.dumps(self.pk, salt="lot")


class SupplierNCR(models.Model):
    lot = models.ForeignKey(RawMaterialLot, on_delete=models.PROTECT)
    reason = models.TextField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
