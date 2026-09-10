from __future__ import annotations

import argparse
import sys
from typing import Any

from .. import cli


def register(subparsers: Any) -> None:
    p = subparsers.add_parser("rm", help="delete an item")
    p.add_argument("service", help="service name")
    p.add_argument("-y", "--yes", action="store_true", help="skip confirmation")
    p.add_argument("--vault", type=int, default=None, help="vault id override")
    p.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    config = cli.load_config(args.config)
    client = cli.login(config)
    vault_id = cli.resolve_vault(config, client, args.config, explicit=args.vault)
    matches = cli.find_items(client, vault_id, args.service)
    if not matches:
        print(f"error: no item matching {args.service!r}", file=sys.stderr)
        return 1
    if len(matches) > 1:
        names = ", ".join(sorted(str(m["service"]) for m in matches))
        print(f"error: multiple matches: {names}", file=sys.stderr)
        return 1
    item = matches[0]
    if not args.yes:
        answer = input(f"delete {item['service']}? [y/N]: ").strip().lower()
        if answer not in ("y", "yes"):
            print("aborted")
            return 0
    client.delete_item(int(item["id"]))
    print("deleted")
    return 0
