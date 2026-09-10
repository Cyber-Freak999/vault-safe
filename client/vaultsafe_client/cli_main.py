from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import cast

from . import commands
from .client import VaultApiError
from .config import ConfigError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vs",
        description="VaultSafe zero-knowledge password CLI",
    )
    parser.add_argument("--config", type=Path, default=None, help="config file path")
    sub = parser.add_subparsers(dest="command", required=True)
    commands.register_all(sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        return cast(int, args.handler(args))
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except VaultApiError as exc:
        print(f"error: {exc.message}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("aborted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
