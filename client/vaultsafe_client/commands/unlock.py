from __future__ import annotations

import argparse
from typing import Any

from .. import cli


def register(subparsers: Any) -> None:
    p = subparsers.add_parser("unlock", help="verify master password")
    p.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    config = cli.load_config(args.config)
    cli.login(config)
    print("unlocked")
    return 0
