from django.core.exceptions import PermissionDenied, ValidationError
from core.audit import log
from core.notifications import alert_roles
from .models import RawMaterialLot, SupplierNCR


def register_lot(user, lot):
    """Save a new lot: lab-test grades wait in 'In Lab Testing', others are cleared."""
    if not lot.mtc_file:
        raise ValidationError("A readable Mill Test Certificate (MTC) is mandatory")
    lot.received_by = user
    lot.status = RawMaterialLot.Status.IN_LAB if lot.requires_lab_test else RawMaterialLot.Status.CLEARED
    lot.save()
    log(user, "LOT_RECEIVED", lot, "", lot.status)
    return lot


def reject_lot(lot, user, reason):
    if not reason.strip():
        raise ValidationError("Rejection reason is required")
    old = lot.status
    lot.status = RawMaterialLot.Status.QUARANTINE
    lot.save()
    ncr = SupplierNCR.objects.create(lot=lot, reason=reason, created_by=user)
    log(user, "LOT_REJECTED", lot, old, lot.status)
    alert_roles(["QM", "PM"], f"SNCR: heat {lot.heat_number}", f"Supplier {lot.supplier} lot rejected: {reason}")
    return ncr


def clear_lot(lot, user):
    if user.role not in ("QM", "QE") and not user.is_superuser:
        raise PermissionDenied
    if lot.status != RawMaterialLot.Status.IN_LAB:
        raise ValidationError("Only lots in lab testing can be cleared")
    lot.status = RawMaterialLot.Status.CLEARED
    lot.save()
    log(user, "LOT_CLEARED", lot, "LAB", "OK")


def assert_issuable(lot):
    if lot.status != RawMaterialLot.Status.CLEARED:
        raise ValidationError(f"Lot {lot.heat_number} is '{lot.get_status_display()}' and cannot be issued to production")
