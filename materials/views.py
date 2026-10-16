from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from accounts.decorators import role_required
from core.utils import flash, qr_response
from .forms import LotForm
from .models import RawMaterialLot
from .services import clear_lot, register_lot, reject_lot


@role_required("DOCK", "QE", "QM", "PM", "SUP")
def lot_list(request):
    return render(request, "materials/list.html", {"lots": RawMaterialLot.objects.order_by("-received_at")[:100]})


@role_required("DOCK", "QM")
def lot_new(request):
    form = LotForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            register_lot(request.user, form.save(commit=False))
            messages.success(request, "Raw material intake saved")
            return redirect("lot_list")
        except ValidationError as e:
            flash(request, e)
    return render(request, "form.html", {"form": form, "title": "New Raw Material Intake", "multipart": True})


@require_POST
@role_required("DOCK", "QM")
def lot_reject(request, pk):
    try:
        reject_lot(get_object_or_404(RawMaterialLot, pk=pk), request.user, request.POST.get("reason", ""))
        messages.success(request, "Lot quarantined and SNCR created")
    except ValidationError as e:
        flash(request, e)
    return redirect("lot_list")


@require_POST
@role_required("QM", "QE")
def lot_clear(request, pk):
    try:
        clear_lot(get_object_or_404(RawMaterialLot, pk=pk), request.user)
    except ValidationError as e:
        flash(request, e)
    return redirect("lot_list")


@role_required("DOCK", "QM", "QE")
def lot_label(request, pk):
    return qr_response(get_object_or_404(RawMaterialLot, pk=pk).qr_payload)
