from __future__ import annotations

import os
from dataclasses import dataclass
from typing import cast

from argon2 import low_level as _argon2


class KdfParamsError(ValueError):
    pass


@dataclass(frozen=True)
class KdfParams:
    memory_kib: int = 65536
    iterations: int = 3
    parallelism: int = 4
    hash_len: int = 32

    def to_dict(self) -> dict[str, int]:
        return {
            "memory_kib": self.memory_kib,
            "iterations": self.iterations,
            "parallelism": self.parallelism,
            "hash_len": self.hash_len,
        }

    @classmethod
    def from_dict(cls: type[KdfParams], data: dict[str, object]) -> KdfParams:
        required = ("memory_kib", "iterations", "parallelism", "hash_len")
        if not all(isinstance(data.get(k), int) for k in required):
            raise KdfParamsError(f"missing or invalid kdf params, expected {required}")
        return cls(**{k: cast(int, data[k]) for k in required})


DefaultParams = KdfParams()


def generate_salt(size: int = 16) -> bytes:
    return os.urandom(size)


def derive_kek(password: str, salt: bytes, params: KdfParams) -> bytes:
    return _argon2.hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt,
        time_cost=params.iterations,
        memory_cost=params.memory_kib,
        parallelism=params.parallelism,
        hash_len=params.hash_len,
        type=_argon2.Type.ID,
    )


def derive_verifier(kek: bytes, salt: bytes, params: KdfParams) -> bytes:
    return _argon2.hash_secret_raw(
        secret=kek,
        salt=salt,
        time_cost=params.iterations,
        memory_cost=params.memory_kib,
        parallelism=params.parallelism,
        hash_len=params.hash_len,
        type=_argon2.Type.ID,
    )
