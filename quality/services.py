"""ALL quality business rules live here so views, the API and offline sync cannot bypass them."""
from decimal import Decimal, InvalidOperation
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from core.audit import log
from core.notifications import alert_roles
from plant.models import Gauge
from plant.services import resolve_machine, validate_gauge
from production.models import Operation
from production.services import resolve_job
from .models import (Concession, DefectPhoto, Inspection, InspectionTemplate, Measurement, MRBDisposition)

S = Inspection.Status
REVIEW_ROLES = ("SUP", "QM")


# ---------- templates ----------
def release_template(template, user):
    if user.role != "QM" and not user.is_superuser:
        raise PermissionDenied("Only the Quality Manager can release templates")
    if template.is_released:
        raise ValidationError("Already released")
    if not template.fields.exists():
        raise ValidationError("Template has no inspection fields")
    template.is_released, template.approved_by, template.released_at = True, user, timezone.now()
    template.save()
    log(user, "TEMPLATE_RELEASED", template, "draft", "released")


# ---------- tolerance engine ----------
def evaluate(field, value):
    """True = in tolerance (screen turns GREEN), False = out (RED)."""
    D = lambda x: Decimal(str(x))
    K, value = field.Kind, D(value)
    if field.kind == K.TOLERANCE:
        return D(field.nominal) + D(field.lower_tol) <= value <= D(field.nominal) + D(field.upper_tol)
    if field.kind == K.MAX:
        return value <= D(field.nominal)
    if field.kind == K.MIN:
        return value >= D(field.nominal)
    return value == 1


def next_field(inspection):
    done = set(inspection.measurements.values_list("field_id", flat=True))
    return next((f for f in inspection.template.fields.all() if f.pk not in done), None)


# ---------- inspector workflow ----------
def start_inspection(inspector, machine_qr, job_qr, is_final_pdi=False):
    """Two QR scans are mandatory: machine plate + job traveler barcode."""
    machine, job = resolve_machine(machine_qr), resolve_job(job_qr)
    if job.status != "ACTIVE":
        raise ValidationError(f"Job is {job.get_status_display()}")
    open_ = Inspection.objects.filter(inspector=inspector, status=S.IN_PROGRESS).first()
    if open_:
        if open_.job_id == job.pk:
            return open_
        raise ValidationError(f"Finish inspection #{open_.pk} first - the tablet is locked to that job")
    tpl = (InspectionTemplate.objects.filter(part=job.part, is_released=True).order_by("-released_at").first())
    if not tpl:
        raise ValidationError("No released inspection template for this part")
    insp = Inspection.objects.create(template=tpl, machine=machine, job=job, inspector=inspector, is_final_pdi=is_final_pdi)
    log(inspector, "INSPECTION_START", insp, "", f"{machine.code} / {job.work_order}")
    return insp


def record_measurement(inspection, field, raw_value, gauge_serial, user):
    if inspection.status != S.IN_PROGRESS:
        raise ValidationError("This inspection is not open for entry")
    if inspection.inspector_id != user.pk:
        raise ValidationError("Locked to the inspector who started it")
    nxt = next_field(inspection)
    if nxt is None:
        raise ValidationError("All fields are already measured")
    if field.pk != nxt.pk:
        raise ValidationError(f"Fields must be measured in order. Next is #{nxt.pin_number} {nxt.label}")

    gauge = None
    if field.kind == field.Kind.PASSFAIL:
        value = Decimal(1 if str(raw_value).strip().lower() in ("1", "yes", "true", "on", "pass") else 0)
    else:
        try:
            value = Decimal(str(raw_value).strip())
        except InvalidOperation:
            raise ValidationError("Enter a valid number")
        gauge = Gauge.objects.filter(serial=(gauge_serial or "").strip()).first()
        if gauge is None:
            raise ValidationError("Scan/select a registered gauge")
        validate_gauge(gauge)                                    # blocks expired calibration

    passed = evaluate(field, value)
    m = Measurement.objects.create(inspection=inspection, field=field, value=value, passed=passed, gauge=gauge)
    log(user, "MEASUREMENT", f"{inspection} / {field.label}", "", f"{value} {'PASS' if passed else 'FAIL'}")
    if not passed and field.is_ctq:
        inspection.status = S.FROZEN
        inspection.save()
        log(user, "CTQ_FREEZE", inspection, "IN_PROGRESS", "FROZEN")
        alert_roles(["QM"], f"CTQ FAILURE {inspection.job.work_order}",
                    f"{field.label} measured {value} (spec {field.spec_text()}). Checklist frozen.")
    return m


def add_photo(measurement, image, user):
    insp = measurement.inspection
    if insp.inspector_id != user.pk or insp.status not in (S.IN_PROGRESS, S.FROZEN):
        raise ValidationError("Photos can only be added by the inspector while the inspection is open")
    if measurement.passed:
        raise ValidationError("Photos are only for out-of-tolerance entries")
    return DefectPhoto.objects.create(measurement=measurement, image=image)


def complete_inspection(inspection, user):
    if inspection.inspector_id != user.pk:
        raise PermissionDenied
    if inspection.status != S.IN_PROGRESS:
        raise ValidationError("Inspection cannot be completed in its current state")
    if next_field(inspection) is not None:
        raise ValidationError("All fields must be measured before completing")
    for m in inspection.measurements.filter(passed=False):
        if m.photos.count() < 2:
            raise ValidationError(f"At least 2 defect photos required for '{m.field.label}'")
    inspection.status, inspection.completed_at = S.AWAITING_APPROVAL, timezone.now()
    inspection.save()
    log(user, "INSPECTION_DONE", inspection, "IN_PROGRESS", "AWAITING_APPROVAL")


# ---------- supervisor / quality manager ----------
def _can_review(user):
    if user.role not in REVIEW_ROLES and not user.is_superuser:
        raise PermissionDenied


def _awaiting(inspection):
    if inspection.status != S.AWAITING_APPROVAL:
        raise ValidationError("Inspection is not awaiting approval")


def _close(inspection, user, status):
    old = inspection.status
    inspection.status, inspection.reviewed_by, inspection.reviewed_at = status, user, timezone.now()
    inspection.save()
    log(user, f"REVIEW_{status}", inspection, old, status)


def approve_inspection(inspection, user):
    _can_review(user); _awaiting(inspection)
    if inspection.measurements.filter(passed=False).exists():
        raise ValidationError("Failed measurements exist - use Concession or Quarantine")
    _close(inspection, user, S.APPROVED)


def grant_concession(inspection, user, reason_code, justification):
    _can_review(user); _awaiting(inspection)
    if inspection.measurements.filter(passed=False, field__is_ctq=True).exists():
        raise ValidationError("CTQ failures can never be conceded")
    if not reason_code.strip() or not justification.strip():
        raise ValidationError("Reason code and detailed engineering justification are required")
    Concession.objects.create(inspection=inspection, reason_code=reason_code, justification=justification, approved_by=user)
    _close(inspection, user, S.CONCESSION)


def quarantine_inspection(inspection, user):
    _can_review(user)
    if inspection.status not in (S.AWAITING_APPROVAL, S.FROZEN):
        raise ValidationError("Only submitted or frozen inspections can be quarantined")
    inspection.job.status = "QUARANTINED"
    inspection.job.save()
    _close(inspection, user, S.QUARANTINED)


def mrb_decide(inspection, action, user, note="", customer_approval=None):
    if user.role not in ("PM", "QM") and not user.is_superuser:
        raise PermissionDenied
    if inspection.status != S.QUARANTINED or inspection.dispositions.exists():
        raise ValidationError("Inspection is not waiting for an MRB decision")
    job, A = inspection.job, MRBDisposition.Action
    d = MRBDisposition.objects.create(inspection=inspection, action=action, note=note, decided_by=user,
                                      customer_approval=customer_approval or "")
    if action == A.REWORK:
        last = job.ops.order_by("-seq").first().seq if job.ops.exists() else 0
        Operation.objects.create(traveler=job, seq=last + 10, name="Rework (MRB)")
        job.status = "ACTIVE"
    elif action == A.SCRAP:
        job.status = "SCRAPPED"
    elif action == A.RTV:
        job.status = "RETURNED"
    elif action == A.CUSTOMER and customer_approval:
        job.status = "ACTIVE"
    job.save()
    log(user, "MRB_DISPOSITION", inspection, "QUARANTINED", d.get_action_display())
    return d


def attach_customer_approval(disposition, file, user):
    if disposition.action != MRBDisposition.Action.CUSTOMER:
        raise ValidationError("Not a customer concession")
    disposition.customer_approval = file
    disposition.save()
    disposition.inspection.job.status = "ACTIVE"
    disposition.inspection.job.save()
    log(user, "CUSTOMER_APPROVAL", disposition.inspection, "", "uploaded")
