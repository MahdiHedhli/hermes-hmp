"""Test-only inverse of the exact committed media-permission generation delta.

Retain the historical frozen registry hash. Current permission/revocation
semantics are tested separately; stripping literal blocks is not runtime proof.
Unknown/changed/duplicate blocks refuse; unrelated bytes reach the old hash.
"""
from __future__ import annotations

EDITS = (
    (
        '''    user_id: str
    instance_id: str
    profile: str
    permission_generation: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        for name in ("device_id", "user_id", "instance_id", "profile"):
            _text(getattr(self, name))
        _permission_generation(self.permission_generation)

    def __repr__(self) -> str:
        return "Caller()"

    __str__ = __repr__


def _permission_generation(value: tuple[int, ...]) -> None:
    if (type(value) is not tuple or len(value) not in (0, 4)
            or any(type(item) is not int or not -1 <= item <= 2 ** 63 - 1 for item in value)):
        raise RegistryRefusal from None


@dataclass(frozen=True, slots=True, repr=False)
''',
        '''    user_id: str
    instance_id: str
    profile: str

    def __post_init__(self) -> None:
        for name in ("device_id", "user_id", "instance_id", "profile"):
            _text(getattr(self, name))

    def __repr__(self) -> str:
        return "Caller()"

    __str__ = __repr__


@dataclass(frozen=True, slots=True, repr=False)
''',
    ),
    (
        '''    tip: str
    tool_row_id: int
    raw_digest: bytes
    permission_generation: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        for name in ("device_id", "user_id", "instance_id", "profile", "session_id", "tip"):
            _text(getattr(self, name))
        _row_id(self.tool_row_id)
        _digest(self.raw_digest)
        _permission_generation(self.permission_generation)
        if type(self.kind) is not SessionKind:
            raise RegistryRefusal from None

''',
        '''    tip: str
    tool_row_id: int
    raw_digest: bytes

    def __post_init__(self) -> None:
        for name in ("device_id", "user_id", "instance_id", "profile", "session_id", "tip"):
            _text(getattr(self, name))
        _row_id(self.tool_row_id)
        _digest(self.raw_digest)
        if type(self.kind) is not SessionKind:
            raise RegistryRefusal from None

''',
    ),
    (
        '''            and self.user_id == caller.user_id
            and self.instance_id == caller.instance_id
            and self.profile == caller.profile
            and self.permission_generation == caller.permission_generation
        )


''',
        '''            and self.user_id == caller.user_id
            and self.instance_id == caller.instance_id
            and self.profile == caller.profile
        )


''',
    ),
)


def reverse_registry_permission_generation(source: str, name: str) -> str:
    if name != "local_media_registry.py":
        return source
    for accepted, historical in reversed(EDITS):
        assert source.count(accepted) == 1
        source = source.replace(accepted, historical, 1)
    return source
