from __future__ import annotations

from typing import Any

_COMMAND_REGISTERS: list[Any] = []


def register_all(subparsers: Any) -> None:
    for register in _COMMAND_REGISTERS:
        register(subparsers)


def _add_command(register: Any) -> None:
    _COMMAND_REGISTERS.append(register)
