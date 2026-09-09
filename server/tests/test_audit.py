from tests.test_items import FAST, _create_vault, _envelope
from tests.test_vaults import _register


def _actions(api_client) -> list[str]:
    entries = api_client.get("/api/audit").json()
    return [e["action"] for e in entries]


def test_audit_records_registration_and_login(api_client, django_db):
    _register(api_client, "alice")
    assert "register" in _actions(api_client)
    assert "login" in _actions(api_client)


def test_audit_records_item_actions(api_client, django_db):
    _register(api_client, "alice")
    vault_id = _create_vault(api_client)
    item_id = api_client.post(
        f"/api/vaults/{vault_id}/items",
        {
            "vault": vault_id,
            "service": "github",
            "tags": [],
            "envelope": _envelope({"password": "x"}),
        },
        format="json",
    ).json()["id"]
    api_client.get(f"/api/items/{item_id}")
    api_client.patch(f"/api/items/{item_id}", {"service": "gitlab"}, format="json")
    api_client.delete(f"/api/items/{item_id}")
    actions = _actions(api_client)
    for expected in ("create_vault", "create_item", "read_item", "update_item", "delete_item"):
        assert expected in actions


def test_audit_is_owner_scoped(api_client, django_db):
    import base64

    from vaultsafe_client.kdf import derive_kek, derive_verifier

    _register(api_client, "alice")
    _register(api_client, "bob")
    api_client.credentials()
    kdf_salt = b"a" * 16
    verifier_salt = b"b" * 16
    kek = derive_kek("correct horse battery staple", kdf_salt, FAST)
    verifier = derive_verifier(kek, verifier_salt, FAST)
    token = api_client.post(
        "/api/auth/login",
        {"username": "bob", "verifier": base64.b64encode(verifier).decode()},
        format="json",
    ).json()["token"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    entries = api_client.get("/api/audit").json()
    assert entries  # bob has register + login entries of his own
    actions = {e["action"] for e in entries}
    assert {"register", "login"} <= actions
