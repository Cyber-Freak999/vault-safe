from __future__ import annotations

import argparse
from typing import Any

from .. import generator


def register(subparsers: Any) -> None:
    p = subparsers.add_parser("gen", help="generate a password")
    p.add_argument("length", nargs="?", type=int, default=20, help="password length")
    p.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    print(generator.generate_password(args.length))
    return 0
