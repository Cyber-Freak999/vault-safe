from __future__ import annotations

import argparse
from typing import Any

from .. import cli


def register(subparsers: Any) -> None:
    p = subparsers.add_parser("ls", help="list stored services")
    p.add_argument("query", nargs="?", default=None, help="filter by service substring")
    p.add_argument("-t", "--tag", default=None, help="filter by tag")
    p.add_argument("--vault", type=int, default=None, help="vault id override")
    p.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    config = cli.load_config(args.config)
    client = cli.login(config)
    vault_id = cli.resolve_vault(config, client, args.config, explicit=args.vault)
    items = client.list_items(vault_id, service=args.query, tag=args.tag)
    for item in items:
        tags = ",".join(item.get("tags", []))
        print(f"{item['id']}\t{item['service']}\t{tags}")
    return 0
