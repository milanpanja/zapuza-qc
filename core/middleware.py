import threading

_local = threading.local()


def get_ctx():
    return getattr(_local, "ctx", {})


class AuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.ctx = {"ip": request.META.get("REMOTE_ADDR"),
                      "device": request.headers.get("X-Device-Serial", "")}
        try:
            return self.get_response(request)
        finally:
            _local.ctx = {}
