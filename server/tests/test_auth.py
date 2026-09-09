import base64

from vaultsafe_client.kdf import KdfParams, derive_kek, derive_verifier

FAST = KdfParams(memory_kib=8, iterations=1, parallelism=1)


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _register_payload(
    username: str = "alice", password: str = "correct horse battery staple"
) -> dict:
    kdf_salt = b"a" * 16
    verifier_salt = b"b" * 16
    kek = derive_kek(password, kdf_salt, FAST)
    verifier = derive_verifier(kek, verifier_salt, FAST)
    return {
        "username": username,
        "kdf_salt": _b64(kdf_salt),
        "verifier_salt": _b64(verifier_salt),
        "verifier": _b64(verifier),
        "kdf_params": FAST.to_dict(),
    }


def test_register_creates_user_and_profile(api_client, django_db):
    res = api_client.post("/api/auth/register", _register_payload(), format="json")
    assert res.status_code == 201
    assert res.json()["username"] == "alice"


def test_register_rejects_duplicate_username(api_client, django_db):
    api_client.post("/api/auth/register", _register_payload(), format="json")
    res = api_client.post("/api/auth/register", _register_payload(), format="json")
    assert res.status_code == 400


def test_register_rejects_bad_base64(api_client, django_db):
    payload = _register_payload()
    payload["verifier"] = "!!!not-base64!!!"
    res = api_client.post("/api/auth/register", payload, format="json")
    assert res.status_code == 400


def test_register_stores_no_plaintext_password(api_client, django_db):
    from django.contrib.auth.models import User

    api_client.post("/api/auth/register", _register_payload(), format="json")
    user = User.objects.get(username="alice")
    assert user.has_usable_password() is False
