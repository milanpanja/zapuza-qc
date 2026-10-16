from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from accounts.decorators import role_required
from quality.models import Inspection
from .models import AuditLog


@login_required
def home(request):
    return render(request, "home.html", {
        "awaiting": Inspection.objects.filter(status="AWAITING_APPROVAL").count(),
        "frozen": Inspection.objects.filter(status="FROZEN").count(),
        "quarantined": Inspection.objects.filter(status="QUARANTINED", dispositions__isnull=True).count(),
    })


@role_required("PM", "QM")
def audit_list(request):
    q = request.GET.get("q", "")
    logs = AuditLog.objects.select_related("user")
    if q:
        logs = logs.filter(object_repr__icontains=q)
    return render(request, "audit_list.html", {"logs": logs[:200], "q": q})
