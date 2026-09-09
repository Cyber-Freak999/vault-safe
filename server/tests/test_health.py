def test_health_public(api_client, django_db):
    res = api_client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
