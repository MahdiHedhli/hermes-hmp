"""Independent media permission DATA. It grants no approval or host-control authority."""
from __future__ import annotations

from typing import NamedTuple


def validate_media_scope(iid: str, device_id: str) -> None:
    if (type(iid) is not str or len(iid) != 52
            or any(char not in 'abcdefghijklmnopqrstuvwxyz234567' for char in iid)
            or type(device_id) is not str or not 1 <= len(device_id) <= 256
            or any(not 33 <= ord(char) <= 126 for char in device_id)):
        raise ValueError('invalid media permission scope')


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
        return '<MediaReadDecision redacted>'

    @property
    def generation(self) -> tuple[int, ...]:
        return (self.instance_epoch, self.revocation_epoch, self.revision,
                -1 if self.fallback_revision is None else self.fallback_revision)
