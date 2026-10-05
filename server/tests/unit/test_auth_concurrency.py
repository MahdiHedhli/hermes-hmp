"""Concurrent bearer reads preserve synthetic actor binding; never uses a live home."""
from __future__ import annotations

import collections
import concurrent.futures
import hashlib
import sqlite3
import threading
from pathlib import Path
from typing import Any

import pytest

from hmp_plugin.auth import AuthContext, Authenticator
from hmp_plugin.contract import ErrorCode, HmpError
from hmp_plugin.store import Store
from hmp_plugin.wire import b64u_encode


def test_shared_connection_disables_cache_and_keeps_bearers_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_connect = sqlite3.connect
    options: list[dict[str, Any]] = []

    def connect(*args: Any, **kwargs: Any) -> sqlite3.Connection:
        options.append(dict(kwargs))
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", connect)
    store = Store(tmp_path / "synthetic.sqlite3")
    store.migrate()
    try:
        actors = [
            (AuthContext(device_id=f"synthetic-device-{i}", user_id=f"synthetic-user-{i}",
                         family_id=f"synthetic-family-{i}"), bytes([i]) * 32)
            for i in range(4)
        ]
        iid = "aaaaaaaaaaaaaaaaaaaaaaaaaa"
        auth = Authenticator(store, iid, lambda: 1000)
        for expected, token in actors:
            store.insert_user(expected.user_id, "synthetic", 1000)
            store.insert_device(expected.device_id, expected.user_id, "synthetic", b"synthetic",
                                "synthetic", 1000, state="ACTIVE")
            store.insert_token_family(expected.family_id, expected.device_id, 1000)
            store.insert_access_token(hashlib.sha256(token).digest(), expected.family_id,
                                      expected.device_id, iid, 2000)
            assert auth.authenticate("Bearer " + b64u_encode(token), iid) == expected

        barrier = threading.Barrier(16, timeout=10)

        def worker(index: int) -> collections.Counter[str]:
            expected, token = actors[index % 4]
            header = "Bearer " + b64u_encode(token)
            results: collections.Counter[str] = collections.Counter()
            barrier.wait()
            for _ in range(100):
                try:
                    actual = auth.authenticate(header, iid)
                    results["correct" if actual == expected else "wrong_context"] += 1
                except Exception as error:
                    results[type(error).__name__] += 1
            return results

        total: collections.Counter[str] = collections.Counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            for result in pool.map(worker, range(16)):
                total.update(result)
        assert options == [{"isolation_level": None, "check_same_thread": False,
                            "cached_statements": 0}]
        assert total == {"correct": 1600}

        header = "Bearer " + b64u_encode(actors[0][1])
        with pytest.raises(HmpError) as refusal:
            auth.authenticate(header, "wrong-instance")
        assert refusal.value.code is ErrorCode.WRONG_INSTANCE
        for invalid in (None, "Bearer invalid", "Bearer " + b64u_encode(bytes([255]) * 32)):
            with pytest.raises(HmpError) as refusal:
                auth.authenticate(invalid, iid)
            assert refusal.value.code is ErrorCode.UNAUTHENTICATED

        # A family belonging to a different synthetic device cannot authenticate.
        mismatched = bytes([240]) * 32
        store.insert_access_token(hashlib.sha256(mismatched).digest(), actors[1][0].family_id,
                                  actors[0][0].device_id, iid, 2000)
        with pytest.raises(HmpError) as refusal:
            auth.authenticate("Bearer " + b64u_encode(mismatched), iid)
        assert refusal.value.code is ErrorCode.UNAUTHENTICATED

        expired = bytes([241]) * 32
        store.insert_access_token(hashlib.sha256(expired).digest(), actors[0][0].family_id,
                                  actors[0][0].device_id, iid, 999)
        with pytest.raises(HmpError) as refusal:
            auth.authenticate("Bearer " + b64u_encode(expired), iid)
        assert refusal.value.code is ErrorCode.UNAUTHENTICATED

        store.set_device_state(actors[2][0].device_id, "REVOKED")
        with pytest.raises(HmpError) as refusal:
            auth.authenticate("Bearer " + b64u_encode(actors[2][1]), iid)
        assert refusal.value.code is ErrorCode.REVOKED
    finally:
        store.close()
