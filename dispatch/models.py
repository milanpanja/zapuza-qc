from django.conf import settings
from django.db import models


class ShippingManifest(models.Model):
    traveler = models.OneToOneField("production.JobTraveler", on_delete=models.PROTECT)
    customer_po = models.CharField(max_length=50)
    batch_size = models.PositiveIntegerField()
    vehicle = models.CharField(max_length=50)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
