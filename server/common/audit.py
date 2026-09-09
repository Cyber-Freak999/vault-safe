from django.contrib.auth.models import User
from django.http import HttpRequest

from vaults.models import VaultItem

from .models import AuditLog


def log_action(
    user: User,
    action: str,
    *,
    item: VaultItem | None = None,
    request: HttpRequest | None = None,
) -> None:
    ip = request.META.get("REMOTE_ADDR") if request else None
    AuditLog.objects.create(user=user, action=action, item=item, ip=ip)
