"""Independent media permission DATA. It grants no approval or host-control authority."""

from __future__ import annotations

from typing import NamedTuple


def validate_media_scope(iid: str, device_id: str) -> None:
    if (
        type(iid) is not str
        or len(iid) != 52
        or any(char not in "abcdefghijklmnopqrstuvwxyz234567" for char in iid)
        or iid[-1] not in "aq"
        or type(device_id) is not str
        or not 1 <= len(device_id) <= 256
        or any(not 33 <= ord(char) <= 126 for char in device_id)
    ):
        raise ValueError("invalid media permission scope")


class MediaReadDecision(NamedTuple):
    iid: str
    device_id: str
    user_id: str
    allowed: bool | None
    revision: int
    instance_epoch: int
    revocation_epoch: int
    fallback_controls: bool | None
    fallback_revision: int | None

    def __repr__(self):
        return "<MediaReadDecision redacted>"

    def validate(self) -> None:
        validate_media_scope(self.iid, self.device_id)
        if (
            type(self.user_id) is not str
            or not 1 <= len(self.user_id) <= 256
            or any(not 33 <= ord(char) <= 126 for char in self.user_id)
            or (self.allowed is not None and type(self.allowed) is not bool)
            or any(
                type(value) is not int or not 0 <= value <= 2**63 - 1
                for value in (self.revision, self.instance_epoch, self.revocation_epoch)
            )
        ):
            raise ValueError("invalid media decision fields")
        if self.allowed is None:
            if (
                (self.fallback_controls is not None and type(self.fallback_controls) is not bool)
                or type(self.fallback_revision) is not int
                or not 0 <= self.fallback_revision <= 2**63 - 1
                or (self.fallback_controls is not None and self.fallback_revision < 1)
            ):
                raise ValueError("invalid media fallback fields")
        elif (
            self.revision < 1
            or self.fallback_controls is not None
            or self.fallback_revision is not None
        ):
            raise ValueError("invalid explicit media decision fields")

    @property
    def generation(self) -> tuple[int, ...]:
        return (
            self.instance_epoch,
            self.revocation_epoch,
            self.revision,
            -1 if self.fallback_revision is None else self.fallback_revision,
        )
