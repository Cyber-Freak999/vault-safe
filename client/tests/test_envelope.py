import pytest
from cryptography.exceptions import InvalidTag

from vaultsafe_client.envelope import (
    Envelope,
    EnvelopeError,
    UnsupportedEnvelopeVersion,
    build_envelope,
    unseal_envelope,
)
from vaultsafe_client.kdf import KdfParams, derive_kek

FAST = KdfParams(memory_kib=8, iterations=1, parallelism=1)
KEK = derive_kek("master-password", b"a" * 16, FAST)


def test_round_trip():
    fields = {"password": "s3cret", "username": "alice", "notes": "github"}
    env = build_envelope(fields, KEK)
    assert unseal_envelope(env, KEK) == fields


def test_wrong_key_fails():
    env = build_envelope({"password": "x"}, KEK)
    other = derive_kek("other-password", b"a" * 16, FAST)
    with pytest.raises(InvalidTag):
        unseal_envelope(env, other)


def test_tampered_ciphertext_fails():
    env = build_envelope({"password": "x"}, KEK)
    mut = bytes([env.ciphertext[0] ^ 0xFF]) + env.ciphertext[1:]
    tampered = Envelope(env.version, env.nonce_c, mut, env.nonce_k, env.wrapped_key)
    with pytest.raises(InvalidTag):
        unseal_envelope(tampered, KEK)


def test_tampered_wrapped_key_fails():
    env = build_envelope({"password": "x"}, KEK)
    tampered = Envelope(env.version, env.nonce_c, env.ciphertext, env.nonce_k, b"\x00" * 48)
    with pytest.raises(InvalidTag):
        unseal_envelope(tampered, KEK)


def test_to_dict_from_dict_round_trip():
    env = build_envelope({"password": "x", "username": "y"}, KEK)
    restored = Envelope.from_dict(env.to_dict())
    assert restored == env
    assert unseal_envelope(restored, KEK) == {"password": "x", "username": "y"}


def test_unknown_version_rejected():
    env = build_envelope({"password": "x"}, KEK)
    data = env.to_dict()
    data["version"] = 999
    with pytest.raises(UnsupportedEnvelopeVersion):
        Envelope.from_dict(data)


def test_malformed_envelope_rejected():
    with pytest.raises(EnvelopeError):
        Envelope.from_dict({})
    with pytest.raises(EnvelopeError):
        Envelope.from_dict({"version": 1, "nonce_c": "!!!"})


def test_serialized_dict_has_no_plaintext():
    fields = {"password": "plaintext-value-123"}
    data = Envelope.from_dict(build_envelope(fields, KEK).to_dict()).to_dict()
    assert "plaintext-value-123" not in data["ciphertext"]
