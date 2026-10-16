from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from accounts.decorators import role_required
from core.audit import log
from core.utils import qr_response
from .models import Machine, MachinePMCheck
from .services import can_select_job


@role_required("PM", "QE", "QM", "SUP", "OPR", "INS")
def machine_list(request):
    rows = [(m, can_select_job(m)) for m in Machine.objects.select_related("site")]
    return render(request, "plant/machine_list.html", {"rows": rows})


@require_POST
@role_required("SUP", "PM")
def machine_pm(request, pk):
    m = get_object_or_404(Machine, pk=pk)
    MachinePMCheck.objects.update_or_create(machine=m, date=timezone.localdate(),
                                            defaults={"completed": True, "checked_by": request.user})
    log(request.user, "PM_CHECK", m, "", "completed")
    return redirect("machine_list")


@role_required("PM", "QE", "SUP")
def machine_qr(request, pk):
    return qr_response(get_object_or_404(Machine, pk=pk).qr_payload)
