from django.core import signing
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.utils import timezone
from core.audit import log
from plant.services import can_select_job
from .models import JobTraveler, ProductionRun, ShiftHandover

OPEN_INSPECTION = ["IN_PROGRESS", "AWAITING_APPROVAL", "FROZEN"]


def resolve_job(payload):
    try:
        return JobTraveler.objects.get(pk=signing.loads((payload or "").strip(), salt="job"))
    except (signing.BadSignature, ObjectDoesNotExist):
        raise ValidationError("Invalid job traveler barcode")


def fmt_td(td):
    mins = int(td.total_seconds() // 60)
    return f"{mins // 60} hr {mins % 60} min"


def start_operation(op, user, machine):
    t = op.traveler
    if t.status != "ACTIVE":
        raise ValidationError(f"Job is {t.get_status_display()} - work is blocked")
    if op.started_at:
        raise ValidationError("Operation already started")
    prev = t.ops.filter(seq__lt=op.seq).order_by("-seq").first()
    if prev and not prev.finished_at:
        raise ValidationError(f"Op {prev.seq} ({prev.name}) is not complete")
    if prev and prev.hold_remaining():
        raise ValidationError(f"Mandatory Cooling Hold Active ({fmt_td(prev.hold_remaining())} remaining)")
    if t.inspections.filter(status__in=OPEN_INSPECTION).exists():
        raise ValidationError("A quality inspection/review is still pending for this job")
    if not can_select_job(machine):
        raise ValidationError("Machine daily PM check is pending - job selection disabled")
    if ShiftHandover.objects.filter(machine=machine, acknowledged_at__isnull=True).exists():
        raise ValidationError("Acknowledge the shift handover log for this machine first")
    op.started_at, op.operator, op.machine = timezone.now(), user, machine
    op.save()
    if op.requires_first_piece:
        ProductionRun.objects.get_or_create(operation=op)
    log(user, "OP_START", f"{t.work_order} {op}", "", machine.code)


def finish_operation(op, user):
    if not op.started_at or op.finished_at:
        raise ValidationError("Operation is not running")
    if op.operator_id != user.pk and user.role not in ("SUP", "QM") and not user.is_superuser:
        raise PermissionDenied
    run = getattr(op, "run", None)
    if run and not run.first_piece_approved:
        raise ValidationError("First-piece inspection sign-off is still pending")
    op.finished_at = timezone.now()
    op.save()
    log(user, "OP_FINISH", f"{op.traveler.work_order} {op}", "", "signed off")


def approve_first_piece(run, user):
    if user.role not in ("INS", "SUP", "QM") and not user.is_superuser:
        raise PermissionDenied
    run.first_piece_approved, run.first_piece_by = True, user
    run.last_check_time = timezone.now()
    run.save()
    log(user, "FIRST_PIECE", run.operation, "pending", "approved")


def increment_counter(run, user, n=1):
    if not run.first_piece_approved:
        raise ValidationError("Machine is in Setup Mode - first piece not approved")
    run.refresh_due()
    if run.grace_expired():
        run.timer_paused = True
        run.save()
        raise ValidationError("Periodic Quality Inspection overdue - job timer paused")
    run.parts_count += n
    run.refresh_due()
    run.save()


def record_periodic_check(run, user):
    run.last_check_count, run.last_check_time = run.parts_count, timezone.now()
    run.check_due_since, run.timer_paused = None, False
    run.save()
    log(user, "PERIODIC_CHECK", run.operation, "", f"count={run.parts_count}")


def acknowledge_handover(h, user):
    if user.pk == h.outgoing_user_id:
        raise ValidationError("The incoming worker must acknowledge the handover")
    h.acknowledged_by, h.acknowledged_at = user, timezone.now()
    h.save()
    log(user, "HANDOVER_ACK", f"{h.machine} {h.shift}")
