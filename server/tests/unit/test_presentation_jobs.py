"""Synthetic frame and parent-ownership causals; no child, native, or files."""

from __future__ import annotations

import asyncio
import hashlib
import json
import struct
import unittest

from hmp_plugin.presentation_jobs import (
    BoundedResultBuffer,
    CapturedLease,
    FrameError,
    JobOwner,
    State,
    decode_input,
    decode_output,
    encode_input,
    encode_output,
)

CHALLENGE = "a" * 64
DIGEST = "b" * 64


def input_row() -> dict[str, object]:
    return {
        "schema": 1,
        "challenge": CHALLENGE,
        "epoch": 1,
        "profile": "alpha",
        "root": "/owned/root",
        "home": "/owned/root/profiles/alpha",
        "operation": "METADATA",
        "expected_avatar_sha": None,
        "uid": 501,
        "gid": 20,
        "dir_modes": [448, 488, 493],
        "leaf_modes": [384, 416, 420],
        "source_manifest_sha": DIGEST,
        "deadline_ns": 123456789,
    }


def header_row() -> dict[str, object]:
    return {
        "schema": 1,
        "challenge": CHALLENGE,
        "epoch": 1,
        "outcome": "OK",
        "fields": {
            "display_name": "Aster",
            "title": "Aster",
            "shape": "squircle",
            "color": "#8b5cf6",
            "custom": False,
        },
        "mime": None,
        "width": 0,
        "height": 0,
        "avatar_sha": None,
        "avatar_length": 0,
        "source_proof": {
            "profile_meta": [1, 2, 33152, 501, 20, 1, 10, 3, 4],
            "profile_sha": DIGEST,
            "avatar_meta": None,
            "avatar_body_sha": None,
        },
        "absence_bitmap": 14,
        "chain": [[1, 2, 16832, 0, 0, 2, 0, 3, 4]],
        "ledger": {
            "body_bytes": 10,
            "opens": 2,
            "metadata": 5,
            "path_bytes": 50,
            "raster_units": 0,
            "yaml_nodes": 4,
        },
        "cleanup": {"known_fds_closed": True, "unknown_close": False},
    }


def lease() -> CapturedLease:
    return CapturedLease("iid", "device", "user", "family", "alpha", DIGEST, "binding", 1)


class Authority:
    def __init__(self) -> None:
        self.entered: asyncio.Event | None = None
        self.release: asyncio.Event | None = None
        self.calls: list[str] = []

    async def reauthenticate(self, captured: CapturedLease, stage: str) -> bool:
        assert captured == lease()
        self.calls.append(stage)
        if self.entered is not None and self.release is not None:
            self.entered.set()
            await self.release.wait()
        return True


class Frames(unittest.TestCase):
    def test_closed_input_round_trip(self) -> None:
        row = input_row()
        self.assertEqual(decode_input(encode_input(row)), row)

    def test_input_rejects_duplicate_extra_bool_profile_escape(self) -> None:
        wire = encode_input(input_row())
        raw = wire[4:]
        for payload in (
            b'{"schema":1,"schema":1}',
            raw[:-1] + b',"private_config":"secret"}',
            raw.replace(b'"uid":501', b'"uid":true'),
            raw.replace(b'"/owned/root/profiles/alpha"', b'"/owned/root/../secret"'),
            raw.replace(b'"alpha"', b'"Alpha"'),
            raw + b"X",
        ):
            with self.assertRaises(FrameError):
                decode_input(struct.pack(">I", len(payload)) + payload)
        for name in ("dir_modes", "leaf_modes"):
            for bad in (
                [float(item) for item in input_row()[name]],
                [True, 488, 493],
                tuple(input_row()[name]),
                [*input_row()[name], 0],
            ):
                changed = input_row()
                changed[name] = bad
                with self.assertRaises(FrameError):
                    encode_input(changed)

    def test_output_round_trip_and_closed_projection(self) -> None:
        header = header_row()
        wire = encode_output(header, b"")
        self.assertEqual(decode_output(wire, CHALLENGE, 1), (header, b""))
        with self.assertRaises(FrameError):
            decode_output(wire, "c" * 64, 1)
        with self.assertRaises(FrameError):
            decode_output(wire + b"X", CHALLENGE, 1)
        for fields in (
            {"private_prompt": "secret"},
            {"custom": {"url": "https://bad.invalid"}},
            {"display_name": "X" * 257},
            {"color": "#GGGGGG"},
        ):
            changed = header_row()
            changed["fields"] = fields
            with self.assertRaises(FrameError):
                encode_output(changed, b"")
        for row in (
            None,
            [1] * 8,
            [1] * 10,
            [1.0] + [1] * 8,
            [True] + [1] * 8,
            tuple([1] * 9),
        ):
            changed = header_row()
            changed["chain"] = [row]
            with self.assertRaises(FrameError):
                encode_output(changed, b"")

    def test_avatar_exact_hash_and_length(self) -> None:
        body = b"real synthetic pixels"
        changed = header_row()
        changed.update(
            {
                "mime": "image/png",
                "width": 1,
                "height": 1,
                "avatar_sha": hashlib.sha256(body).hexdigest(),
                "avatar_length": len(body),
            }
        )
        changed["source_proof"]["avatar_meta"] = [1, 3, 33152, 501, 20, 1, len(body), 3, 4]
        changed["source_proof"]["avatar_body_sha"] = changed["avatar_sha"]
        wire = encode_output(changed, body)
        self.assertEqual(decode_output(wire, CHALLENGE, 1)[1], body)
        with self.assertRaises(FrameError):
            decode_output(wire[:-1] + b"x", CHALLENGE, 1)

    def test_bounded_accumulator_rejects_partial_extra_and_reuse(self) -> None:
        wire = encode_output(header_row(), b"")
        buffer = BoundedResultBuffer()
        buffer.feed(wire[:3])
        with self.assertRaises(FrameError):
            buffer.finish(CHALLENGE, 1)
        buffer = BoundedResultBuffer()
        buffer.feed(wire)
        with self.assertRaises(FrameError):
            buffer.feed(b"X")
        buffer = BoundedResultBuffer()
        buffer.feed(wire)
        self.assertEqual(buffer.finish(CHALLENGE, 1)[1], b"")
        with self.assertRaises(FrameError):
            buffer.finish(CHALLENGE, 1)
        buffer = BoundedResultBuffer()
        with self.assertRaises(FrameError):
            buffer.feed(b"X" * 65537)


class Ownership(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.now = 100.0
        self.authority = Authority()
        self.owner = JobOwner("iid", self.authority, lambda: self.now, lambda: CHALLENGE)
        self.job = self.owner.queue(lease(), "METADATA")
        self.job_challenge = self.owner.challenge(self.job)

    async def _running(self) -> object:
        await self.owner.authorize(self.job)
        self.owner.start(self.job)
        child = object()
        self.owner.bind_child(self.job, child)
        self.owner.go(self.job, child, self.job_challenge)
        return child

    async def _complete(self) -> object:
        child = await self._running()
        header = header_row()
        header["challenge"] = self.job_challenge
        wire = encode_output(header, b"")
        for offset in range(0, len(wire), 13):
            self.owner.feed_result(self.job, wire[offset : offset + 13], child)
        for event in (
            "RESULT_EOF",
            "DIAGNOSTIC_EOF",
            "WAIT_OK",
            "GROUP_GONE",
            "IPC_CLOSED",
            "SIGNAL_CLOSED",
        ):
            self.owner.custody(self.job, event, child)
        self.assertIs(self.owner.inspect(self.job)[0], State.COMPLETE)
        return child

    async def test_unbound_authority_refuses_before_child(self) -> None:
        owner = JobOwner("iid", clock=lambda: self.now, challenge_source=lambda: CHALLENGE)
        job = owner.queue(lease(), "METADATA")
        await owner.authorize(job)
        self.assertIs(owner.inspect(job)[0], State.REFUSED)
        self.assertTrue(owner.inspect(job)[2])

    async def test_foreign_instance_and_forged_handle_refuse(self) -> None:
        other = CapturedLease("other", "device", "user", "family", "alpha", DIGEST, "binding", 1)
        with self.assertRaises(FrameError):
            self.owner.queue(other, "METADATA")
        from hmp_plugin.presentation_jobs import JobHandle

        with self.assertRaises(FrameError):
            self.owner.start(JobHandle())

    async def test_pre_go_result_disables_owner_without_emission(self) -> None:
        await self.owner.authorize(self.job)
        self.owner.start(self.job)
        child = object()
        self.owner.bind_child(self.job, child)
        self.owner.feed_result(self.job, encode_output(header_row(), b""), child)
        self.assertIs(self.owner.inspect(self.job)[0], State.UNKNOWN)
        self.assertTrue(self.owner.disabled)

    async def test_wrong_go_challenge_cannot_be_reused(self) -> None:
        await self.owner.authorize(self.job)
        self.owner.start(self.job)
        child = object()
        self.owner.bind_child(self.job, child)
        self.owner.go(self.job, child, "c" * 64)
        self.assertIs(self.owner.inspect(self.job)[0], State.UNKNOWN)
        with self.assertRaises(FrameError):
            self.owner.go(self.job, child, self.job_challenge)

    async def test_full_synthetic_path_requires_final_authority(self) -> None:
        await self._complete()
        self.assertEqual(self.authority.calls, ["BEFORE"])
        emitted: list[tuple[dict[str, object], bytes]] = []
        await self.owner.reauthorize(self.job)
        self.owner.emit_inline(self.job, lambda _: True, lambda h, b: emitted.append((h, b)))
        self.assertEqual(len(emitted), 1)
        self.assertIs(self.owner.inspect(self.job)[0], State.EMIT)
        self.assertEqual(self.authority.calls, ["BEFORE", "AFTER"])
        with self.assertRaises(FrameError):
            self.owner.emit_inline(self.job, lambda _: True, lambda h, b: None)

    async def test_stale_authority_await_and_epoch_retirement(self) -> None:
        self.authority.entered = asyncio.Event()
        self.authority.release = asyncio.Event()
        task = asyncio.create_task(self.owner.authorize(self.job))
        await self.authority.entered.wait()
        self.owner.retire_epoch()
        self.authority.release.set()
        await task
        self.assertIs(self.owner.inspect(self.job)[0], State.REFUSED)
        self.assertFalse(self.owner.inspect(self.job)[1])

    async def test_deadline_no_emit_and_retained_credit_until_drain(self) -> None:
        child = await self._running()
        self.now = 102.0
        self.owner.deadline(self.job)
        self.assertIs(self.owner.inspect(self.job)[0], State.DRAINING)
        self.assertFalse(self.owner.inspect(self.job)[2])
        self.owner.custody(self.job, "RESULT_EOF", child)
        self.assertIs(self.owner.inspect(self.job)[0], State.UNKNOWN)
        self.assertFalse(self.owner.inspect(self.job)[2])

    async def test_canceled_running_clean_refusal_can_drain_without_emit(self) -> None:
        child = await self._running()
        self.owner.cancel(self.job)
        header = header_row()
        header["challenge"] = self.job_challenge
        header["outcome"] = "REFUSED"
        header["fields"] = {}
        self.owner.feed_result(self.job, encode_output(header, b""), child)
        for event in (
            "RESULT_EOF",
            "DIAGNOSTIC_EOF",
            "WAIT_FAIL",
            "GROUP_GONE",
            "IPC_CLOSED",
            "SIGNAL_CLOSED",
        ):
            self.owner.custody(self.job, event, child)
        self.assertIs(self.owner.inspect(self.job)[0], State.REFUSED)
        self.assertTrue(self.owner.inspect(self.job)[2])

    async def test_unknown_wrong_challenge_retains_credit_disables_owner(self) -> None:
        child = await self._running()
        self.owner.feed_result(self.job, encode_output(header_row(), b""), object())
        self.assertIs(self.owner.inspect(self.job)[0], State.UNKNOWN)
        self.assertFalse(self.owner.inspect(self.job)[2])
        self.assertTrue(self.owner.disabled)
        del child

    async def test_result_without_eof_reap_is_never_complete(self) -> None:
        child = await self._running()
        self.owner.feed_result(self.job, encode_output(header_row(), b""), child)
        self.owner.custody(self.job, "WAIT_OK", child)
        self.owner.custody(self.job, "GROUP_GONE", child)
        self.assertIs(self.owner.inspect(self.job)[0], State.RUNNING)
        self.assertFalse(self.owner.inspect(self.job)[2])

    async def test_extra_result_and_diagnostic_budget_refuse(self) -> None:
        child = await self._running()
        header = header_row()
        header["challenge"] = self.job_challenge
        wire = encode_output(header, b"")
        self.owner.feed_result(self.job, wire + b"x", child)
        self.assertIs(self.owner.inspect(self.job)[0], State.UNKNOWN)
        other_owner = JobOwner("iid", Authority(), lambda: self.now, lambda: "d" * 64)
        other = other_owner.queue(lease(), "METADATA")
        await other_owner.authorize(other)
        other_owner.start(other)
        second_child = object()
        other_owner.bind_child(other, second_child)
        other_owner.go(other, second_child, other_owner.challenge(other))
        other_owner.diagnostic(other, 4097)
        self.assertIs(other_owner.inspect(other)[0], State.UNKNOWN)

    async def test_no_late_emit_after_deadline_or_scope_loss(self) -> None:
        await self._complete()
        await self.owner.reauthorize(self.job)
        self.now = 102.0
        emitted: list[object] = []
        self.owner.emit_inline(self.job, lambda _: True, lambda h, b: emitted.append(h))
        self.assertEqual(emitted, [])
        self.assertIs(self.owner.inspect(self.job)[0], State.REFUSED)

    async def test_post_authority_current_callback_denies(self) -> None:
        await self._complete()
        await self.owner.reauthorize(self.job)
        emitted: list[object] = []
        self.owner.emit_inline(self.job, lambda _: False, lambda h, b: emitted.append(h))
        self.assertEqual(emitted, [])
        self.assertIs(self.owner.inspect(self.job)[0], State.REFUSED)

    async def test_final_reauth_canceled_after_await(self) -> None:
        await self._complete()
        self.authority.entered = asyncio.Event()
        self.authority.release = asyncio.Event()
        task = asyncio.create_task(self.owner.reauthorize(self.job))
        await self.authority.entered.wait()
        self.owner.retire_epoch()
        self.authority.release.set()
        await task
        self.assertIs(self.owner.inspect(self.job)[0], State.REFUSED)

    async def test_terminal_journal_is_bounded_and_opaque(self) -> None:
        handles = [self.job]
        issued = [self.job_challenge]
        self.owner.cancel(self.job)
        for _ in range(80):
            owner = self.owner
            handle = owner.queue(lease(), "METADATA")
            handles.append(handle)
            issued.append(owner.challenge(handle))
            owner.cancel(handle)
        self.assertEqual(len(set(issued)), len(issued))
        self.assertEqual(len(self.owner._jobs), 0)
        self.assertEqual(len(self.owner._terminal), 64)
        with self.assertRaises(FrameError):
            self.owner.inspect(handles[0])
        self.assertIs(self.owner.inspect(handles[-1])[0], State.REFUSED)
        with self.assertRaises(FrameError):
            self.owner.start(handles[0])
        new = self.owner.queue(lease(), "METADATA")
        await self.owner.authorize(new)
        self.owner.start(new)
        child = object()
        self.owner.bind_child(new, child)
        self.owner.go(new, child, self.owner.challenge(new))
        stale = header_row()
        stale["challenge"] = issued[0]
        self.owner.feed_result(new, encode_output(stale, b""), child)
        self.owner.custody(new, "RESULT_EOF", child)
        self.assertIs(self.owner.inspect(new)[0], State.UNKNOWN)

    async def test_many_successful_avatar_jobs_drop_private_buffers(self) -> None:
        value = 0

        def challenge() -> str:
            nonlocal value
            value += 1
            return f"{value:064x}"

        owner = JobOwner("iid", Authority(), lambda: self.now, challenge)
        old: list[object] = []
        for _ in range(70):
            handle = owner.queue(lease(), "AVATAR")
            old.append(handle)
            await owner.authorize(handle)
            owner.start(handle)
            child = object()
            owner.bind_child(handle, child)
            frame_challenge = owner.challenge(handle)
            owner.go(handle, child, frame_challenge)
            body = b"private-pixels" * 200
            header = header_row()
            header["challenge"] = frame_challenge
            header["mime"] = "image/png"
            header["width"] = 1
            header["height"] = 1
            header["avatar_sha"] = hashlib.sha256(body).hexdigest()
            header["avatar_length"] = len(body)
            header["source_proof"]["avatar_meta"] = [1, 3, 33152, 501, 20, 1, len(body), 3, 4]
            header["source_proof"]["avatar_body_sha"] = header["avatar_sha"]
            wire = encode_output(header, body)
            for offset in range(0, len(wire), 1024):
                owner.feed_result(handle, wire[offset : offset + 1024], child)
            for event in (
                "RESULT_EOF",
                "DIAGNOSTIC_EOF",
                "WAIT_OK",
                "GROUP_GONE",
                "IPC_CLOSED",
                "SIGNAL_CLOSED",
            ):
                owner.custody(handle, event, child)
            await owner.reauthorize(handle)
            owner.emit_inline(handle, lambda _: True, lambda h, b: None)
            self.assertIs(owner.inspect(handle)[0], State.EMIT)
        self.assertEqual(len(owner._jobs), 0)
        self.assertEqual(len(owner._terminal), 64)
        self.assertNotIn("private-pixels", repr(owner._terminal))
        with self.assertRaises(FrameError):
            owner.inspect(old[0])

    async def test_starting_cancel_late_child_attaches_for_drain_only(self) -> None:
        await self.owner.authorize(self.job)
        self.owner.start(self.job)
        self.owner.cancel(self.job)
        self.assertIs(self.owner.inspect(self.job)[0], State.DRAINING)
        child = object()
        self.owner.bind_child(self.job, child)
        self.assertFalse(self.owner.inspect(self.job)[1])
        with self.assertRaises(FrameError):
            self.owner.go(self.job, child, self.job_challenge)
        for event in (
            "RESULT_EOF",
            "DIAGNOSTIC_EOF",
            "WAIT_FAIL",
            "GROUP_GONE",
            "IPC_CLOSED",
            "SIGNAL_CLOSED",
        ):
            self.owner.custody(self.job, event, child)
        self.assertIs(self.owner.inspect(self.job)[0], State.REFUSED)
        self.assertTrue(self.owner.inspect(self.job)[2])

    async def test_unbound_none_custody_never_releases_pending_start(self) -> None:
        events = (
            "RESULT_EOF",
            "DIAGNOSTIC_EOF",
            "WAIT_FAIL",
            "GROUP_GONE",
            "IPC_CLOSED",
            "SIGNAL_CLOSED",
        )
        for event in events:
            with self.subTest(event=event):
                owner = JobOwner("iid", Authority(), lambda: self.now, lambda: CHALLENGE)
                handle = owner.queue(lease(), "METADATA")
                await owner.authorize(handle)
                owner.start(handle)
                owner.cancel(handle)
                owner.custody(handle, event, None)
                state, go_sent, released = owner.inspect(handle)
                self.assertIs(state, State.UNKNOWN)
                self.assertFalse(go_sent)
                self.assertFalse(released)
                self.assertTrue(owner.disabled)
                self.assertIn(handle, owner._jobs)
                self.assertIsNone(owner._jobs[handle].child)
                self.assertFalse(owner._jobs[handle].seen_events)
                self.assertFalse(owner._jobs[handle].result_eof)
                self.assertFalse(owner._jobs[handle].wait_done)
                self.assertFalse(owner._jobs[handle].group_gone)
                self.assertFalse(owner._jobs[handle].ipc_closed)
                self.assertFalse(owner._jobs[handle].signal_closed)
                with self.assertRaises(FrameError):
                    owner.bind_child(handle, object())

    async def test_bound_child_rejects_none_and_foreign_custody(self) -> None:
        for invalid_child in (None, object()):
            with self.subTest(invalid_child=invalid_child):
                owner = JobOwner("iid", Authority(), lambda: self.now, lambda: CHALLENGE)
                handle = owner.queue(lease(), "METADATA")
                await owner.authorize(handle)
                owner.start(handle)
                child = object()
                owner.bind_child(handle, child)
                owner.custody(handle, "RESULT_EOF", invalid_child)
                self.assertIs(owner.inspect(handle)[0], State.UNKNOWN)
                self.assertFalse(owner.inspect(handle)[2])
                self.assertFalse(owner._jobs[handle].seen_events)

    async def test_late_bind_duplicate_and_foreign_child_stay_closed(self) -> None:
        await self.owner.authorize(self.job)
        self.owner.start(self.job)
        self.owner.retire_epoch()
        child = object()
        self.owner.bind_child(self.job, child)
        self.assertIs(self.owner.inspect(self.job)[0], State.DRAINING)
        self.owner.bind_child(self.job, object())
        self.assertIs(self.owner.inspect(self.job)[0], State.UNKNOWN)
        self.assertFalse(self.owner.inspect(self.job)[2])

    async def test_unknown_close_is_sticky_and_retains_credit(self) -> None:
        child = await self._running()
        header = header_row()
        header["outcome"] = "REFUSED"
        header["fields"] = {}
        header["cleanup"] = {"known_fds_closed": False, "unknown_close": True}
        header["challenge"] = self.job_challenge
        self.owner.feed_result(self.job, encode_output(header, b""), child)
        for event in (
            "RESULT_EOF",
            "DIAGNOSTIC_EOF",
            "WAIT_OK",
            "GROUP_GONE",
            "IPC_CLOSED",
            "SIGNAL_CLOSED",
        ):
            self.owner.custody(self.job, event, child)
        self.assertIs(self.owner.inspect(self.job)[0], State.UNKNOWN)
        self.assertFalse(self.owner.inspect(self.job)[2])
        self.assertTrue(self.owner.disabled)
        with self.assertRaises(FrameError):
            self.owner.queue(lease(), "METADATA")

    async def test_refused_known_cleanup_can_retire(self) -> None:
        child = await self._running()
        header = header_row()
        header["outcome"] = "REFUSED"
        header["fields"] = {}
        header["challenge"] = self.job_challenge
        self.owner.feed_result(self.job, encode_output(header, b""), child)
        for event in (
            "RESULT_EOF",
            "DIAGNOSTIC_EOF",
            "WAIT_FAIL",
            "GROUP_GONE",
            "IPC_CLOSED",
            "SIGNAL_CLOSED",
        ):
            self.owner.custody(self.job, event, child)
        self.assertIs(self.owner.inspect(self.job)[0], State.REFUSED)
        self.assertTrue(self.owner.inspect(self.job)[2])
        self.assertEqual(len(self.owner._jobs), 0)

    async def test_refused_known_false_and_ok_unknown_both_retain(self) -> None:
        for outcome in ("REFUSED", "OK"):
            owner = JobOwner("iid", Authority(), lambda: self.now, lambda: CHALLENGE)
            handle = owner.queue(lease(), "METADATA")
            await owner.authorize(handle)
            owner.start(handle)
            child = object()
            owner.bind_child(handle, child)
            owner.go(handle, child, owner.challenge(handle))
            header = header_row()
            header["challenge"] = owner.challenge(handle)
            header["cleanup"] = {"known_fds_closed": False, "unknown_close": outcome == "OK"}
            header["outcome"] = outcome
            if outcome == "REFUSED":
                header["fields"] = {}
            if outcome == "OK":
                with self.assertRaises(FrameError):
                    encode_output(header, b"")
                # A malformed OK frame is rejected at observed EOF, never released.
                bad = json.dumps(header, separators=(",", ":")).encode()
                owner.feed_result(handle, struct.pack(">I", len(bad)) + bad, child)
                owner.custody(handle, "RESULT_EOF", child)
            else:
                owner.feed_result(handle, encode_output(header, b""), child)
                for event in (
                    "RESULT_EOF",
                    "DIAGNOSTIC_EOF",
                    "WAIT_OK",
                    "GROUP_GONE",
                    "IPC_CLOSED",
                    "SIGNAL_CLOSED",
                ):
                    owner.custody(handle, event, child)
            self.assertIs(owner.inspect(handle)[0], State.UNKNOWN)
            self.assertFalse(owner.inspect(handle)[2])


if __name__ == "__main__":
    unittest.main()
