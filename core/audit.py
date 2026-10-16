from .middleware import get_ctx
from .models import AuditLog


def log(user, action, obj, old="", new=""):
    ctx = get_ctx()
    AuditLog.objects.create(
        user=user if getattr(user, "pk", None) else None,
        action=action, object_repr=str(obj)[:200],
        old_value=str(old), new_value=str(new),
        ip_address=ctx.get("ip"), device_serial=ctx.get("device", ""),
    )
