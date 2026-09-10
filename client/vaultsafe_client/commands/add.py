from __future__ import annotations

import argparse
import getpass
import sys
from typing import Any

from .. import cli, clipboard, generator


def register(subparsers: Any) -> None:
    p = subparsers.add_parser("add", help="store a new item")
    p.add_argument("service", help="service name")
    p.add_argument("-t", "--tag", action="append", default=[], help="tag (repeatable)")
    p.add_argument("--ask", action="store_true", help="prompt for password instead of generating")
    p.add_argument("--vault", type=int, default=None, help="vault id override")
    p.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    config = cli.load_config(args.config)
    client = cli.login(config)
    vault_id = cli.resolve_vault(config, client, args.config, explicit=args.vault)
    if args.ask:
        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm: ")
        if password != confirm:
            print("error: passwords do not match", file=sys.stderr)
            return 1
    else:
        password = generator.generate_password()
        tool = clipboard.copy_to_clipboard(password)
        if tool is None:
            print(f"warning: could not copy; password: {password}", file=sys.stderr)
        else:
            print("generated password copied to clipboard")
    client.create_item(vault_id, args.service, {"password": password}, tags=list(args.tag))
    print(f"stored {args.service}")
    return 0
