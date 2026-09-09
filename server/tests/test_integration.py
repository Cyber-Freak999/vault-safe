import pytest
from vaultsafe_client import VaultApiError, VaultClient
from vaultsafe_client.kdf import KdfParams

FAST = KdfParams(memory_cost=8, iterations=1, parallelism=1)
SECRET_STATIC_PASSWORD = "correct horse battery staple"


@pytest.mark.django_db
def test_zero_knowledge_end_to_end(live_server):
    client = VaultClient(live_server.url)
    client.register("alice", "master-pw", params=FAST)
    client.login("alice", "master-pw")

    vault = client.create_vault("personal")
    assert vault["id"]

    item = client.create_item(
        vault["id"],
        "github",
        {"username": "alice", "password": "s3cret-value"},
        tags=["work"],
    )
    assert item["id"]

    assert client.get_secret(item["id"]) == {
        "username": "alice",
        "password": "s3cret-value",
    }

    found = client.list_items(vault_id=vault["id"], tag="work")
    assert len(found) == 1
    assert found[0]["service"] == "github"

    updated = client.update_item(item["id"], service="gitlab")
    assert updated["service"] == "gitlab"


@pytest.mark.django_db
def test_server_receives_no_plaintext(live_server):
    client = VaultClient(live_server.url)
    client.register("bob", "master-pw", params=FAST)
    client.login("bob", "master-pw")
    vault = client.create_vault("v")
    item = client.create_item(vault["id"], "github", {"password": "ultra-secret-42"}, tags=[])
    raw = client.get_item(item["id"])
    assert "ultra-secret-42" not in repr(raw)
    assert "ultra-secret-42" not in raw["envelope"]["ciphertext"]


@pytest.mark.django_db
def test_wrong_password_cannot_login(live_server):
    client = VaultClient(live_server.url)
    client.register("carol", "right-pw", params=FAST)
    with pytest.raises(VaultApiError) as exc:
        VaultClient(live_server.url).login("carol", "wrong-pw")
    assert exc.value.code == "invalid_credentials"
