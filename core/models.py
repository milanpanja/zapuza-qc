from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import models


class AppendOnlyQuerySet(models.QuerySet):
    def update(self, *a, **k):
        raise PermissionDenied("Audit logs are append-only")

    def delete(self):
        raise PermissionDenied("Audit logs cannot be deleted")


class AuditLog(models.Model):
    """Immutable record of every important action."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    action = models.CharField(max_length=40)
    object_repr = models.CharField(max_length=200)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_serial = models.CharField(max_length=60, blank=True)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        ordering = ["-timestamp"]

    def save(self, *a, **k):
        if self.pk:
            raise PermissionDenied("Audit logs are append-only")
        super().save(*a, **k)

    def delete(self, *a, **k):
        raise PermissionDenied("Audit logs cannot be deleted")
