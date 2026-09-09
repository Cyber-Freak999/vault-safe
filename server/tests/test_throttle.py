from rest_framework.throttling import SimpleRateThrottle


def test_login_throttle_returns_429(api_client, django_db):
    original_rates = SimpleRateThrottle.THROTTLE_RATES
    SimpleRateThrottle.THROTTLE_RATES = {**original_rates, "login": "3/min"}
    try:
        for _ in range(3):
            api_client.post(
                "/api/auth/login", {"username": "ghost", "verifier": "Ym9nb3Vz"}, format="json"
            )
        res = api_client.post(
            "/api/auth/login", {"username": "ghost", "verifier": "Ym9nb3Vz"}, format="json"
        )
        assert res.status_code == 429
    finally:
        SimpleRateThrottle.THROTTLE_RATES = original_rates
