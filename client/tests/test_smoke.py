def test_workspace_imports_resolve():
    import vaultsafe_client

    assert vaultsafe_client.__name__ == "vaultsafe_client"
