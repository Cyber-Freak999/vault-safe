import base64
import json

import httpx
import pytest

from vaultsafe_client.client import VaultApiError, VaultClient
from vaultsafe_client.kdf import KdfParams, derive_kek

FAST = KdfParams(memory_kib=8, iterations=1, parallelism=1)


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _challenge() -> dict:
    return {
        "kdf_salt": _b64(b"a" * 16),
        "verifier_salt": _b64(b"c" * 16),
        "kdf_params": FAST.to_dict(),
    }


def _make_client(handler) -> VaultClient:
    return VaultClient(
        "http://testserver",
        transport=httpx.MockTransport(handler),
    )


def test_login_sets_token_and_kek():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth/preauth":
            return httpx.Response(200, json=_challenge())
        if request.url.path == "/api/auth/login":
            assert "verifier" in json.loads(request.content)
            return httpx.Response(200, json={"token": "tok123"})
        raise AssertionError(f"unexpected {request.method} {request.url.path}")

    client = _make_client(handler)
    client.login("alice", "hunter2")
    assert client._token == "tok123"
    assert client._kek == derive_kek("hunter2", b"a" * 16, FAST)


def test_authed_requests_send_token_header():
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth/preauth":
            return httpx.Response(200, json=_challenge())
        if request.url.path == "/api/auth/login":
            return httpx.Response(200, json={"token": "tok123"})
        if request.url.path == "/api/me":
            seen["auth"] = request.headers.get("Authorization", "")
            return httpx.Response(200, json={"username": "alice"})
        raise AssertionError(f"unexpected {request.method} {request.url.path}")

    client = _make_client(handler)
    client.login("alice", "hunter2")
    assert client.me() == {"username": "alice"}
    assert seen["auth"] == "Token tok123"


def test_api_error_surfaces_code_and_message():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth/preauth":
            return httpx.Response(200, json=_challenge())
        if request.url.path == "/api/auth/login":
            return httpx.Response(
                400,
                json={"error": {"code": "invalid_credentials", "message": "nope"}},
            )
        raise AssertionError(f"unexpected {request.method} {request.url.path}")

    client = _make_client(handler)
    with pytest.raises(VaultApiError) as exc:
        client.login("alice", "wrong")
    assert exc.value.code == "invalid_credentials"
    assert exc.value.status == 400


def test_create_item_and_get_secret_round_trip():
    stored: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth/preauth":
            return httpx.Response(200, json=_challenge())
        if request.url.path == "/api/auth/login":
            return httpx.Response(200, json={"token": "tok123"})
        if request.method == "POST" and request.url.path == "/api/vaults/1/items":
            body = json.loads(request.content)
            stored.update(body)
            return httpx.Response(
                201,
                json={
                    "id": 7,
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-01T00:00:00Z",
                    "last_accessed_at": None,
                    **body,
                },
            )
        if request.method == "GET" and request.url.path == "/api/items/7":
            return httpx.Response(200, json=stored)
        raise AssertionError(f"unexpected {request.method} {request.url.path}")

    client = _make_client(handler)
    client.login("alice", "master")
    client.create_item(1, "github", {"password": "s3cret"}, tags=["work"])
    assert stored["service"] == "github"
    assert stored["tags"] == ["work"]
    assert "ciphertext" in stored["envelope"]
    assert client.get_secret(7)["password"] == "s3cret"
    assert "s3cret" not in stored["envelope"]["ciphertext"]


def test_works_before_unlock_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth/preauth":
            return httpx.Response(200, json=_challenge())
        if request.url.path == "/api/auth/login":
            return httpx.Response(200, json={"token": "tok123"})
        raise AssertionError(f"unexpected {request.method} {request.url.path}")

    client = _make_client(handler)
    assert client._kek is None
    try:
        client.create_item(1, "github", {"password": "x"})
    except VaultApiError as exc:
        assert exc.code == "not_unlocked"
    else:
        raise AssertionError("expected not_unlocked error")
