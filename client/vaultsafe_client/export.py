from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

from cryptography.exceptions import InvalidTag

from .client import VaultClient
from .envelope import Envelope, EnvelopeError, build_envelope, unseal_envelope

DOC_FORMAT = "vaultsafe-backup"
DOC_VERSION = 1


class ExportError(ValueError):
    pass


@dataclass(frozen=True)
class BundleItem:
    service: str
    tags: list[str]
    secrets: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return {"service": self.service, "tags": self.tags, "secrets": self.secrets}

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> BundleItem:
        service = data.get("service")
        tags = data.get("tags", [])
        secrets = data.get("secrets")
        if not isinstance(service, str):
            raise ExportError("backup item missing 'service'")
        if not isinstance(tags, list):
            raise ExportError("backup item 'tags' must be a list")
        if not isinstance(secrets, dict):
            raise ExportError("backup item missing 'secrets'")
        return cls(
            service=service,
            tags=[str(t) for t in tags],
            secrets={str(k): str(v) for k, v in secrets.items()},
        )


@dataclass(frozen=True)
class Bundle:
    vault_name: str
    items: list[BundleItem]

    def to_dict(self) -> dict[str, object]:
        return {"vault_name": self.vault_name, "items": [i.to_dict() for i in self.items]}

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Bundle:
        vault_name = data.get("vault_name")
        items = data.get("items")
        if not isinstance(vault_name, str):
            raise ExportError("backup missing 'vault_name'")
        if not isinstance(items, list):
            raise ExportError("backup missing 'items'")
        parsed = [BundleItem.from_dict(cast(dict[str, object], entry)) for entry in items]
        return cls(vault_name=vault_name, items=parsed)


def collect_bundle(client: VaultClient, vault_id: int, vault_name: str | None = None) -> Bundle:
    if vault_name is None:
        vault_name = "vault"
        for vault in [dict(v) for v in client.list_vaults()]:
            if vault["id"] == vault_id:
                vault_name = str(vault["name"])
                break
    items = [
        BundleItem(
            service=str(item["service"]),
            tags=[str(t) for t in item.get("tags", [])],
            secrets=dict(client.get_secret(int(item["id"]))),
        )
        for item in client.list_items(vault_id)
    ]
    return Bundle(vault_name=vault_name, items=items)


def export_bundle(bundle: Bundle, kek: bytes) -> bytes:
    envelope = build_envelope(
        {
            "format": DOC_FORMAT,
            "version": str(DOC_VERSION),
            "created": datetime.now(UTC).isoformat(),
            "vault_name": bundle.vault_name,
            "items": json.dumps([i.to_dict() for i in bundle.items], sort_keys=True),
        },
        kek,
    )
    header = {"format": DOC_FORMAT, "version": DOC_VERSION, "envelope": envelope.to_dict()}
    return json.dumps(header, sort_keys=True).encode("utf-8")


def import_bundle(data: bytes, kek: bytes) -> Bundle:
    try:
        header = cast(dict[str, Any], json.loads(data.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExportError("backup is not valid JSON") from exc
    if header.get("format") != DOC_FORMAT or header.get("version") != DOC_VERSION:
        raise ExportError("unsupported backup format or version")
    try:
        envelope = Envelope.from_dict(cast(dict[str, object], header["envelope"]))
        fields = unseal_envelope(envelope, kek)
    except (EnvelopeError, InvalidTag) as exc:
        raise ExportError("wrong master password or corrupt backup") from exc
    try:
        items = [
            BundleItem.from_dict(cast(dict[str, object], d)) for d in json.loads(fields["items"])
        ]
    except (json.JSONDecodeError, ExportError) as exc:
        raise ExportError("backup contents are malformed") from exc
    return Bundle(vault_name=fields["vault_name"], items=items)
