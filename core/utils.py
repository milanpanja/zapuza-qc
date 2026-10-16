import io
import qrcode
from django.contrib import messages
from django.http import HttpResponse


def qr_response(text):
    buf = io.BytesIO()
    qrcode.make(text).save(buf, format="PNG")
    return HttpResponse(buf.getvalue(), content_type="image/png")


def flash(request, exc):
    for m in getattr(exc, "messages", None) or [str(exc)]:
        messages.error(request, m)
