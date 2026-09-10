from __future__ import annotations

import pytest

from vaultsafe_client.export import (
    Bundle,
    BundleItem,
    ExportError,
    collect_bundle,
    export_bundle,
    import_bundle,
)

CEK = bytes(range(32))


def test_round_trip():
    bundle = Bundle("personal", [BundleItem("github", ["work"], {"password": "s3cret!"})])
    data = export_bundle(bundle, CEK)
    assert import_bundle(data, CEK) == bundle


def test_round_trip_empty():
    bundle = Bundle("v", [])
    assert import_bundle(export_bundle(bundle, CEK), CEK) == bundle


def test_wrong_kek_rejected():
    data = export_bundle(Bundle("v", []), CEK)
    with pytest.raises(ExportError):
        import_bundle(data, bytes(range(32, 64)))


def test_tampered_rejected():
    data = bytearray(export_bundle(Bundle("v", [BundleItem("x", [], {"p": "y"})]), CEK))
    data[40] ^= 0xFF
    with pytest.raises(ExportError):
        import_bundle(bytes(data), CEK)


def test_garbage_json_rejected():
    with pytest.raises(ExportError):
        import_bundle(b"not json at all", CEK)


class FakeClient:
    def __init__(self) -> None:
        self.secret = {"password": "s3cret!"}

    def list_vaults(self) -> list[dict]:
        return [{"id": 1, "name": "personal"}]

    def list_items(self, vault_id: int, *, service=None, tag=None) -> list[dict]:
        return [{"id": 7, "service": "github", "tags": ["work"]}]

    def get_secret(self, item_id) -> dict[str, str]:
        return dict(self.secret)


def test_collect_bundle():
    bundle = collect_bundle(FakeClient(), 1)
    assert bundle.vault_name == "personal"
    assert bundle.items == [BundleItem("github", ["work"], {"password": "s3cret!"})]
