import base64
from typing import Any

from django.contrib.auth.models import User
from rest_framework import serializers


def _b64_validator(value: str) -> None:
    try:
        base64.b64decode(value, validate=True)
    except Exception as exc:
        raise serializers.ValidationError("must be base64-encoded bytes") from exc


class PreauthSerializer(serializers.Serializer[dict[str, Any]]):
    username = serializers.CharField(max_length=150)


class RegisterSerializer(serializers.Serializer[dict[str, Any]]):
    username = serializers.CharField(max_length=150)
    kdf_salt = serializers.CharField(validators=[_b64_validator])
    verifier_salt = serializers.CharField(validators=[_b64_validator])
    verifier = serializers.CharField(validators=[_b64_validator])
    kdf_params = serializers.JSONField()

    def validate_username(self, value: str) -> str:
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("username already taken")
        return value

    def validate_kdf_params(self, value: Any) -> Any:
        for key in ("memory_cost", "iterations", "parallelism", "hash_len"):
            if not isinstance(value, dict) or key not in value:
                raise serializers.ValidationError(f"missing '{key}'")
        return value


class LoginSerializer(serializers.Serializer[dict[str, Any]]):
    username = serializers.CharField(max_length=150)
    verifier = serializers.CharField(validators=[_b64_validator])
