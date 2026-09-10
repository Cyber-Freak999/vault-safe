from __future__ import annotations

import secrets
import string

MIN_LENGTH = 8
MAX_LENGTH = 128
_GROUPS = (string.ascii_lowercase, string.ascii_uppercase, string.digits, string.punctuation)
_ALPHABET = string.ascii_letters + string.digits + string.punctuation


def generate_password(length: int = 20) -> str:
    if not MIN_LENGTH <= length <= MAX_LENGTH:
        raise ValueError(f"length must be between {MIN_LENGTH} and {MAX_LENGTH}")
    chars = [secrets.choice(group) for group in _GROUPS]
    chars += [secrets.choice(_ALPHABET) for _ in range(length - len(chars))]
    return "".join(_shuffle(chars))


def _shuffle(chars: list[str]) -> list[str]:
    for i in range(len(chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        chars[i], chars[j] = chars[j], chars[i]
    return chars
