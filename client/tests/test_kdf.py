import pytest

from vaultsafe_client.kdf import (
    DefaultParams,
    KdfParams,
    KdfParamsError,
    derive_kek,
    derive_verifier,
    generate_salt,
)

FAST = KdfParams(memory_cost=8, iterations=1, parallelism=1)


def test_default_params_reasonable_sizes():
    assert DefaultParams.memory_cost >= 64 * 1024
    assert DefaultParams.iterations >= 2


def test_derive_kek_is_deterministic_and_32_bytes():
    salt = b"a" * 16
    kek1 = derive_kek("correct horse", salt, FAST)
    kek2 = derive_kek("correct horse", salt, FAST)
    assert kek1 == kek2
    assert len(kek1) == FAST.hash_len


def test_derive_kek_differs_with_salt_or_password():
    salt = b"a" * 16
    base = derive_kek("password", salt, FAST)
    assert base != derive_kek("password", b"b" * 16, FAST)
    assert base != derive_kek("passwore", salt, FAST)


def test_derive_verifier_deterministic_and_32_bytes():
    kek = derive_kek("password", b"a" * 16, FAST)
    v1 = derive_verifier(kek, b"b" * 16, FAST)
    v2 = derive_verifier(kek, b"b" * 16, FAST)
    assert v1 == v2
    assert len(v1) == 32


def test_derive_verifier_differs_from_kek():
    kek = derive_kek("password", b"a" * 16, FAST)
    verifier = derive_verifier(kek, b"b" * 16, FAST)
    assert verifier != kek


def test_generate_salt_lengths():
    assert len(generate_salt()) == 16
    assert len(generate_salt(32)) == 32


def test_params_round_trip_and_validation():
    d = FAST.to_dict()
    assert KdfParams.from_dict(d) == FAST
    with pytest.raises(KdfParamsError):
        KdfParams.from_dict({"memory_cost": "lots"})
    with pytest.raises(KdfParamsError):
        KdfParams.from_dict({"iterations": 1})
