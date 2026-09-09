def test_development_defaults_are_safe_for_localhost(settings):
    assert "rest_framework" in settings.INSTALLED_APPS
    assert "rest_framework.authtoken" in settings.INSTALLED_APPS
    assert "accounts" in settings.INSTALLED_APPS
    assert "vaults" in settings.INSTALLED_APPS
    assert "common" in settings.INSTALLED_APPS
    assert settings.DEBUG is True
    assert "localhost" in settings.ALLOWED_HOSTS
