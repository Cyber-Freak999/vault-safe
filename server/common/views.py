from typing import Any

from django.db import models
from rest_framework import generics, permissions
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AuditLog


class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response({"status": "ok"})


class AuditLogView(generics.ListAPIView[AuditLog]):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self) -> models.QuerySet[AuditLog]:
        assert self.request.user.is_authenticated
        qs = AuditLog.objects.filter(user=self.request.user).order_by("-at")
        limit = self.request.query_params.get("limit")
        if limit:
            qs = qs[: int(limit)]
        return qs

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        queryset = self.get_queryset()
        return Response(list(queryset.values("id", "action", "item_id", "ip", "at")))
