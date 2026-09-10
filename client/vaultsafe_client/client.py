from __future__ import annotations

import base64
from typing import Any, cast

import httpx

from .envelope import Envelope, build_envelope, unseal_envelope
from .kdf import DefaultParams, KdfParams, derive_kek, derive_verifier, generate_salt


class VaultApiError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status: int | None = None,
        fields: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.fields = fields or {}

    @classmethod
    def from_response(cls, response: httpx.Response) -> VaultApiError:
        payload: Any = {}
        if response.headers.get("content-type", "").startswith("application/json"):
            try:
                payload = response.json()
            except ValueError:
                payload = {}
        error = payload.get("error", {}) if isinstance(payload, dict) else {}
        return cls(
            code=str(error.get("code", "api_error")),
            message=str(error.get("message", f"HTTP {response.status_code}")),
            status=response.status_code,
            fields=error.get("fields"),
        )


class VaultClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"), timeout=timeout, transport=transport
        )
        self._token: str | None = None
        self._kek: bytes | None = None

    # -- lifecycle ----------------------------------------------------------

    def register(
        self,
        username: str,
        password: str,
        *,
        params: KdfParams = DefaultParams,
    ) -> None:
        kdf_salt = generate_salt()
        kek = derive_kek(password, kdf_salt, params)
        verifier_salt = generate_salt()
        verifier = derive_verifier(kek, verifier_salt, params)
        self._request(
            "POST",
            "/api/auth/register",
            json={
                "username": username,
                "kdf_salt": base64.b64encode(kdf_salt).decode("ascii"),
                "verifier_salt": base64.b64encode(verifier_salt).decode("ascii"),
                "verifier": base64.b64encode(verifier).decode("ascii"),
                "kdf_params": params.to_dict(),
            },
        )
        self._kek = kek

    def preauth(self, username: str) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._request("GET", "/api/auth/preauth", params={"username": username}),
        )

    def login(self, username: str, password: str) -> None:
        challenge = self.preauth(username)
        params = KdfParams.from_dict(challenge["kdf_params"])
        kek = derive_kek(password, base64.b64decode(challenge["kdf_salt"]), params)
        verifier = derive_verifier(kek, base64.b64decode(challenge["verifier_salt"]), params)
        response = self._request(
            "POST",
            "/api/auth/login",
            json={
                "username": username,
                "verifier": base64.b64encode(verifier).decode("ascii"),
            },
        )
        self._token = str(response["token"])
        self._kek = kek

    def logout(self) -> None:
        self._request("POST", "/api/auth/logout")
        self._token = None
        self._kek = None

    def me(self) -> dict[str, Any]:
        return cast(dict[str, Any], self._request("GET", "/api/me"))

    # -- vaults -------------------------------------------------------------

    def create_vault(self, name: str) -> dict[str, Any]:
        return cast(dict[str, Any], self._request("POST", "/api/vaults", json={"name": name}))

    def list_vaults(self) -> list[Any]:
        data = self._request("GET", "/api/vaults")
        return cast(list[Any], data)

    def delete_vault(self, vault_id: int) -> None:
        self._request("DELETE", f"/api/vaults/{vault_id}")

    # -- items --------------------------------------------------------------

    def create_item(
        self,
        vault_id: int,
        service: str,
        secret_fields: dict[str, str],
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        kek = self._require_unlocked()
        envelope = build_envelope(secret_fields, kek)
        return cast(
            dict[str, Any],
            self._request(
                "POST",
                f"/api/vaults/{vault_id}/items",
                json={
                    "vault": vault_id,
                    "service": service,
                    "tags": tags or [],
                    "envelope": envelope.to_dict(),
                },
            ),
        )

    def list_items(
        self,
        vault_id: int,
        *,
        service: str | None = None,
        tag: str | None = None,
    ) -> list[Any]:
        url = f"/api/vaults/{vault_id}/items"
        params: dict[str, Any] = {}
        if service is not None:
            params["service"] = service
        if tag is not None:
            params["tag"] = tag
        data = self._request("GET", url, params=params)
        return cast(list[Any], data)

    def get_item(self, item_id: int) -> dict[str, Any]:
        return cast(dict[str, Any], self._request("GET", f"/api/items/{item_id}"))

    def get_secret(self, item_id: int) -> dict[str, str]:
        kek = self._require_unlocked()
        item = self.get_item(item_id)
        return unseal_envelope(Envelope.from_dict(item["envelope"]), kek)

    def update_item(
        self,
        item_id: int,
        *,
        service: str | None = None,
        secret_fields: dict[str, str] | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        kek = self._require_unlocked()
        payload: dict[str, Any] = {}
        if service is not None:
            payload["service"] = service
        if tags is not None:
            payload["tags"] = tags
        if secret_fields is not None:
            payload["envelope"] = build_envelope(secret_fields, kek).to_dict()
        return cast(dict[str, Any], self._request("PATCH", f"/api/items/{item_id}", json=payload))

    def delete_item(self, item_id: int) -> None:
        self._request("DELETE", f"/api/items/{item_id}")

    # -- audit --------------------------------------------------------------

    def audit_log(self, limit: int = 50) -> list[Any]:
        data = self._request("GET", "/api/audit", params={"limit": limit})
        return cast(list[Any], data)

    # -- internals ----------------------------------------------------------

    def _require_unlocked(self) -> bytes:
        if self._kek is None:
            raise VaultApiError("not_unlocked", "call register() or login() first")
        return self._kek

    def current_kek(self) -> bytes:
        return self._require_unlocked()

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
    ) -> Any:
        headers: dict[str, str] = {}
        if self._token is not None:
            headers["Authorization"] = f"Token {self._token}"
        try:
            response = self._http.request(method, url, headers=headers, params=params, json=json)
        except httpx.RequestError as exc:
            raise VaultApiError("connection_error", f"could not reach server: {exc}") from exc
        if response.status_code >= 400:
            raise VaultApiError.from_response(response)
        if response.status_code == 204:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise VaultApiError(
                "unexpected_response",
                f"server returned a non-JSON response: {exc}",
                status=response.status_code,
            ) from exc
