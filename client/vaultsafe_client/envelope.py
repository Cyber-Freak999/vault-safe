from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any, cast

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ENVELOPE_VERSION = 1
_NONCE_BYTES = 12


class EnvelopeError(ValueError):
    pass


class UnsupportedEnvelopeVersion(EnvelopeError):
    pass


@dataclass(frozen=True)
class Envelope:
    version: int
    nonce_c: bytes
    ciphertext: bytes
    nonce_k: bytes
    wrapped_key: bytes

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "nonce_c": base64.b64encode(self.nonce_c).decode("ascii"),
            "ciphertext": base64.b64encode(self.ciphertext).decode("ascii"),
            "nonce_k": base64.b64encode(self.nonce_k).decode("ascii"),
            "wrapped_key": base64.b64encode(self.wrapped_key).decode("ascii"),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Envelope:
        if not isinstance(data, dict):
            raise EnvelopeError("envelope must be a dictionary")
        version = data.get("version")
        if version != ENVELOPE_VERSION:
            raise UnsupportedEnvelopeVersion(f"unsupported envelope version: {version!r}")
        try:
            return cls(
                version=ENVELOPE_VERSION,
                nonce_c=base64.b64decode(cast(str, data["nonce_c"]), validate=True),
                ciphertext=base64.b64decode(cast(str, data["ciphertext"]), validate=True),
                nonce_k=base64.b64decode(cast(str, data["nonce_k"]), validate=True),
                wrapped_key=base64.b64decode(cast(str, data["wrapped_key"]), validate=True),
            )
        except KeyError as exc:
            raise EnvelopeError(f"missing envelope field: {exc.args[0]}") from exc
        except ValueError as exc:
            raise EnvelopeError("envelope contains invalid base64") from exc


def build_envelope(secret_fields: dict[str, str], kek: bytes) -> Envelope:
    dek = AESGCM.generate_key(bit_length=256)
    nonce_k = os.urandom(_NONCE_BYTES)
    wrapped_key = AESGCM(kek).encrypt(nonce_k, dek, None)
    nonce_c = os.urandom(_NONCE_BYTES)
    payload = json.dumps(secret_fields, sort_keys=True).encode("utf-8")
    ciphertext = AESGCM(dek).encrypt(nonce_c, payload, None)
    return Envelope(
        version=ENVELOPE_VERSION,
        nonce_c=nonce_c,
        ciphertext=ciphertext,
        nonce_k=nonce_k,
        wrapped_key=wrapped_key,
    )


def unseal_envelope(envelope: Envelope, kek: bytes) -> dict[str, str]:
    dek = AESGCM(kek).decrypt(envelope.nonce_k, envelope.wrapped_key, None)
    payload = AESGCM(dek).decrypt(envelope.nonce_c, envelope.ciphertext, None)
    return cast(dict[str, str], json.loads(payload.decode("utf-8")))
