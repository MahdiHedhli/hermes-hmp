"""Bounded listener-memory PN-ISS-3 hint custody. No authority, persistence or logging.

Only the listener loop mints/maintains this map. Producers on other threads must
handoff to that loop (PN-DSP-2). Resolver lookups are strictly read-only.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from . import crypto, wire
from .prompts import PromptKey, RowView

HINT_CAP = 256
HINT_HARD_MAX_S = 3600
HINT_SETTLE_MARGIN_S = 60


@dataclass(frozen=True, repr=False)
class HintBinding:
    route_hash: bytes
    generation: int
    prompt_generation: int
    key: PromptKey
    minted_at: int


def hint_live(binding: HintBinding, view: RowView | None, now: int) -> bool:
    if now < binding.minted_at or now >= binding.minted_at + HINT_HARD_MAX_S:
        return False
    if view is None or view.generation != binding.prompt_generation or view.kind != "approval":
        return False
    if view.open_now:
        return True
    return (
        view.status != "open"
        and view.settled_at is not None
        and view.settled_at <= now < view.settled_at + HINT_SETTLE_MARGIN_S
    )


class HintMap:
    def __init__(self) -> None:
        self._entries: dict[str, HintBinding] = {}

    def __len__(self) -> int:
        return len(self._entries)

    def lookup(self, hint: str, *, now: int) -> HintBinding | None:
        binding = self._entries.get(hint)
        if binding is None or not binding.minted_at <= now < binding.minted_at + HINT_HARD_MAX_S:
            return None
        return binding

    def clear(self) -> None:
        self._entries.clear()

    def maintain(self, *, now: int, view: Callable[[HintBinding], RowView | None]) -> None:
        for hint, binding in tuple(self._entries.items()):
            if not hint_live(binding, view(binding), now):
                del self._entries[hint]

    def mint(
        self, binding: HintBinding, *, now: int, view: Callable[[HintBinding], RowView | None]
    ) -> str:
        if (
            type(binding.route_hash) is not bytes
            or len(binding.route_hash) != 32
            or type(binding.generation) is not int
            or not 1 <= binding.generation < 2**53
            or type(binding.prompt_generation) is not int
            or binding.prompt_generation < 1
            or binding.minted_at != now
            or not hint_live(binding, view(binding), now)
        ):
            raise ValueError("invalid push hint binding")
        self.maintain(now=now, view=view)
        if len(self._entries) >= HINT_CAP:
            # Prefer a settled/closed generation to a still-open row; then oldest mint.
            def priority(item):
                _, old = item
                current = view(old)
                return (
                    bool(
                        current is not None
                        and current.open_now
                        and current.generation == old.prompt_generation
                    ),
                    old.minted_at,
                )

            oldest = min(self._entries.items(), key=priority)[0]
            del self._entries[oldest]
        # A live collision is redrawn; no replacement or reuse of the old binding.
        while True:
            hint = wire.b64u_encode(crypto.random_bytes(32))
            if hint not in self._entries:
                self._entries[hint] = binding
                return hint
