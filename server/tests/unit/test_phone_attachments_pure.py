"""D4 pure/fake-only causal definitions. No native, descriptor read, socket or custody adapter."""

from __future__ import annotations

import asyncio
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from hmp_plugin.contract import (
    OwnedPhoneAttachmentInput,
    PhoneAttachmentLogicalItem,
    PhoneAttachmentMessageRequest,
    PhoneAttachmentMime,
    PhoneAttachmentPayload,
    PhoneAttachmentValidated,
    PhoneAttachmentValidationFailure,
    PhoneAttachmentValidationRejected,
    PhoneAttachmentWireReference,
)
from hmp_plugin.phone_attachments import (
    canonical_phone_attachment_payload,
    parse_phone_attachment_message,
    parse_phone_attachment_message_json,
    phone_attachment_message_wire,
    phone_attachment_payload_hash,
)

VECTORS = json.loads((Path(__file__).resolve().parents[3] /
    "specs/028-phone-attachments/contracts/canonical-hash-vectors.json").read_text())
CMID = "00000000-0000-7000-8000-000000000099"
REF = "A" * 43


def payload(value: dict[str, object]) -> PhoneAttachmentPayload:
    return PhoneAttachmentPayload(value["target_binding"], value["text"], tuple(
        PhoneAttachmentLogicalItem(i["client_attachment_id"], i["sha256"],
            PhoneAttachmentMime(i["mime"]), i["length"], i["label"])
        for i in value["items"]
    ))


def request(value: PhoneAttachmentPayload) -> PhoneAttachmentMessageRequest:
    return PhoneAttachmentMessageRequest(CMID, value, tuple(
        PhoneAttachmentWireReference(i, REF) for i in value.items
    ))


@pytest.mark.parametrize("case", VECTORS["positive"], ids=lambda c: c["name"])
def test_exact_frozen_utf8_hash_and_wire_bound(case: dict[str, object]) -> None:
    value = payload(case["payload"])
    assert canonical_phone_attachment_payload(value).hex() == case["expected_canonical_utf8_hex"]
    assert phone_attachment_payload_hash(value) == case["expected_sha256"]
    if case["expected_wire_validation"] == "too_large":
        with pytest.raises(ValueError, match=r"^invalid phone attachment$"):
            request(value)
    else:
        body = phone_attachment_message_wire(request(value))
        raw = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
        assert len(raw) == case["expected_wire_bytes_with_reference_placeholder"]
        parsed = parse_phone_attachment_message_json(raw)
        assert parsed.payload == value


@pytest.mark.parametrize("case", VECTORS["negative_logical"], ids=lambda c: c["name"])
def test_closed_logical_negatives(case: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        payload(case["payload"])


@pytest.mark.parametrize("case", VECTORS["negative_raw_json"], ids=lambda c: c["name"])
def test_frozen_raw_negatives(case: dict[str, object]) -> None:
    with pytest.raises(ValueError, match=r"^malformed phone attachment request$"):
        parse_phone_attachment_message_json(bytes.fromhex(case["raw_json_utf8_hex"]))


def test_logical_changes_and_excluded_metadata_relations() -> None:
    actual = {c["name"]: phone_attachment_payload_hash(payload(c["payload"]))
        for c in VECTORS["positive"]}
    for relation in VECTORS["relations"]:
        hashes = [actual[name] for name in relation["cases"]]
        assert len(set(hashes)) == (1 if relation["relation"] == "equal" else len(hashes))


def test_raw_cap_duplicate_and_unknown_members_are_causal() -> None:
    body = phone_attachment_message_wire(request(payload(VECTORS["positive"][0]["payload"])))
    raw = json.dumps(body, separators=(",", ":")).encode()
    assert parse_phone_attachment_message_json(raw).client_message_id == CMID
    # Exact bound, then one over, from an otherwise identical valid object.
    assert parse_phone_attachment_message_json(raw + b" " * (8192 - len(raw)))
    invalid = [
        raw + b" " * (8193 - len(raw)),
        raw.replace(b'"revision":1', b'"revision":1,"revision":1'),
        raw.replace(b'"revision":1', b'"revision":1,"\\u0072evision":1'),
        raw.replace(b'"revision":1', b'"revision":1.0'),
        raw.replace(b'"revision":1', b'"revision":true'),
        raw.replace(b'"revision":1', b'"revision":NaN'),
        raw.replace(b'"revision":1', b'"revision":1e400'),
        raw.replace(b'"revision":1', b'"revision":1,"extra":0'),
        raw + b"0", b"\xff", b"[" * 9 + b"0" + b"]" * 9,
    ]
    for bad in invalid:
        with pytest.raises(ValueError, match=r"^malformed phone attachment request$"):
            parse_phone_attachment_message_json(bad)


def test_map_shape_preflight_and_reference_alignment() -> None:
    value = payload(VECTORS["positive"][4]["payload"])
    good = request(value)
    body = phone_attachment_message_wire(good)
    assert parse_phone_attachment_message(body) == good
    for name in ("revision", "target_binding", "client_message_id", "attachments"):
        changed = dict(body)
        changed.pop(name)
        with pytest.raises(ValueError, match=r"^malformed phone attachment request$"):
            parse_phone_attachment_message(changed)
    with pytest.raises(ValueError, match=r"^invalid phone attachment$"):
        PhoneAttachmentMessageRequest(CMID, value, tuple(reversed(good.references)))
    body["attachments"][0]["length"] = True
    with pytest.raises(ValueError, match=r"^malformed phone attachment request$"):
        parse_phone_attachment_message(body)


def test_subclass_hooks_do_not_run_and_values_are_immutable_redacted() -> None:
    class HostileString(str):
        def __len__(self) -> int:
            raise AssertionError("hook ran")

    class HostileTuple(tuple):
        def __iter__(self):
            raise AssertionError("hook ran")

    class HostileDict(dict):
        def __iter__(self):
            raise AssertionError("hook ran")

    item = payload(VECTORS["positive"][0]["payload"]).items[0]
    with pytest.raises(ValueError, match=r"^invalid phone attachment$"):
        PhoneAttachmentLogicalItem(HostileString(item.client_attachment_id), item.sha256,
            item.mime, item.length, item.label)
    with pytest.raises(ValueError, match=r"^invalid phone attachment$"):
        PhoneAttachmentPayload(REF, "x", HostileTuple((item,)))
    with pytest.raises(ValueError, match=r"^malformed phone attachment request$"):
        parse_phone_attachment_message(HostileDict())
    with pytest.raises(FrozenInstanceError):
        item.label = "changed"
    value = request(PhoneAttachmentPayload(REF, "synthetic-private-caption", (item,)))
    values = (item, value, value.payload, value.references[0], OwnedPhoneAttachmentInput(9, item))
    for obj in values:
        printed = str(obj) + repr(obj)
        for private in (CMID, REF, item.label, item.sha256, "synthetic-private-caption"):
            assert private not in printed


def test_reference_canonical_tail_and_fixed_constructor_failure() -> None:
    value = payload(VECTORS["positive"][0]["payload"])
    for ref in (REF[:-1] + "B", REF + "=", "!" * 43):
        with pytest.raises(ValueError, match=r"^invalid phone attachment$"):
            PhoneAttachmentWireReference(value.items[0], ref)
    assert str(PhoneAttachmentValidationRejected(PhoneAttachmentValidationFailure.UNAVAILABLE)) == (
        "PhoneAttachmentValidationRejected"
    )


class HeldFakeValidator:
    """Explicit fake: no descriptor or content validation, never production availability."""
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.active = False

    async def validate(self, source: OwnedPhoneAttachmentInput, /):
        self.active = True
        self.started.set()
        try:
            try:
                await asyncio.shield(self.release.wait())
            except asyncio.CancelledError:
                await self.release.wait()
                raise
            return PhoneAttachmentValidated(source.expected)
        finally:
            self.active = False


@pytest.mark.asyncio
async def test_fake_contract_retains_actual_terminal_lifetime_on_cancel() -> None:
    fake = HeldFakeValidator()
    source = OwnedPhoneAttachmentInput(9, payload(VECTORS["positive"][0]["payload"]).items[0])
    task = asyncio.create_task(fake.validate(source))
    await fake.started.wait()
    task.cancel()
    await asyncio.sleep(0)
    assert fake.active and not task.done()
    fake.release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not fake.active


def test_all_metadata_domains_are_syntactic_and_closed() -> None:
    from hmp_plugin.contract import (
        PhoneAttachmentBytesState,
        PhoneAttachmentCaptionState,
        PhoneAttachmentLimits,
        PhoneAttachmentProjectedItem,
        PhoneAttachmentReceipt,
        PhoneAttachmentReservation,
        PhoneAttachmentRowPresent,
        PhoneAttachmentsAvailable,
        PhoneAttachmentSendState,
        PhoneAttachmentsUnavailable,
        PhoneAttachmentTargetBinding,
        PhoneAttachmentTargetState,
        PhoneAttachmentUnavailableReason,
    )

    value = payload(VECTORS["positive"][0]["payload"])
    item = value.items[0]
    def limits(**changes):
        fields = {"item_count": 4, "item_bytes": 8 * 1024 * 1024,
            "message_bytes": 16 * 1024 * 1024, "output_edge": 2048, "source_pixels": 120_000_000,
            "source_edge": 32768, "source_image_bytes": 16 * 1024 * 1024,
            "selection_source_bytes": 32 * 1024 * 1024,
            "normalized_mimes": tuple(PhoneAttachmentMime)}
        return PhoneAttachmentLimits(**(fields | changes))

    target = PhoneAttachmentTargetBinding(REF, PhoneAttachmentTargetState.ABSENT, 1)
    available = PhoneAttachmentsAvailable(target, limits())
    closed = PhoneAttachmentsUnavailable(PhoneAttachmentUnavailableReason.ADMISSION_UNAVAILABLE)
    assert available.target.state is PhoneAttachmentTargetState.ABSENT
    assert str(closed) == "PhoneAttachmentsUnavailable"
    for changes in ({"item_count": True}, {"item_count": 5}, {"source_pixels": 120_000_001},
            {"normalized_mimes": ()}, {"normalized_mimes": (PhoneAttachmentMime.JPEG,) * 2}):
        with pytest.raises(ValueError, match=r"^invalid phone attachment$"):
            limits(**changes)
    reservation = PhoneAttachmentReservation("a" * 52, "opaque-routed-user", "dev_opaque",
        "triage", CMID, REF, phone_attachment_payload_hash(value), (item.client_attachment_id,),
        "0" * 64, 0, PhoneAttachmentSendState.UNKNOWN, 0)
    assert "caption" not in repr(reservation)
    assert not hasattr(reservation, "text")
    expired = PhoneAttachmentProjectedItem(item, PhoneAttachmentBytesState.EXPIRED, None)
    live = PhoneAttachmentProjectedItem(item, PhoneAttachmentBytesState.AVAILABLE, REF)
    receipt = PhoneAttachmentReceipt(phone_attachment_payload_hash(value),
        PhoneAttachmentCaptionState.UNAVAILABLE, (expired,))
    assert PhoneAttachmentRowPresent(1, CMID, receipt).receipt.items == (expired,)
    for state, ref_value in ((PhoneAttachmentBytesState.AVAILABLE, None),
            (PhoneAttachmentBytesState.EXPIRED, REF)):
        with pytest.raises(ValueError, match=r"^invalid phone attachment$"):
            PhoneAttachmentProjectedItem(item, state, ref_value)
    for row_id in (True, 1.0, 0, 1 << 53):
        with pytest.raises(ValueError, match=r"^invalid phone attachment$"):
            PhoneAttachmentRowPresent(row_id, CMID, receipt)
    for obj in (available, target, expired, live, receipt, reservation):
        for secret in (REF, CMID, "triage", item.label, item.sha256):
            assert secret not in repr(obj)


def test_fixed_parse_failure_retains_no_raw_exception_cause_or_context() -> None:
    body = phone_attachment_message_wire(request(payload(VECTORS["positive"][0]["payload"])))
    body["attachments"][0]["mime"] = "synthetic-private-invalid-mime"
    for operation in (lambda: parse_phone_attachment_message(body),
            lambda: parse_phone_attachment_message_json(b"\xffsynthetic-private-bytes")):
        with pytest.raises(ValueError, match=r"^malformed phone attachment request$") as failure:
            operation()
        assert failure.value.__cause__ is None
        assert failure.value.__context__ is None
        assert "private" not in str(failure.value)


@pytest.mark.parametrize("raw", [
    b'{"a":0,"b":0,"c":0,"d":0,"e":0,"f":0,"g":0}',
    b'[0,0,0,0,0]',
    b'{"ignored":[0,0,0,0,0]}',
    b'[' * 9 + b'0' + b']' * 9,
    b'{"a":' * 9 + b'0' + b'}' * 9,
], ids=["object-seven", "array-five", "unknown-nested-array-five", "array-depth-nine",
    "object-depth-nine"])
def test_raw_structural_overcaps_precede_generic_decoder(raw: bytes, monkeypatch) -> None:
    import hmp_plugin.phone_attachments as codec

    calls = []
    decoder = codec.json.loads
    def counted(*args, **kwargs):
        calls.append(True)
        return decoder(*args, **kwargs)
    monkeypatch.setattr(codec.json, "loads", counted)
    with pytest.raises(ValueError, match=r"^malformed phone attachment request$") as failure:
        parse_phone_attachment_message_json(raw)
    assert calls == []
    assert failure.value.__cause__ is None
    assert failure.value.__context__ is None


def test_raw_total_member_cap_precedes_decoder_and_exact_valid_bound_reaches_it(
    monkeypatch,
) -> None:
    import hmp_plugin.phone_attachments as codec

    value = payload(next(case["payload"] for case in VECTORS["positive"]
        if len(case["payload"]["items"]) == 4 and case["expected_wire_validation"] != "too_large"))
    body = phone_attachment_message_wire(request(value))
    assert len(body) == 5
    assert len(body["attachments"]) == 4
    assert all(len(row) == 6 for row in body["attachments"])
    assert len(body) + sum(len(row) for row in body["attachments"]) == 29
    good = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    # Keep every object within six members, arrays within four, and depth below eight;
    # only the total member count changes from 29 to 30.
    body["extra"] = 0
    bad = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    assert len(body) == 6 and len(bad) <= 8192
    calls = []
    decoder = codec.json.loads
    def counted(*args, **kwargs):
        calls.append(True)
        return decoder(*args, **kwargs)
    monkeypatch.setattr(codec.json, "loads", counted)
    with pytest.raises(ValueError, match=r"^malformed phone attachment request$") as failure:
        parse_phone_attachment_message_json(bad)
    assert calls == []
    assert failure.value.__cause__ is None
    assert failure.value.__context__ is None
    assert parse_phone_attachment_message_json(good).payload == value
    assert calls == [True]


def test_raw_exact_depth_bound_reaches_decoder_without_granting_shape_admission(
    monkeypatch,
) -> None:
    import hmp_plugin.phone_attachments as codec

    calls = []
    decoder = codec.json.loads
    def counted(*args, **kwargs):
        calls.append(True)
        return decoder(*args, **kwargs)
    monkeypatch.setattr(codec.json, "loads", counted)
    # Eight one-entry containers are structurally legal but are not a message object.
    with pytest.raises(ValueError, match=r"^malformed phone attachment request$"):
        parse_phone_attachment_message_json(b'[' * 8 + b'0' + b']' * 8)
    assert calls == [True]
