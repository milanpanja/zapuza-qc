import json
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from accounts.decorators import role_required
from core.utils import flash
from . import services as svc
from .models import Inspection, InspectionTemplate, Measurement, MRBDisposition, TemplateField


@role_required("QE", "QM", "PM")
def tpl_list(request):
    return render(request, "quality/tpl_list.html", {"templates": InspectionTemplate.objects.select_related("part")})


@require_POST
@role_required("QM")
def tpl_release(request, pk):
    try:
        svc.release_template(get_object_or_404(InspectionTemplate, pk=pk), request.user)
        messages.success(request, "Template released to the shopfloor")
    except ValidationError as e:
        flash(request, e)
    return redirect("tpl_list")


@role_required("INS")
def scan(request):
    if request.method == "POST":
        try:
            insp = svc.start_inspection(request.user, request.POST.get("machine_qr"), request.POST.get("job_qr"),
                                        is_final_pdi="final_pdi" in request.POST)
            return redirect("inspection", pk=insp.pk)
        except ValidationError as e:
            flash(request, e)
    from django.conf import settings
    return render(request, "quality/scan.html", {"manual": settings.DEBUG})


@role_required("INS", "SUP", "QM", "PM")
def inspection(request, pk):
    insp = get_object_or_404(Inspection.objects.select_related("template", "job", "machine"), pk=pk)
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "measure":
                field = get_object_or_404(TemplateField, pk=request.POST.get("field"))
                m = svc.record_measurement(insp, field, request.POST.get("value"), request.POST.get("gauge"), request.user)
                messages.success(request, "IN TOLERANCE" if m.passed else "OUT OF TOLERANCE - take at least 2 defect photos")
            elif action == "photo":
                m = get_object_or_404(Measurement, pk=request.POST.get("measurement"), inspection=insp)
                for f in request.FILES.getlist("image"):
                    svc.add_photo(m, f, request.user)
            elif action == "complete":
                svc.complete_inspection(insp, request.user)
                messages.success(request, "Sent to supervisor for approval")
                return redirect("home")
        except ValidationError as e:
            flash(request, e)
        return redirect("inspection", pk=pk)
    return render(request, "quality/inspection.html", {
        "insp": insp, "next": svc.next_field(insp) if insp.status == "IN_PROGRESS" else None,
        "measurements": insp.measurements.select_related("field", "gauge").prefetch_related("photos"),
        "fields": insp.template.fields.all()})


@role_required("SUP", "QM")
def queue(request):
    order = {"machine": "machine__code", "urgency": "completed_at"}.get(request.GET.get("sort"), "completed_at")
    items = Inspection.objects.filter(status__in=["AWAITING_APPROVAL", "FROZEN"]).select_related("job", "machine", "inspector").order_by(order)
    return render(request, "quality/queue.html", {"items": items})


@role_required("SUP", "QM")
def review(request, pk):
    insp = get_object_or_404(Inspection, pk=pk)
    if request.method == "POST":
        a = request.POST.get("action")
        try:
            if a == "approve": svc.approve_inspection(insp, request.user)
            elif a == "concession":
                svc.grant_concession(insp, request.user, request.POST.get("reason_code", ""), request.POST.get("justification", ""))
            elif a == "quarantine": svc.quarantine_inspection(insp, request.user)
            messages.success(request, f"Done: {a}")
            return redirect("queue")
        except ValidationError as e:
            flash(request, e)
    return render(request, "quality/review.html", {"insp": insp, "measurements": insp.measurements.select_related("field", "gauge").prefetch_related("photos")})


@role_required("PM", "QM")
def mrb(request):
    if request.method == "POST":
        insp = get_object_or_404(Inspection, pk=request.POST.get("inspection"))
        try:
            svc.mrb_decide(insp, request.POST.get("action"), request.user, request.POST.get("note", ""), request.FILES.get("approval"))
            messages.success(request, "MRB disposition recorded")
        except ValidationError as e:
            flash(request, e)
        return redirect("mrb")
    return render(request, "quality/mrb.html", {
        "items": Inspection.objects.filter(status="QUARANTINED", dispositions__isnull=True).select_related("job"),
        "actions": MRBDisposition.Action.choices,
        "pending_cc": MRBDisposition.objects.filter(action="CC", customer_approval="")})


@require_POST
@role_required("INS")
def sync(request):
    """Offline sync: tablet posts queued entries; each goes through the SAME service rules."""
    try:
        items = json.loads(request.body)["items"]
    except (ValueError, KeyError):
        return JsonResponse({"error": "bad payload"}, status=400)
    results = []
    for it in items:
        try:
            insp = Inspection.objects.get(pk=it["inspection"])
            field = TemplateField.objects.get(pk=it["field"])
            svc.record_measurement(insp, field, it.get("value"), it.get("gauge"), request.user)
            results.append({"ok": True})
        except (ValidationError, Inspection.DoesNotExist, TemplateField.DoesNotExist, KeyError) as e:
            results.append({"ok": False, "error": getattr(e, "messages", [str(e)])[0]})
    return JsonResponse({"results": results})
