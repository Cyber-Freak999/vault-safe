from typing import Any

from django.db import models
from django.http import Http404
from rest_framework import generics, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer

from common.audit import log_action

from .models import Vault, VaultItem
from .serializers import VaultItemSerializer, VaultSerializer


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


class ItemListCreateView(generics.ListCreateAPIView[VaultItem]):
    serializer_class = VaultItemSerializer

    def get_vault(self) -> Vault:
        assert self.request.user.is_authenticated
        vault_id = self.kwargs["vault_id"]
        try:
            return Vault.objects.get(pk=vault_id, owner=self.request.user)
        except Vault.DoesNotExist as exc:
            raise Http404 from exc

    def get_queryset(self) -> models.QuerySet[VaultItem]:
        vault = self.get_vault()
        qs = VaultItem.objects.filter(vault=vault)
        service = self.request.query_params.get("service")
        if service:
            qs = qs.filter(service__icontains=service)
        return qs.order_by("service")

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        qs = self.get_queryset()
        tag = request.query_params.get("tag")
        items: models.QuerySet[VaultItem] | list[VaultItem] = qs
        if tag:
            items = [item for item in qs if tag in item.tags]
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        vault = self.get_vault()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = serializer.save(vault=vault)
        assert request.user.is_authenticated
        log_action(request.user, "create_item", item=item, request=request)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
