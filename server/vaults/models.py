from django.conf import settings
from django.db import models


class Vault(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vaults"
    )
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class VaultItem(models.Model):
    vault = models.ForeignKey(Vault, on_delete=models.CASCADE, related_name="items")
    service = models.CharField(max_length=200, db_index=True)
    tags = models.JSONField(default=list)
    envelope = models.JSONField()
    last_accessed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
