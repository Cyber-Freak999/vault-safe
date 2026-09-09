from vaultsafe_client.envelope import Envelope, build_envelope, unseal_envelope
from vaultsafe_client.kdf import KdfParams, derive_kek

from tests.test_vaults import _register

FAST = KdfParams(memory_kib=8, iterations=1, parallelism=1)
KEK = derive_kek("master", b"a" * 16, FAST)


def _create_vault(api_client, name: str = "personal") -> int:
    res = api_client.post("/api/vaults", {"name": name}, format="json")
    assert res.status_code == 201, res.content
    return res.json()["id"]


def _envelope(secret: dict) -> dict:
    return build_envelope(secret, KEK).to_dict()


def test_create_item_round_trips_envelope(api_client, django_db):
    _register(api_client, "alice")
    vault_id = _create_vault(api_client)
    res = api_client.post(
        f"/api/vaults/{vault_id}/items",
        {
            "vault": vault_id,
            "service": "github",
            "tags": ["work"],
            "envelope": _envelope({"password": "s3cret", "username": "alice"}),
        },
        format="json",
    )
    assert res.status_code == 201, res.content
    body = res.json()
    assert body["service"] == "github"
    assert body["tags"] == ["work"]
    assert body["envelope"]["version"] == 1


def test_list_items_searches_by_service_and_tag(api_client, django_db):
    _register(api_client, "alice")
    vault_id = _create_vault(api_client)
    for service, tags in [("github", ["work"]), ("gitlab", ["work"]), ("bank", ["personal"])]:
        api_client.post(
            f"/api/vaults/{vault_id}/items",
            {
                "vault": vault_id,
                "service": service,
                "tags": tags,
                "envelope": _envelope({"password": "x"}),
            },
            format="json",
        )
    res = api_client.get(f"/api/vaults/{vault_id}/items")
    assert len(res.json()) == 3
    assert [i["service"] for i in res.json()] == ["bank", "github", "gitlab"]
    res = api_client.get(f"/api/vaults/{vault_id}/items", {"service": "git"})
    assert {i["service"] for i in res.json()} == {"github", "gitlab"}
    res = api_client.get(f"/api/vaults/{vault_id}/items", {"tag": "work"})
    assert {i["service"] for i in res.json()} == {"github", "gitlab"}


def test_create_item_rejects_bad_envelope_version(api_client, django_db):
    _register(api_client, "alice")
    vault_id = _create_vault(api_client)
    envelope = _envelope({"password": "x"})
    envelope["version"] = 999
    res = api_client.post(
        f"/api/vaults/{vault_id}/items",
        {"vault": vault_id, "service": "github", "tags": [], "envelope": envelope},
        format="json",
    )
    assert res.status_code == 400


def test_create_item_rejects_malformed_envelope(api_client, django_db):
    _register(api_client, "alice")
    vault_id = _create_vault(api_client)
    res = api_client.post(
        f"/api/vaults/{vault_id}/items",
        {
            "vault": vault_id,
            "service": "github",
            "tags": [],
            "envelope": {"version": 1, "nonce_c": "!!!"},
        },
        format="json",
    )
    assert res.status_code == 400


def test_item_write_to_foreign_vault_is_404(api_client, django_db):
    _register(api_client, "alice")
    vault_id = _create_vault(api_client)
    _register(api_client, "bob")
    res = api_client.post(
        f"/api/vaults/{vault_id}/items",
        {
            "vault": vault_id,
            "service": "github",
            "tags": [],
            "envelope": _envelope({"password": "x"}),
        },
        format="json",
    )
    assert res.status_code == 404


def test_get_item_returns_envelope(api_client, django_db):
    _register(api_client, "alice")
    vault_id = _create_vault(api_client)
    item_id = api_client.post(
        f"/api/vaults/{vault_id}/items",
        {
            "vault": vault_id,
            "service": "github",
            "tags": ["work"],
            "envelope": _envelope({"password": "s3cret"}),
        },
        format="json",
    ).json()["id"]
    res = api_client.get(f"/api/items/{item_id}")
    assert res.status_code == 200
    body = res.json()
    assert body["envelope"]["version"] == 1
    secret = unseal_envelope(Envelope.from_dict(body["envelope"]), KEK)
    assert secret["password"] == "s3cret"


def test_update_item_replaces_service_and_envelope(api_client, django_db):
    _register(api_client, "alice")
    vault_id = _create_vault(api_client)
    item_id = api_client.post(
        f"/api/vaults/{vault_id}/items",
        {
            "vault": vault_id,
            "service": "github",
            "tags": [],
            "envelope": _envelope({"password": "old"}),
        },
        format="json",
    ).json()["id"]
    res = api_client.patch(
        f"/api/items/{item_id}",
        {"service": "gitlab", "envelope": _envelope({"password": "new"})},
        format="json",
    )
    assert res.status_code == 200
    body = res.json()
    assert body["service"] == "gitlab"
    assert unseal_envelope(Envelope.from_dict(body["envelope"]), KEK)["password"] == "new"


def test_delete_item(api_client, django_db):
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
    assert api_client.delete(f"/api/items/{item_id}").status_code == 204
    assert api_client.get(f"/api/items/{item_id}").status_code == 404


def test_item_detail_is_owner_scoped(api_client, django_db):
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
    _register(api_client, "bob")
    assert api_client.get(f"/api/items/{item_id}").status_code == 404
    res = api_client.patch(f"/api/items/{item_id}", {"service": "x"}, format="json")
    assert res.status_code == 404
    assert api_client.delete(f"/api/items/{item_id}").status_code == 404
