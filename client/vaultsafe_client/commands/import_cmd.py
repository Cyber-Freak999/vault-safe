from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from .. import cli, export


def register(subparsers: Any) -> None:
    p = subparsers.add_parser("import", help="restore from an encrypted backup")
    p.add_argument("path", help="backup file path")
    p.add_argument("--overwrite", action="store_true", help="update items that already exist")
    p.add_argument("--vault-name", default=None, help="target vault name override")
    p.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    config = cli.load_config(args.config)
    client = cli.login(config)
    try:
        bundle = export.import_bundle(Path(args.path).read_bytes(), client.current_kek())
    except (export.ExportError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    vault_id = _find_or_create_vault(client, args.vault_name or bundle.vault_name)
    existing = {str(item["service"]).casefold(): item for item in client.list_items(vault_id)}
    created = updated = skipped = 0
    for item in bundle.items:
        prior = existing.get(item.service.casefold())
        if prior is None:
            client.create_item(vault_id, item.service, item.secrets, tags=list(item.tags))
            created += 1
        elif args.overwrite:
            client.update_item(
                int(prior["id"]),
                service=item.service,
                secret_fields=dict(item.secrets),
                tags=list(item.tags),
            )
            updated += 1
        else:
            skipped += 1
    print(
        f"imported into vault {vault_id}: {created} created, {updated} updated, {skipped} skipped"
    )
    return 0


def _find_or_create_vault(client: Any, name: str) -> int:
    for vault in client.list_vaults():
        if str(vault["name"]).casefold() == name.casefold():
            return int(vault["id"])
    return int(client.create_vault(name)["id"])
