"""`contract.py` against the contract text (HMP v1 §13, V-1, ERR-2, ERR-2a, ERR-3).

The tables are parsed from `docs/architecture/contracts/HMP_V1.md`, so drift in either direction
fails: a changed value, a row missing from `contract.py`, or a new row in the contract.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from hmp_plugin import contract as c

HMP_V1 = Path(__file__).resolve().parents[3] / "docs" / "architecture" / "contracts" / "HMP_V1.md"


@pytest.fixture(scope="module")
def doc() -> str:
    return HMP_V1.read_text(encoding="utf-8")


def _section(doc: str, start: str, end: str) -> str:
    i = doc.index(start)
    return doc[i : doc.index(end, i + len(start))]


def _rows(block: str) -> list[list[str]]:
    """Body rows of the markdown tables in `block` (header and separator rows dropped)."""
    rows = []
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("|") or re.fullmatch(r"\|[\s|:-]+\|", line):
            continue
        rows.append([cell.strip() for cell in line.strip("|").split(" | ")])
    return rows[1:] if rows else rows  # the first row of each section's table is its header


def _ints(cell: str) -> list[int]:
    cell = re.sub(r"\([^)]*\)", "", cell)  # "(30 d)", "(24 h)"
    cell = re.sub(r"in revision [\d.]+", "", cell)  # "0 in revision 1.0"
    return [int(m.replace(" ", "")) for m in re.findall(r"\d{1,3}(?: \d{3})+|\d+", cell)]


def _ticks(cell: str) -> list[str]:
    return re.findall(r"`([^`]+)`", cell)


# ---------------------------------------------------------------------------------------------
# §13 constants
# ---------------------------------------------------------------------------------------------

# Contract row name -> the contract.py attribute(s) its value cell lists, in order.
SECTION_13: dict[str, tuple[str, ...]] = {
    "OFFER_TTL_S": ("OFFER_TTL_S",),
    "PAIRING_CONFIRM_WINDOW_S": ("PAIRING_CONFIRM_WINDOW_S",),
    "ACCESS_TTL_S": ("ACCESS_TTL_S",),
    "REFRESH_IDLE_TTL_S": ("REFRESH_IDLE_TTL_S",),
    "REFRESH_ABSOLUTE_TTL_S": ("REFRESH_ABSOLUTE_TTL_S",),
    "REFRESH_RETRY_GRACE_S": ("REFRESH_RETRY_GRACE_S",),
    "CLOCK_SKEW_S": ("CLOCK_SKEW_S",),
    "WATCHDOG_INTERVAL_S": ("WATCHDOG_INTERVAL_S",),
    "HEARTBEAT_S": ("HEARTBEAT_S",),
    "TAIL_RING": ("TAIL_RING",),
    "ADMISSION_WAIT_S": ("ADMISSION_WAIT_S",),
    "ADMISSION_DEADLINE_S": ("ADMISSION_DEADLINE_S",),
    "LOOKUP_SETTLE_MARGIN_S": ("LOOKUP_SETTLE_MARGIN_S",),
    "IDEMPOTENCY_RETENTION_S": ("IDEMPOTENCY_RETENTION_S",),
    "CLIENT_RETRY_WINDOW_S": ("CLIENT_RETRY_WINDOW_S",),
    "CLIENT_MAX_AUTO_ATTEMPTS": ("CLIENT_MAX_AUTO_ATTEMPTS",),
    "MAX_BODY_BYTES / MAX_HEADER_BYTES": ("MAX_BODY_BYTES", "MAX_HEADER_BYTES"),
    "MAX_JSON_DEPTH": ("MAX_JSON_DEPTH",),
    "MAX_STREAMS_PER_DEVICE": ("MAX_STREAMS_PER_DEVICE",),
    "RATE_PAIR_REQUEST_PER_MIN": (
        "RATE_PAIR_REQUEST_PER_MIN_PER_IP",
        "RATE_PAIR_REQUEST_PER_MIN_PER_OFFER",
    ),
    "RATE_PAIR_COMPLETE_PER_MIN": (
        "RATE_PAIR_COMPLETE_PER_MIN_PER_IP",
        "RATE_PAIR_COMPLETE_PER_MIN_PER_PAIRING_ID",
    ),
    "RATE_TOKEN_PER_MIN": ("RATE_TOKEN_PER_MIN_PER_IP", "RATE_TOKEN_PER_MIN_PER_DEVICE_ID"),
    "LIMITER_TABLE_MAX": ("LIMITER_TABLE_MAX",),
    "OFFER_MAX_FAILURES": ("OFFER_MAX_FAILURES",),
    "SAS_MAX_MISMATCHES": ("SAS_MAX_MISMATCHES",),
    "DEVICE_NAME_MAX_BYTES": ("DEVICE_NAME_MAX_BYTES",),
    "Snapshot limit": ("SNAPSHOT_LIMIT_DEFAULT", "SNAPSHOT_LIMIT_MAX"),
    "History limit": ("HISTORY_LIMIT_DEFAULT", "HISTORY_LIMIT_MAX"),
}


def _section_13(doc: str) -> dict[str, list[int]]:
    table = {}
    for name_cell, value_cell, *_ in _rows(_section(doc, "## 13. Constants", "## 14.")):
        table[name_cell.replace("`", "")] = _ints(value_cell)
    return table


def test_section_13_rows_are_all_mapped(doc: str) -> None:
    assert set(_section_13(doc)) == set(SECTION_13)


@pytest.mark.parametrize("row", sorted(SECTION_13))
def test_section_13_value_matches(doc: str, row: str) -> None:
    expected = _section_13(doc)[row]
    attrs = SECTION_13[row]
    assert len(expected) == len(attrs), f"{row}: contract lists {expected}"
    assert [getattr(c, a) for a in attrs] == expected


def test_section_13_values_are_plain_ints() -> None:
    for attrs in SECTION_13.values():
        for a in attrs:
            value = getattr(c, a)
            assert type(value) is int, a  # never bool or float (TR-10 spirit)


def test_offer_ttl_within_note_bound() -> None:
    assert c.OFFER_TTL_S <= 600  # §13 note: "server-fixed; <= 600"


# ---------------------------------------------------------------------------------------------
# V-1 wire identifiers
# ---------------------------------------------------------------------------------------------


def _v1(doc: str) -> dict[str, list[str]]:
    block = _section(doc, "**V-1. v1 wire identifiers**", "**Why v1 does not keep")
    return {row[0]: _ticks(row[1]) for row in _rows(block)}


def test_v1_identifiers(doc: str) -> None:
    v1 = _v1(doc)
    assert v1["HTTP path prefix"] == [c.PATH_PREFIX]
    assert v1["QR payload prefix"] == [c.QR_PREFIX]
    assert v1["QR `v`, request `v`, `/ready` `versions`"] == [str(c.PROTOCOL_VERSION)]
    assert c.SUPPORTED_VERSIONS == (c.PROTOCOL_VERSION,)
    assert v1["Signature transcript tags"] == [t.decode("ascii") for t in c.TRANSCRIPT_TAGS]
    assert v1["Hash domain tags"] == [t.decode("ascii") for t in c.HASH_DOMAIN_TAGS]
    assert len(v1) == 5


def test_transcript_tag_constants() -> None:
    assert c.TRANSCRIPT_TAGS == (
        c.TAG_PAIR_REQ,
        c.TAG_PAIR_RESP,
        c.TAG_PAIR_DONE,
        c.TAG_TOKEN,
        c.TAG_SELF_REVOKE,
    )
    assert c.HASH_DOMAIN_TAGS == (c.TAG_OFFER, c.TAG_HOST)
    assert all(t.startswith(b"HMP1-") for t in c.TRANSCRIPT_TAGS + c.HASH_DOMAIN_TAGS)


def test_contract_revision(doc: str) -> None:
    assert c.CONTRACT_REVISION == "1.0"
    assert '"contract":"1.0"' in doc  # PR0-1


# ---------------------------------------------------------------------------------------------
# ERR-2, ERR-2a, ERR-3
# ---------------------------------------------------------------------------------------------


def _definitive(cell: str) -> c.SubmitDefinitive:
    cell = cell.replace("*", "").strip()
    if cell.startswith("only if"):
        return c.SubmitDefinitive.ONLY_IF_FLAGGED
    if cell.startswith("yes"):
        return c.SubmitDefinitive.YES
    if cell.startswith("no"):
        return c.SubmitDefinitive.NO
    assert cell == "—", cell
    return c.SubmitDefinitive.NOT_APPLICABLE


def _err2(doc: str) -> dict[str, tuple[frozenset[int], c.SubmitDefinitive]]:
    block = _section(doc, "**ERR-2. Error table.**", "**ERR-2a.")
    table = {}
    for row in _rows(block):
        assert len(row) == 5, row
        code = _ticks(row[0])[0]
        table[code] = (frozenset(_ints(row[1])), _definitive(row[3]))
    return table


def test_err2_codes_match(doc: str) -> None:
    assert set(_err2(doc)) == {code.value for code in c.ErrorCode}
    assert set(c.ERROR_TABLE) == set(c.ErrorCode)


def test_err2_table_order(doc: str) -> None:
    assert list(_err2(doc)) == [code.value for code in c.ERROR_TABLE]


@pytest.mark.parametrize("code", list(c.ErrorCode))
def test_err2_row_matches(doc: str, code: c.ErrorCode) -> None:
    http, definitive = _err2(doc)[code.value]
    spec = c.ERROR_TABLE[code]
    assert spec.code is code
    assert spec.http == http
    assert spec.definitive is definitive


def test_err1_extras(doc: str) -> None:
    block = _section(doc, "**ERR-1. Body.**", "**ERR-2.")
    line = next(ln for ln in block.splitlines() if "only allowed extras" in ln)
    assert set(_ticks(line)) - {"error", "AuthzState"} == set(c.ERROR_EXTRAS_ALLOWED)
    assert c.ERROR_TOP_LEVEL_SIBLING == "guarantees"


def test_err2a_refusals(doc: str) -> None:
    block = _section(doc, "**ERR-2a.", "**ERR-3.")
    whys = re.findall(r'`503 other \{why:"([a-z_]+)"\}`', block)
    assert whys == [
        c.OtherWhy.HERMES_BUILD_UNSUPPORTED.value,
        c.OtherWhy.HERMES_READ_DEPENDENCY_MISSING.value,
    ]
    assert set(c.READ_COMPAT_REFUSALS) == {c.OtherWhy(w) for w in whys}
    for why, refusal in c.READ_COMPAT_REFUSALS.items():
        assert refusal.why is why
        assert (refusal.http, refusal.code) == (503, c.ErrorCode.OTHER)
        assert refusal.definitive is c.SubmitDefinitive.YES  # "Definitive for submit: yes"
    assert "every route except `/ready`" in block
    assert c.READ_COMPAT_EXEMPT_PATH == "/hmp/v1/ready"


def test_err3_per_bot_gate(doc: str) -> None:
    block = _section(doc, "**ERR-3. Per-bot gate.**", "**ERR-4.")
    expected: dict[str, tuple[int, str, str | None]] = {}
    for states_cell, response_cell in _rows(block):
        response = _ticks(response_cell)[0]  # e.g. `403 forbidden {authz}`
        status, code = response.split()[:2]
        why = re.search(r'why:"([a-z_]+)"', response)
        for state in _ticks(states_cell):
            expected[state] = (int(status), code, why.group(1) if why else None)
    actual = {
        state.value: (g.http, g.code.value, g.why.value if g.why else None)
        for state, g in c.PER_BOT_GATE_REFUSALS.items()
    }
    assert actual == expected
    assert c.AuthzState.AUTHORIZED not in c.PER_BOT_GATE_REFUSALS


def test_err4_definitive_tags(doc: str) -> None:
    block = _section(doc, "**ERR-4.", "## 5.")
    first = next(ln for ln in block.splitlines() if "definitive only for these exit tags" in ln)
    tags = _ticks(first.split("exit tags:", 1)[1])
    assert set(tags) == set(c.DEFINITIVE_OTHER_TAGS)


# ---------------------------------------------------------------------------------------------
# AuthzState, resets, guarantees
# ---------------------------------------------------------------------------------------------


def test_authz_states_cover_contract(doc: str) -> None:
    roster = re.search(r'"authz":("authorized"[^}\]]+)\}', doc)
    assert roster is not None
    roster_states = set(re.findall(r'"([a-z_]+)"', roster.group(1)))
    # RO-1 lists five; ERR-2/ERR-3 add not_served.
    assert roster_states | {"not_served"} == {s.value for s in c.AuthzState}


def test_history_reset_reasons(doc: str) -> None:
    m = re.search(r'"reset":\{"reason":("[^}]+?), "snapshot_required"', doc)
    assert m is not None
    reasons = set(re.findall(r'"([a-z_]+)"', m.group(1)))
    assert reasons == {r.value for r in c.HISTORY_RESET_REASONS}


def test_tail_reset_reasons(doc: str) -> None:
    block = _section(doc, "**EV-2. Resume**", "**EV-3.")
    reasons = {_ticks(row[0])[0] for row in _rows(block)}
    assert reasons == {r.value for r in c.TAIL_RESET_REASONS}


def test_capability_floors(doc: str) -> None:
    block = _section(doc, "**GU-2. Runtime derivation**", "**GU-2a.")
    table = {}
    for flag_cell, key_cell, floor_cell in _rows(block):
        table[_ticks(flag_cell)[0]] = (_ticks(key_cell)[0], _ints(floor_cell)[0])
    assert table == dict(c.CAPABILITY_FLOORS)
    assert set(c.GUARANTEE_FLAGS) == set(table)


def test_grace_tag_is_server_internal() -> None:
    """Research R16 (CS-13): `HMP1-GRACE` derives P5 successors. It is not a V-1 wire tag."""
    research = (HMP_V1.parents[3] / "specs" / "001-connect-and-browse" / "research.md").read_text(
        encoding="utf-8"
    )
    assert 'transcript("HMP1-GRACE"' in research
    assert c.TAG_GRACE == b"HMP1-GRACE"
    assert c.TAG_GRACE not in c.TRANSCRIPT_TAGS
    assert c.TAG_GRACE not in c.HASH_DOMAIN_TAGS
