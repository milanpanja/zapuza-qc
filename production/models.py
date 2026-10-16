from datetime import timedelta
from django.conf import settings
from django.core import signing
from django.db import models
from django.utils import timezone
from materials.services import assert_issuable


class JobTraveler(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        QUARANTINED = "QUARANTINED", "Quarantined"
        SCRAPPED = "SCRAPPED", "Scrapped"
        RETURNED = "RETURNED", "Returned to vendor"
        SHIPPED = "SHIPPED", "Shipped"

    work_order = models.CharField(max_length=30, unique=True)
    part = models.ForeignKey("plant.Part", on_delete=models.PROTECT)
    raw_lot = models.ForeignKey("materials.RawMaterialLot", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self): return self.work_order

    def save(self, *a, **k):
        if self._state.adding:
            assert_issuable(self.raw_lot)        # quarantined / lab lots can never be issued
        super().save(*a, **k)

    @property
    def qr_payload(self):
        return signing.dumps(self.pk, salt="job")

    def has_active_holds(self):
        return any(op.hold_remaining() for op in self.ops.all())


class Operation(models.Model):
    traveler = models.ForeignKey(JobTraveler, related_name="ops", on_delete=models.CASCADE)
    seq = models.PositiveSmallIntegerField()                      # 10, 20, 30 ...
    name = models.CharField(max_length=60)
    hold_minutes = models.PositiveIntegerField(default=0, help_text="Mandatory cooling/curing time AFTER this op")
    requires_first_piece = models.BooleanField(default=False)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    machine = models.ForeignKey("plant.Machine", null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        ordering = ["seq"]
        unique_together = ("traveler", "seq")

    def __str__(self): return f"Op {self.seq} {self.name}"

    def hold_remaining(self):
        if not (self.finished_at and self.hold_minutes):
            return timedelta(0)
        return max(self.finished_at + timedelta(minutes=self.hold_minutes) - timezone.now(), timedelta(0))


class SerialNumber(models.Model):
    traveler = models.ForeignKey(JobTraveler, related_name="serials", on_delete=models.PROTECT)
    number = models.CharField(max_length=60, unique=True)


class ProductionRun(models.Model):
    """Created automatically for operations that need First-Piece approval."""
    operation = models.OneToOneField(Operation, related_name="run", on_delete=models.CASCADE)
    first_piece_approved = models.BooleanField(default=False)
    first_piece_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    parts_count = models.PositiveIntegerField(default=0)
    check_every_parts = models.PositiveIntegerField(default=50)
    check_every_minutes = models.PositiveIntegerField(default=60)
    last_check_count = models.PositiveIntegerField(default=0)
    last_check_time = models.DateTimeField(default=timezone.now)
    check_due_since = models.DateTimeField(null=True, blank=True)
    timer_paused = models.BooleanField(default=False)
    GRACE = timedelta(minutes=15)

    def refresh_due(self):
        if self.check_due_since is None:
            by_count = self.parts_count - self.last_check_count >= self.check_every_parts
            time_due = self.last_check_time + timedelta(minutes=self.check_every_minutes)
            if by_count:
                self.check_due_since = timezone.now()
            elif timezone.now() >= time_due:
                self.check_due_since = time_due

    def grace_expired(self):
        return bool(self.check_due_since and timezone.now() > self.check_due_since + self.GRACE)


class ShiftHandover(models.Model):
    machine = models.ForeignKey("plant.Machine", on_delete=models.PROTECT)
    shift = models.CharField(max_length=20)
    outgoing_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="+", on_delete=models.PROTECT)
    active_job_status = models.CharField(max_length=200, blank=True)
    parts_produced = models.PositiveIntegerField(default=0)
    scrap_count = models.PositiveIntegerField(default=0)
    open_quality_alerts = models.TextField(blank=True)
    pending_pdi_reviews = models.TextField(blank=True)
    tool_wear = models.TextField(blank=True)
    machine_health = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    acknowledged_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, related_name="+", on_delete=models.PROTECT)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
