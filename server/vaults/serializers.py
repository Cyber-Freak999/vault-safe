from rest_framework import serializers

from .models import Vault


class VaultSerializer(serializers.ModelSerializer[Vault]):
    class Meta:
        model = Vault
        fields = ["id", "name", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
