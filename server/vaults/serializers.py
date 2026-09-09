import base64
from typing import Any, ClassVar

from rest_framework import serializers

from .models import Vault, VaultItem

_ENVELOPE_VERSION = 1
_ENVELOPE_FIELDS = ("nonce_c", "ciphertext", "nonce_k", "wrapped_key")


class VaultSerializer(serializers.ModelSerializer[Vault]):
    class Meta:
        model = Vault
        fields = ["id", "name", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class VaultItemSerializer(serializers.ModelSerializer[VaultItem]):
    class Meta:
        model = VaultItem
        fields = [
            "id",
            "vault",
            "service",
            "tags",
            "envelope",
            "last_accessed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "vault", "last_accessed_at", "created_at", "updated_at"]
        extra_kwargs: ClassVar[dict[str, dict[str, Any]]] = {"tags": {"default": []}}

    def validate_envelope(self, value: Any) -> Any:
        if not isinstance(value, dict):
            raise serializers.ValidationError("envelope must be an object")
        if value.get("version") != _ENVELOPE_VERSION:
            raise serializers.ValidationError("unsupported envelope version")
        missing = [field for field in _ENVELOPE_FIELDS if field not in value]
        if missing:
            raise serializers.ValidationError("missing envelope fields: " + ", ".join(missing))
        for field in _ENVELOPE_FIELDS:
            raw = value[field]
            if not isinstance(raw, str):
                raise serializers.ValidationError(f"{field} must be a base64 string")
            try:
                base64.b64decode(raw, validate=True)
            except Exception as exc:
                raise serializers.ValidationError(f"{field} is not valid base64") from exc
        return value
