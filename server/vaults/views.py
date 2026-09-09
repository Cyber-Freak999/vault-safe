from django.db import models
from rest_framework import generics
from rest_framework.serializers import BaseSerializer

from common.audit import log_action

from .models import Vault
from .serializers import VaultSerializer


class VaultListCreateView(generics.ListCreateAPIView[Vault]):
    serializer_class = VaultSerializer

    def get_queryset(self) -> models.QuerySet[Vault]:
        assert self.request.user.is_authenticated
        return Vault.objects.filter(owner=self.request.user).order_by("name")

    def perform_create(self, serializer: BaseSerializer[Vault]) -> None:
        serializer.save(owner=self.request.user)
        assert self.request.user.is_authenticated
        log_action(self.request.user, "create_vault", request=self.request)


class VaultDetailView(generics.RetrieveUpdateDestroyAPIView[Vault]):
    serializer_class = VaultSerializer

    def get_queryset(self) -> models.QuerySet[Vault]:
        assert self.request.user.is_authenticated
        return Vault.objects.filter(owner=self.request.user)

    def perform_update(self, serializer: BaseSerializer[Vault]) -> None:
        serializer.save()
        assert self.request.user.is_authenticated
        log_action(self.request.user, "update_vault", request=self.request)

    def perform_destroy(self, instance: Vault) -> None:
        assert self.request.user.is_authenticated
        log_action(self.request.user, "delete_vault", request=self.request)
        instance.delete()
