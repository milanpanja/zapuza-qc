from django.core import signing
from django.core.exceptions import ValidationError
from core.audit import log


def shipping_clearance(traveler):
    """Returns a list of unmet requirements. Empty list = cleared."""
    errors = []
    if traveler.status not in ("ACTIVE", "SHIPPED"):
        errors.append(f"Job status is {traveler.get_status_display()}")
    ops = list(traveler.ops.all())
    if not ops:
        errors.append("No operations routed for this job")
    for op in ops:
        if not op.finished_at:
            errors.append(f"Op {op.seq} ({op.name}) is not signed off")
    if traveler.has_active_holds():
        errors.append("Mandatory hold/cooling time not yet fulfilled")
    pdi = traveler.inspections.filter(is_final_pdi=True).order_by("-started_at").first()
    if not pdi or pdi.status not in ("APPROVED", "CONCESSION"):
        errors.append("Final PDI checklist is not signed and approved by Quality")
    return errors


def create_manifest(traveler, user, po, batch_size, vehicle):
    from .models import ShippingManifest
    errors = shipping_clearance(traveler)
    if errors:
        raise ValidationError(errors)
    m = ShippingManifest.objects.create(traveler=traveler, customer_po=po, batch_size=batch_size, vehicle=vehicle, created_by=user)
    traveler.status = "SHIPPED"
    traveler.save()
    log(user, "SHIPPED", traveler, "", f"PO {po}")
    return m


def cert_token(traveler):
    return signing.dumps(traveler.pk, salt="cert")


def traveler_from_token(token):
    from production.models import JobTraveler
    return JobTraveler.objects.get(pk=signing.loads(token, salt="cert"))
