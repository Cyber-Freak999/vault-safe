# client/vaultsafe_client/commands/__init__.py
from __future__ import annotations

from typing import Any

from . import add, gen, get, init, ls, rm, unlock

_COMMAND_REGISTERS: list[Any] = []


def register_all(subparsers: Any) -> None:
    for register in _COMMAND_REGISTERS:
        register(subparsers)


def _add_command(register: Any) -> None:
    _COMMAND_REGISTERS.append(register)


_add_command(add.register)
_add_command(gen.register)
_add_command(get.register)
_add_command(init.register)
_add_command(ls.register)
_add_command(rm.register)
_add_command(unlock.register)
