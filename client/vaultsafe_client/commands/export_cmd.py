# client/vaultsafe_client/commands/export_cmd.py
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .. import cli, export


def register(subparsers: Any) -> None:
    p = subparsers.add_parser("export", help="write an encrypted backup")
    p.add_argument("path", nargs="?", default=None, help="output file path")
    p.add_argument("--vault", type=int, default=None, help="vault id override")
    p.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    config = cli.load_config(args.config)
    client = cli.login(config)
    vault_id = cli.resolve_vault(config, client, args.config, explicit=args.vault)
    try:
        bundle = export.collect_bundle(client, vault_id)
        data = export.export_bundle(bundle, client.current_kek())
    except export.ExportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    path = Path(args.path) if args.path else default_path(bundle.vault_name)
    path.write_bytes(data)
    print(f"backup written to {path}")
    return 0


def default_path(vault_name: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path(f"vaultsafe-backup-{vault_name}-{stamp}.json")
