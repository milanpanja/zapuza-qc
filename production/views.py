from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from accounts.decorators import role_required
from core.audit import log
from core.utils import flash, qr_response
from plant.services import resolve_machine
from . import services as svc
from .forms import HandoverForm
from .models import JobTraveler, Operation, ProductionRun, ShiftHandover

ALL = ("OPR", "INS", "SUP", "QE", "QM", "PM", "WH")


@role_required(*ALL)
def trav_list(request):
    return render(request, "production/trav_list.html", {"travelers": JobTraveler.objects.select_related("part", "raw_lot").order_by("-created_at")[:100]})


@role_required(*ALL)
def trav_detail(request, pk):
    t = get_object_or_404(JobTraveler, pk=pk)
    ops = [(o, svc.fmt_td(o.hold_remaining()) if o.hold_remaining() else "") for o in t.ops.all()]
    return render(request, "production/trav_detail.html", {"t": t, "ops": ops})


@role_required("PM", "QE", "SUP", "WH")
def trav_qr(request, pk):
    return qr_response(get_object_or_404(JobTraveler, pk=pk).qr_payload)


@require_POST
@role_required("OPR", "SUP")
def op_start(request, pk):
    op = get_object_or_404(Operation, pk=pk)
    try:
        svc.start_operation(op, request.user, resolve_machine(request.POST.get("machine_qr")))
        messages.success(request, f"{op} started")
    except ValidationError as e:
        flash(request, e)
    return redirect("trav_detail", pk=op.traveler_id)


@require_POST
@role_required("OPR", "SUP", "QM")
def op_finish(request, pk):
    op = get_object_or_404(Operation, pk=pk)
    try:
        svc.finish_operation(op, request.user)
        messages.success(request, f"{op} signed off")
    except ValidationError as e:
        flash(request, e)
    return redirect("trav_detail", pk=op.traveler_id)


@role_required("OPR", "INS", "SUP", "QM")
def run_detail(request, pk):
    run = get_object_or_404(ProductionRun, pk=pk)
    if request.method == "POST":
        a = request.POST.get("action")
        try:
            if a == "first_piece": svc.approve_first_piece(run, request.user)
            elif a == "count": svc.increment_counter(run, request.user, int(request.POST.get("n", 1)))
            elif a == "check": svc.record_periodic_check(run, request.user)
        except ValidationError as e:
            flash(request, e)
        return redirect("run_detail", pk=pk)
    run.refresh_due()
    return render(request, "production/run.html", {"run": run, "due": run.check_due_since is not None})


@role_required(*ALL)
def handover_list(request):
    return render(request, "production/handover_list.html", {"items": ShiftHandover.objects.select_related("machine", "outgoing_user").order_by("-created_at")[:50]})


@role_required("OPR", "SUP")
def handover_new(request):
    form = HandoverForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        h = form.save(commit=False)
        h.outgoing_user = request.user
        h.save()
        log(request.user, "HANDOVER_CREATED", h)
        return redirect("handover_list")
    return render(request, "form.html", {"form": form, "title": "Digital Shift Handover"})


@require_POST
@role_required("OPR", "SUP")
def handover_ack(request, pk):
    try:
        svc.acknowledge_handover(get_object_or_404(ShiftHandover, pk=pk), request.user)
    except ValidationError as e:
        flash(request, e)
    return redirect("handover_list")


@role_required("SUP", "PM", "QM")
def bottlenecks(request):
    """Idle queue time between operations + actual cycle time."""
    rows = []
    for op in Operation.objects.filter(started_at__isnull=False).select_related("traveler", "machine").order_by("-started_at")[:200]:
        prev = op.traveler.ops.filter(seq__lt=op.seq).order_by("-seq").first()
        idle = (op.started_at - prev.finished_at) if prev and prev.finished_at else None
        cycle = (op.finished_at - op.started_at) if op.finished_at else None
        rows.append({"op": op, "idle": idle, "cycle": cycle})
    rows.sort(key=lambda r: r["idle"].total_seconds() if r["idle"] else -1, reverse=True)
    return render(request, "production/bottlenecks.html", {"rows": rows[:50]})
