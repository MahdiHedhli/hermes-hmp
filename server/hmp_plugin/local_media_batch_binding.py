"""Closed result and pure decisions for the bridge's media batch binding (C6b).

INERT: no production module imports this one at module scope, and nothing at start-up loads it.
The bridge loads it only inside `bind_media_batch` and the eligibility helper. It imports the
accepted batch module (for `_Closed`, `_initialized` and the batch reasons, by identity), the
accepted sidecar module, and the standard library. It does no I/O, reads no native object, keeps
no cache and logs nothing.

Binding is not authority. It records which of one response's candidate selectors a fresh, bracketed
batch scan accepted for ONE eligible session kind, so a later slice may mint descriptors for
exactly those. A mint still needs its own owner, flag and qualification gates, and a fetch still
re-proves everything. The wrapper holds only the sidecar object (by identity), a closed kind and
reason, the accepted row ids newest-first and six bounded counts: no home, path, name, digest,
title, chain or content, and never the batch result.

Eligibility is decided from two independent proofs (the caller's own Phone session; the canonical
Bot Chat lineage), each with three outcomes: proven, closed negative, or uncertain. `classify`
combines them: any uncertain proof closes the whole binding; exactly one proven kind may qualify.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Any, Final

from . import local_media_active_batch as _batch
from . import local_media_sidecar as _sidecar

MAX_CHAIN: Final = 100  # the bridge's parent-walk bound
CANONICAL_TITLE: Final = "Bot Chat"

OK: Final = _batch.OK
NOT_CANDIDATES: Final = "not_candidates"
PROVENANCE_MISMATCH: Final = "provenance_mismatch"
HOME_INVALID: Final = "home_invalid"
NOT_ELIGIBLE: Final = "not_eligible"
ELIGIBILITY_UNCERTAIN: Final = "eligibility_uncertain"
BINDING_REASONS: Final = frozenset(
    _batch.REASONS
    | {NOT_CANDIDATES, PROVENANCE_MISMATCH, HOME_INVALID, NOT_ELIGIBLE, ELIGIBILITY_UNCERTAIN}
)

PROVEN: Final = "proven"
NEGATIVE: Final = "negative"
UNCERTAIN: Final = "uncertain"


class MintKind(Enum):
    """Session kinds a binding can prove. Values equal `local_media_registry.SessionKind`."""

    BOT_CHAT = "bot_chat"
    PHONE = "phone"


# A proof outcome is `(status, tip)`: `tip` is the exact resolved tip only when proven.
Proof = tuple[str, "str | None"]
Eligibility = tuple[str, "MintKind | None", "str | None"]

PROOF_NEGATIVE: Final[Proof] = (NEGATIVE, None)
PROOF_UNCERTAIN: Final[Proof] = (UNCERTAIN, None)


def proven(tip: str) -> Proof:
    return (PROVEN, tip)


def _valid_proof(proof: object) -> bool:
    if type(proof) is not tuple or len(proof) != 2:
        return False
    status, tip = proof
    if status == PROVEN:
        return type(tip) is str and bool(tip)
    return status in (NEGATIVE, UNCERTAIN) and tip is None


def classify(phone: object, bot: object, expected_tip: object) -> Eligibility:
    """`(reason, kind, tip)` from the two proofs and the tip the caller expects.

    Any uncertain (or malformed) proof is `eligibility_uncertain`, even when the other proves.
    Neither proven, or both, is `not_eligible`. Exactly one proven kind whose tip differs from the
    expected tip is `provenance_mismatch`; otherwise `ok` with that kind and its tip."""
    if not _valid_proof(phone) or not _valid_proof(bot) or type(expected_tip) is not str:
        return (ELIGIBILITY_UNCERTAIN, None, None)
    phone_status, phone_tip = phone  # type: ignore[misc]
    bot_status, bot_tip = bot  # type: ignore[misc]
    if UNCERTAIN in (phone_status, bot_status):
        return (ELIGIBILITY_UNCERTAIN, None, None)
    phone_ok, bot_ok = phone_status == PROVEN, bot_status == PROVEN
    if phone_ok == bot_ok:
        return (NOT_ELIGIBLE, None, None)
    kind, tip = (MintKind.PHONE, phone_tip) if phone_ok else (MintKind.BOT_CHAT, bot_tip)
    if tip != expected_tip:
        return (PROVENANCE_MISMATCH, None, None)
    return (OK, kind, tip)


def strict_home(home: object) -> bool:
    """A lexically strict home: exact nonempty absolute normalized text, no NUL, no `..` part.

    Lexical only. No stat, open or resolve: that a home is a real, non-symlink directory is not
    provable here and belongs to the fetch-time file checks. A POSIX `//` prefix passes."""
    if type(home) is not str or not home or "\0" in home:
        return False
    if not os.path.isabs(home) or home != os.path.normpath(home):
        return False
    return ".." not in home.split("/")


# --------------------------------------------------------------------------- the closed result

_COUNT_NAMES: Final = ("candidates", "accepted", "pages", "rows", "budget_used", "declared")


class MediaBatchBinding(_batch._Closed):
    """The closed outcome of one bind. Never serializable, copyable or mutable.

    `kind` and a non-empty `accepted` exist only when `reason == ok`; an ok binding with no
    accepted ids mints nothing. `accepted` is strictly descending (newest first), unique, at most
    128, and a subset of the sidecar's own candidate row ids. `session_id` and `tip` are the
    sidecar's views, `str | None`; a consumer checks `ok` and `binding.sidecar is result.sidecar`
    first.

    The six counts are type-checked (exact non-negative ints, cross-checked against the sidecar and
    `accepted`) but the constructor sets no magnitude cap; they are bounded only because the
    actual batch counters that feed them are."""

    __slots__ = ("_accepted", "_counts", "_kind", "_reason", "_sidecar")

    def __init__(
        self,
        sidecar: _sidecar.MediaSidecar,
        kind: MintKind | None,
        reason: str,
        accepted: tuple[int, ...],
        counts: tuple[int, int, int, int, int, int],
    ) -> None:
        if _batch._initialized(self):
            raise TypeError("already initialized")
        if type(sidecar) is not _sidecar.MediaSidecar or reason not in BINDING_REASONS:
            raise ValueError("invalid binding")
        if (type(kind) is not MintKind) if reason == OK else (kind is not None):
            raise ValueError("invalid binding")
        if type(accepted) is not tuple or len(accepted) > _batch.MAX_SELECTORS:
            raise ValueError("invalid binding")
        if accepted and reason != OK:
            raise ValueError("invalid binding")
        known = {c.tool_row_id for c in sidecar.candidates}
        previous: int | None = None
        for row_id in accepted:
            if (
                type(row_id) is not int
                or row_id not in known
                or (previous is not None and row_id >= previous)
            ):
                raise ValueError("invalid binding")
            previous = row_id
        if type(counts) is not tuple or len(counts) != len(_COUNT_NAMES):
            raise ValueError("invalid binding")
        if any(type(n) is not int or n < 0 for n in counts):
            raise ValueError("invalid binding")
        if counts[0] != len(sidecar.candidates) or counts[1] != len(accepted):
            raise ValueError("invalid binding")
        object.__setattr__(self, "_sidecar", sidecar)
        object.__setattr__(self, "_kind", kind)
        object.__setattr__(self, "_reason", reason)
        object.__setattr__(self, "_accepted", accepted)
        object.__setattr__(self, "_counts", counts)

    @property
    def sidecar(self) -> _sidecar.MediaSidecar:
        return self._sidecar

    @property
    def kind(self) -> MintKind | None:
        return self._kind

    @property
    def reason(self) -> str:
        return self._reason

    @property
    def ok(self) -> bool:
        return self._reason == OK

    @property
    def accepted(self) -> tuple[int, ...]:
        return self._accepted

    @property
    def session_id(self) -> str | None:
        return self._sidecar.session_id

    @property
    def tip(self) -> str | None:
        return self._sidecar.query_tip

    def report(self) -> dict[str, Any]:
        """Closed metadata only: reason, kind name and counts. No id, digest, path or content."""
        return {
            "reason": self._reason,
            "kind": None if self._kind is None else self._kind.value,
            **dict(zip(_COUNT_NAMES, self._counts, strict=True)),
        }
