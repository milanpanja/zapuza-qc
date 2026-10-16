from django.core import signing
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Machine, MachinePMCheck


def resolve_machine(payload):
    try:
        return Machine.objects.get(pk=signing.loads((payload or "").strip(), salt="machine"))
    except (signing.BadSignature, Machine.DoesNotExist):
        raise ValidationError("Invalid machine QR code")


def can_select_job(machine):
    """Daily PM checklist must be completed before the machine is used."""
    return MachinePMCheck.objects.filter(machine=machine, date=timezone.localdate(), completed=True).exists()


def validate_gauge(gauge):
    if not gauge.is_calibrated:
        raise ValidationError(f"Expired Tool Calibration ({gauge.serial}). Get a calibrated tool from the tool crib.")
