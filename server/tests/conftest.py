import pytest
from rest_framework.test import APIClient

from accounts.lockout import lockout_store


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def django_db(db):
    return db


@pytest.fixture(autouse=True)
def _isolate_lockout():
    lockout_store.clear()
    yield


@pytest.fixture(autouse=True)
def _fast_throttle(settings):
    settings.REST_FRAMEWORK = {
        "DEFAULT_AUTHENTICATION_CLASSES": [
            "rest_framework.authentication.TokenAuthentication",
        ],
        "DEFAULT_PERMISSION_CLASSES": [
            "rest_framework.permissions.IsAuthenticated",
        ],
        "DEFAULT_THROTTLE_RATES": {"login": "1000/min"},
        "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    }
