from accounts.lockout import LockoutStore


def test_clear_resets_everything():
    store = LockoutStore(max_failures=2, lockout_seconds=300)
    store.record_failure("alice")
    store.clear()
    assert store.is_locked("alice") is False


def test_lockout_after_max_failures_on_any_key():
    store = LockoutStore(max_failures=3, lockout_seconds=300)
    assert store.is_locked("alice", "127.0.0.1") is False
    store.record_failure("alice", "127.0.0.1")
    store.record_failure("alice", "127.0.0.1")
    store.record_failure("alice", "127.0.0.1")
    assert store.is_locked("alice", "127.0.0.1") is True
    assert store.is_locked("127.0.0.1", "bob") is True  # IP alone triggers
    assert store.is_locked("bob", "10.0.0.9") is False


def test_reset_clears_key():
    store = LockoutStore(max_failures=2, lockout_seconds=300)
    store.record_failure("alice", "10.0.0.1")
    store.record_failure("alice", "10.0.0.1")
    assert store.is_locked("alice") is True
    store.reset("alice")
    assert store.is_locked("alice") is False
    assert store.is_locked("10.0.0.1") is True
