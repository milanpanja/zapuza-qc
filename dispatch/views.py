from django.contrib import messages
from django.core import signing
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from accounts.decorators import role_required
from core.utils import flash, qr_response
from production.models import JobTraveler
from .services import cert_token, create_manifest, shipping_clearance, traveler_from_token


@role_required("WH", "SUP", "PM", "QM")
def gate_pass(request, pk):
    t = get_object_or_404(JobTraveler, pk=pk)
    errors = shipping_clearance(t)
    if errors:   # Shipping Interlock: no packing slip / gate pass / invoice
        return render(request, "dispatch/lockout.html", {"t": t, "errors": errors}, status=403)
    if request.method == "POST":
        try:
            create_manifest(t, request.user, request.POST["customer_po"], int(request.POST["batch_size"]), request.POST["vehicle"])
            messages.success(request, "Manifest created and gate pass cleared")
            return redirect("gate_pass", pk=pk)
        except (ValidationError, ValueError, KeyError) as e:
            flash(request, e)
    return render(request, "dispatch/gate_pass.html", {"t": t, "token": cert_token(t), "manifest": getattr(t, "shippingmanifest", None)})


@role_required("WH", "SUP", "PM", "QM")
def cert_qr(request, pk):
    t = get_object_or_404(JobTraveler, pk=pk)
    if shipping_clearance(t):
        raise Http404
    return qr_response(request.build_absolute_uri(f"/dispatch/cert/{cert_token(t)}/"))


def cert(request, token):
    """PUBLIC page opened by the customer scanning the crate QR."""
    try:
        t = traveler_from_token(token)
    except (signing.BadSignature, ObjectDoesNotExist):
        raise Http404
    insps = t.inspections.filter(status__in=["APPROVED", "CONCESSION"]).prefetch_related("measurements__field", "measurements__gauge")
    return render(request, "dispatch/certificate.html", {"t": t, "lot": t.raw_lot, "insps": insps})
