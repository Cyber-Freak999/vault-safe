import base64

from vaultsafe_client.kdf import KdfParams, derive_kek, derive_verifier

FAST = KdfParams(memory_cost=8, iterations=1, parallelism=1)


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _register(api_client, username: str, password: str = "correct horse battery staple") -> str:
    kdf_salt = b"a" * 16
    verifier_salt = b"b" * 16
    kek = derive_kek(password, kdf_salt, FAST)
    verifier = derive_verifier(kek, verifier_salt, FAST)
    api_client.post(
        "/api/auth/register",
        {
            "username": username,
            "kdf_salt": _b64(kdf_salt),
            "verifier_salt": _b64(verifier_salt),
            "verifier": _b64(verifier),
            "kdf_params": FAST.to_dict(),
        },
        format="json",
    )
    token = api_client.post(
        "/api/auth/login",
        {"username": username, "verifier": _b64(verifier)},
        format="json",
    ).json()["token"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return token


def test_health_is_public(api_client, django_db):
    res = api_client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_vault_create_and_list(api_client, django_db):
    _register(api_client, "alice")
    res = api_client.post("/api/vaults", {"name": "personal"}, format="json")
    assert res.status_code == 201
    vault_id = res.json()["id"]
    listing = api_client.get("/api/vaults")
    assert listing.status_code == 200
    assert any(v["id"] == vault_id and v["name"] == "personal" for v in listing.json())


def test_vault_patch_and_delete(api_client, django_db):
    _register(api_client, "alice")
    vault_id = api_client.post("/api/vaults", {"name": "personal"}, format="json").json()["id"]
    res = api_client.patch(f"/api/vaults/{vault_id}", {"name": "work"}, format="json")
    assert res.status_code == 200
    assert res.json()["name"] == "work"
    assert api_client.delete(f"/api/vaults/{vault_id}").status_code == 204
    assert api_client.get(f"/api/vaults/{vault_id}").status_code == 404


def test_vaults_are_owner_scoped(api_client, django_db):
    _register(api_client, "alice")
    vault_id = api_client.post("/api/vaults", {"name": "private"}, format="json").json()["id"]
    _register(api_client, "bob")
    assert api_client.get("/api/vaults").json() == []
    assert api_client.get(f"/api/vaults/{vault_id}").status_code == 404
    assert (
        api_client.patch(f"/api/vaults/{vault_id}", {"name": "hax"}, format="json").status_code
        == 404
    )
    assert api_client.delete(f"/api/vaults/{vault_id}").status_code == 404
