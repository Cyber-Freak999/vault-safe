from __future__ import annotations

import argparse
import sys
from typing import Any

from .. import cli, clipboard


def register(subparsers: Any) -> None:
    p = subparsers.add_parser("get", help="retrieve and copy a password")
    p.add_argument("service", help="service name")
    p.add_argument("--show", action="store_true", help="print instead of copying")
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
    secret = client.get_secret(int(item["id"]))
    password = secret["password"]
    if args.show:
        print(password)
        return 0
    tool = clipboard.copy_to_clipboard(password)
    if tool is None:
        print("error: no clipboard tool found", file=sys.stderr)
        return 1
    print("copied to clipboard")
    return 0
