from __future__ import annotations

import argparse
from typing import Any

from ..client import VaultClient
from ..config import Config, default_config_path


def register(subparsers: Any) -> None:
    p = subparsers.add_parser("init", help="create config and verify server reachability")
    p.add_argument("--url", default="http://127.0.0.1:8000", help="server base URL")
    p.add_argument("--username", required=True, help="your username")
    p.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    config = Config(base_url=args.url.rstrip("/"), username=args.username)
    client = VaultClient(args.url)
    client.health()
    path = getattr(args, "config", None) or default_config_path()
    config.save(path)
    print(f"config written to {path}")
    return 0
