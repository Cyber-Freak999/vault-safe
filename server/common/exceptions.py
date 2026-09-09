from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

_CODES = {
    status.HTTP_400_BAD_REQUEST: "validation_error",
    status.HTTP_401_UNAUTHORIZED: "authentication_failed",
    status.HTTP_403_FORBIDDEN: "permission_denied",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_405_METHOD_NOT_ALLOWED: "method_not_allowed",
    status.HTTP_429_TOO_MANY_REQUESTS: "throttled",
}


def _as_fields(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {"detail": str(data)}
    return {
        str(key): (value[0] if isinstance(value, list) and value else value)
        for key, value in data.items()
    }


def _first_message(fields: dict[str, Any]) -> str:
    for value in fields.values():
        if isinstance(value, list):
            if value:
                return str(value[0])
            continue
        return str(value)
    return "invalid request"


def vaultsafe_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    response = exception_handler(exc, context)
    if response is None or response.status_code not in _CODES:
        return response
    fields = _as_fields(response.data)
    response.data = {
        "error": {
            "code": _CODES[response.status_code],
            "message": _first_message(fields),
            "fields": fields,
        }
    }
    return response
