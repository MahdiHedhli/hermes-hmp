"""One worker's nonresetting presentation work ledger, never authority/custody.

File phases must debit before I/O; YAML/raster phases debit before processing.
This class owns no descriptors or processes and grants no permission to read.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import ClassVar


class PresentationBudgetError(ValueError):
    def __init__(self) -> None:
        super().__init__("BI1_WORK_CREDIT_REFUSED")


class PresentationWorkLedger:
    _LIMITS: ClassVar[Mapping[str, int]] = MappingProxyType(
        {
            "read_bytes": 4_131_076,
            "hash_bytes": 2_000_000,
            "opens": 80,
            "metadata": 1024,
            "path_bytes": 32768,
            "yaml_nodes": 256,
            "yaml_tokens": 2048,
            "raster_units": 10000,
        }
    )

    def __init__(
        self,
        *,
        clock: Callable[[], float],
        deadline: float,
        parent_counts: dict[str, int] | None = None,
        parent_home: str | None = None,
    ):
        if type(deadline) is not float or not 0 < deadline < float("inf"):
            raise PresentationBudgetError
        self.clock = clock
        self.deadline = deadline
        self._counts = dict.fromkeys(self._LIMITS, 0)
        self._phases: set[str] = set()
        self._poisoned = False
        if parent_counts is not None or parent_home is not None:
            self._counts = self.validate_parent_counts(parent_home, parent_counts)
            self._phases.add("parent_policy")
        self.tick()

    @classmethod
    def validate_parent_counts(cls, home: object, counts: object) -> dict[str, int]:
        """Validate/copy the exact successful parent schedule, never authority."""
        if type(home) is not str or not home.startswith("/") or home == "/" or "\x00" in home:
            raise PresentationBudgetError
        parts = home[1:].split("/")
        if len(parts) + 1 > 32 or any(part in ("", ".", "..") for part in parts):
            raise PresentationBudgetError
        try:
            encoded = home.encode("utf-8", errors="strict")
        except UnicodeError:
            raise PresentationBudgetError from None
        if len(encoded) > 4096 or type(counts) is not dict or counts.keys() != cls._LIMITS.keys():
            raise PresentationBudgetError
        if any(
            type(value) is not int or not 0 <= value <= cls._LIMITS[key]
            for key, value in counts.items()
        ):
            raise PresentationBudgetError
        expected = dict.fromkeys(cls._LIMITS, 0)
        expected.update(
            opens=len(parts) + 1,
            metadata=4 * (len(parts) + 1),
            path_bytes=3 * (1 + sum(len(part.encode("utf-8")) for part in parts)),
        )
        if counts != expected:
            raise PresentationBudgetError
        return dict(counts)

    def begin_parent_policy(self) -> None:
        self._phase("parent_policy")

    def tick(self) -> None:
        try:
            now = self.clock()
        except BaseException:
            self._poisoned = True
            raise PresentationBudgetError from None
        if self._poisoned or type(now) is not float or not 0 <= now < self.deadline:
            self._poisoned = True
            raise PresentationBudgetError

    def _phase(self, phase: str) -> None:
        self.tick()
        if phase in self._phases:
            self._poisoned = True
            raise PresentationBudgetError
        self._phases.add(phase)

    def _charge(self, key: str, amount: int = 1) -> None:
        self.tick()
        if type(amount) is not int or amount < 1 or amount > self._LIMITS[key] - self._counts[key]:
            self._poisoned = True
            raise PresentationBudgetError
        self._counts[key] += amount

    def begin_file(self) -> None:
        self._phase("file")

    def begin_yaml(self) -> None:
        self._phase("yaml")

    def charge_read_bytes(self, amount: int) -> None:
        self._charge("read_bytes", amount)

    def charge_open(self) -> None:
        self._charge("opens")

    def charge_metadata(self) -> None:
        self._charge("metadata")

    def charge_path_bytes(self, amount: int) -> None:
        self._charge("path_bytes", amount)

    def charge_yaml_node(self) -> None:
        self._charge("yaml_nodes")

    def charge_yaml_token(self) -> None:
        self._charge("yaml_tokens")

    def charge_scan(self) -> None:
        self._phase("raster")

    def charge_unit(self) -> None:
        self._charge("raster_units")

    def charge_hash_bytes(self, count: int) -> None:
        if type(count) is not int or not 1 <= count <= 65536:
            self._poisoned = True
            raise PresentationBudgetError
        self._charge("hash_bytes", count)

    def snapshot(self) -> dict[str, int]:
        self.tick()
        return dict(self._counts)
