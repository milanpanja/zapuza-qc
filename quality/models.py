from decimal import Decimal
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models


class InspectionTemplate(models.Model):
    part = models.ForeignKey("plant.Part", on_delete=models.PROTECT)
    revision = models.CharField(max_length=10)                    # Rev A, Rev B ...
    drawing = models.FileField(upload_to="drawings/", blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, related_name="+", on_delete=models.SET_NULL)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, related_name="+", on_delete=models.SET_NULL)
    is_released = models.BooleanField(default=False)
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("part", "revision")

    def __str__(self): return f"{self.part.part_number} Rev {self.revision}"

    def save(self, *a, **k):
        if self.pk and InspectionTemplate.objects.filter(pk=self.pk, is_released=True).exists():
            raise ValidationError("Released templates are read-only. Create a new revision instead.")
        super().save(*a, **k)

    def delete(self, *a, **k):
        if self.is_released:
            raise ValidationError("Released templates cannot be deleted")
        super().delete(*a, **k)


class TemplateField(models.Model):
    class Kind(models.TextChoices):
        TOLERANCE = "TOL", "Dimension +/- tolerance"
        MAX = "MAX", "Maximum limit"
        MIN = "MIN", "Minimum limit"
        PASSFAIL = "PF", "Visual pass/fail"

    template = models.ForeignKey(InspectionTemplate, related_name="fields", on_delete=models.CASCADE)
    pin_number = models.PositiveSmallIntegerField()
    pin_x = models.FloatField(default=0, help_text="% from left on drawing")
    pin_y = models.FloatField(default=0, help_text="% from top on drawing")
    label = models.CharField(max_length=100)
    kind = models.CharField(max_length=3, choices=Kind.choices)
    nominal = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    upper_tol = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, help_text="e.g. 0.05")
    lower_tol = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, help_text="signed, e.g. -0.02")
    unit = models.CharField(max_length=10, default="mm", blank=True)
    is_ctq = models.BooleanField(default=False)

    class Meta:
        ordering = ["pin_number"]
        unique_together = ("template", "pin_number")

    def __str__(self): return f"#{self.pin_number} {self.label}"

    def save(self, *a, **k):
        if self.template.is_released:
            raise ValidationError("Template is released; fields are read-only")
        super().save(*a, **k)

    def delete(self, *a, **k):
        if self.template.is_released:
            raise ValidationError("Template is released; fields are read-only")
        super().delete(*a, **k)

    def spec_text(self):
        if self.kind == "TOL":
            return f"{self.nominal} {self.unit} (+{self.upper_tol} / {self.lower_tol})"
        if self.kind == "MAX": return f"{self.nominal} {self.unit} MAX"
        if self.kind == "MIN": return f"{self.nominal} {self.unit} MIN"
        return "Pass / Fail"


class Inspection(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS"
        AWAITING_APPROVAL = "AWAITING_APPROVAL"
        APPROVED = "APPROVED"
        CONCESSION = "CONCESSION"
        QUARANTINED = "QUARANTINED"
        FROZEN = "FROZEN"

    template = models.ForeignKey(InspectionTemplate, on_delete=models.PROTECT)
    machine = models.ForeignKey("plant.Machine", on_delete=models.PROTECT)
    job = models.ForeignKey("production.JobTraveler", related_name="inspections", on_delete=models.PROTECT)
    inspector = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="+", on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    is_final_pdi = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, related_name="+", on_delete=models.SET_NULL)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self): return f"Inspection #{self.pk} {self.job}"


class Measurement(models.Model):
    inspection = models.ForeignKey(Inspection, related_name="measurements", on_delete=models.CASCADE)
    field = models.ForeignKey(TemplateField, on_delete=models.PROTECT)
    value = models.DecimalField(max_digits=14, decimal_places=4)
    passed = models.BooleanField()
    gauge = models.ForeignKey("plant.Gauge", null=True, blank=True, on_delete=models.PROTECT)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("inspection", "field")

    def save(self, *a, **k):
        if self.pk:
            raise PermissionDenied("Submitted measurements cannot be edited")
        super().save(*a, **k)

    def delete(self, *a, **k):
        raise PermissionDenied("Measurements cannot be deleted")


class DefectPhoto(models.Model):
    measurement = models.ForeignKey(Measurement, related_name="photos", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="defects/")
    taken_at = models.DateTimeField(auto_now_add=True)


class Concession(models.Model):
    inspection = models.OneToOneField(Inspection, related_name="concession", on_delete=models.PROTECT)
    reason_code = models.CharField(max_length=20)
    justification = models.TextField()
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)


class MRBDisposition(models.Model):
    class Action(models.TextChoices):
        REWORK = "RW", "Rework order"
        SCRAP = "SC", "Scrap"
        RTV = "RTV", "Return to vendor"
        CUSTOMER = "CC", "Customer special concession"

    inspection = models.ForeignKey(Inspection, related_name="dispositions", on_delete=models.PROTECT)
    action = models.CharField(max_length=3, choices=Action.choices)
    note = models.TextField(blank=True)
    customer_approval = models.FileField(upload_to="customer_approvals/", blank=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
