"""Spec 028 D4 pure codec/hash only; no native, file, store, auth, route or lifecycle authority.

All values are syntactic. No function here performs a custody lookup, expiry decision, I/O,
automatic retry or operational feature admission. Existing text AP-6 remains separate.
"""

from __future__ import annotations

import hashlib
import json
from typing import NoReturn

from .contract import (
    PhoneAttachmentLogicalItem,
    PhoneAttachmentMessageRequest,
    PhoneAttachmentMime,
    PhoneAttachmentPayload,
    PhoneAttachmentWireReference,
    _pa_message_wire,
)


def _malformed() -> NoReturn:
    raise ValueError("malformed phone attachment request")


def canonical_phone_attachment_payload(payload: PhoneAttachmentPayload, /) -> bytes:
    if type(payload) is not PhoneAttachmentPayload:
        raise ValueError("invalid phone attachment")
    rows = [
        [i.client_attachment_id, i.sha256, i.mime.value, i.length, i.label]
        for i in payload.items
    ]
    return json.dumps(
        ["HMP1-PHONE-ATTACHMENT-SEND", 1, payload.target_binding, payload.text, rows],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def phone_attachment_payload_hash(payload: PhoneAttachmentPayload, /) -> str:
    return hashlib.sha256(canonical_phone_attachment_payload(payload)).hexdigest()


def phone_attachment_message_wire(request: PhoneAttachmentMessageRequest, /) -> dict[str, object]:
    if type(request) is not PhoneAttachmentMessageRequest:
        raise ValueError("invalid phone attachment")
    return _pa_message_wire(request)


def parse_phone_attachment_message(body: dict[str, object], /) -> PhoneAttachmentMessageRequest:
    # Exact builtin checks precede len/iteration/getitem: no overridden hooks/generators.
    if (type(body) is not dict or len(body) != 5
            or not all(type(k) is str for k in body) or set(body) != {
        "revision", "client_message_id", "text", "target_binding", "attachments"
    }):
        _malformed()
    if type(body["revision"]) is not int or body["revision"] != 1:
        _malformed()
    rows = body["attachments"]
    if type(rows) is not list or not 1 <= len(rows) <= 4:
        _malformed()
    items = []
    references = []
    try:
        for row in rows:
            if (type(row) is not dict or len(row) != 6
                    or not all(type(k) is str for k in row) or set(row) != {
                "client_attachment_id", "custody_reference", "sha256", "mime", "length", "label"
            }):
                _malformed()
            if type(row["mime"]) is not str:
                _malformed()
            item = PhoneAttachmentLogicalItem(
                row["client_attachment_id"], row["sha256"], PhoneAttachmentMime(row["mime"]),
                row["length"], row["label"],
            )
            items.append(item)
            references.append(PhoneAttachmentWireReference(item, row["custody_reference"]))
        payload = PhoneAttachmentPayload(body["target_binding"], body["text"], tuple(items))
        return PhoneAttachmentMessageRequest(body["client_message_id"], payload, tuple(references))
    except (ValueError, TypeError):
        invalid = True
    # Raise outside the handler so the fixed error retains no input-bearing cause/context.
    if invalid:
        _malformed()


def _phone_attachment_json_preflight(text: str, /) -> None:
    """Recognize bounded JSON grammar without constructing a generic object tree.

    Count each member/array entry before reading its value. The later decoder retains
    escaped-equivalent duplicate-key and scalar validation; it sees only structurally
    admitted input. Strings here are scanned, never decoded or accumulated.
    """
    position = 0
    members = 0
    size = len(text)

    def whitespace() -> None:
        nonlocal position
        while position < size and text[position] in " \t\r\n":
            position += 1

    def string() -> None:
        nonlocal position
        if position >= size or text[position] != '"':
            _malformed()
        position += 1
        while position < size:
            char = text[position]
            position += 1
            if char == '"':
                return
            if ord(char) < 32:
                _malformed()
            if char == "\\":
                if position >= size:
                    _malformed()
                escape = text[position]
                position += 1
                if escape == "u":
                    if position + 4 > size or any(
                        char not in "0123456789abcdefABCDEF"
                        for char in text[position:position + 4]
                    ):
                        _malformed()
                    position += 4
                elif escape not in '\"\\/bfnrt':
                    _malformed()
        _malformed()

    def value(depth: int) -> None:
        nonlocal position, members
        whitespace()
        if position >= size:
            _malformed()
        char = text[position]
        if char == '"':
            string()
            return
        if char in "[{":
            if depth >= 8:
                _malformed()
            position += 1
            whitespace()
            closing = "}" if char == "{" else "]"
            if position < size and text[position] == closing:
                position += 1
                return
            count = 0
            while True:
                count += 1
                if char == "{":
                    members += 1
                    if count > 6 or members > 29:
                        _malformed()
                    string()
                    whitespace()
                    if position >= size or text[position] != ":":
                        _malformed()
                    position += 1
                elif count > 4:
                    _malformed()
                value(depth + 1)
                whitespace()
                if position >= size:
                    _malformed()
                separator = text[position]
                position += 1
                if separator == closing:
                    return
                if separator != ",":
                    _malformed()
                whitespace()
        for literal in ("true", "false", "null"):
            if text.startswith(literal, position):
                position += len(literal)
                return
        # The wire allows only integer numbers. Reject floats/constants lexically,
        # without converting arbitrarily large numbers or constructing their values.
        if char == "-":
            position += 1
        if position >= size or text[position] not in "0123456789":
            _malformed()
        if text[position] == "0":
            position += 1
        else:
            while position < size and text[position] in "0123456789":
                position += 1
        if position < size and text[position] in ".eE":
            _malformed()

    value(0)
    whitespace()
    if position != size:
        _malformed()


def parse_phone_attachment_message_json(raw: bytes, /) -> PhoneAttachmentMessageRequest:
    if type(raw) is not bytes or len(raw) > 8192:
        _malformed()
    try:
        text = raw.decode("utf-8", errors="strict")
        _phone_attachment_json_preflight(text)

        members = 0

        def object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
            nonlocal members
            members += len(pairs)
            if len(pairs) > 6 or members > 29:
                _malformed()
            result = {}
            for key, value in pairs:
                if key in result:
                    _malformed()
                result[key] = value
            return result

        def reject_number(value: str) -> object:
            _malformed()

        value = json.loads(
            text, object_pairs_hook=object_pairs, parse_float=reject_number,
            parse_constant=reject_number,
        )
        # Bound all arrays/scalars, including otherwise ignored unknown values, before shape parse.
        def check(node: object) -> None:
            if type(node) is list:
                if len(node) > 4:
                    _malformed()
                for entry in node:
                    check(entry)
            elif type(node) is dict:
                for key, entry in node.items():
                    key.encode("utf-8", errors="strict")
                    check(entry)
            elif type(node) is str:
                node.encode("utf-8", errors="strict")

        check(value)
        return parse_phone_attachment_message(value)
    except (ValueError, TypeError, RecursionError):
        invalid = True
    if invalid:
        _malformed()
