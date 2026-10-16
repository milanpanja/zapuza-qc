from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail


def alert_roles(roles, subject, message):
    """Email every active user with one of the roles. (Swap for Celery task / SMS later.)"""
    emails = list(get_user_model().objects.filter(role__in=roles, is_active=True)
                  .exclude(email="").values_list("email", flat=True))
    if emails:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, emails, fail_silently=True)
