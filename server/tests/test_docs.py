from tests.test_vaults import _register


def test_schema_generates(api_client, django_db):
    _register(api_client, "alice")
    res = api_client.get("/api/schema", HTTP_ACCEPT="application/vnd.oai.openapi+json")
    assert res.status_code == 200
    assert res.json()["openapi"].startswith("3.0")


def test_swagger_ui_serves(api_client, django_db):
    _register(api_client, "alice")
    res = api_client.get("/api/docs")
    assert res.status_code == 200
    assert "swagger" in res.content.decode().lower()
