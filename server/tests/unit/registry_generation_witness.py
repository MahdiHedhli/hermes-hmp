"""Exact test-only inverse of e1d88b6f permission-generation source additions.

This preserves the historical byte witness; no new runtime/allocation qualification.
"""

import hashlib

APPROVED_COMMIT = "e1d88b6f62a99068e8bd5c69de5ca099f2afcfd6"
CURRENT_SHA256 = "f0b040c142945eead90befac8df40ffefff89239597ea4c4fb0c2ac9d5682f64"
ORIGINAL_SHA256 = "b49e6e6205805f38144e769f742f6e3ee918536aa6dd5f66e6c8096d8f77c2b2"

REVERSES = (
    (
        (
            "    user_id: str\n    instance_id: str\n    profile: str\n "
            "   permission_generation: tuple[int, ...] = ()\n\n    def "
            '__post_init__(self) -> None:\n        for name in ("devic'
            'e_id", "user_id", "instance_id", "profile"):\n           '
            " _text(getattr(self, name))\n        _permission_generati"
            "on(self.permission_generation)\n\n    def __repr__(self) -"
            '> str:\n        return "Caller()"\n\n    __str__ = __repr__'
            "\n\n\ndef _permission_generation(value: tuple[int, ...]) ->"
            " None:\n    if (type(value) is not tuple or len(value) no"
            "t in (0, 4)\n            or any(type(item) is not int or "
            "not -1 <= item <= 2 ** 63 - 1 for item in value)):\n     "
            "   raise RegistryRefusal from None\n\n\n@dataclass(frozen=T"
            "rue, slots=True, repr=False)\n"
        ),
        (
            "    user_id: str\n    instance_id: str\n    profile: str\n\n"
            "    def __post_init__(self) -> None:\n        for name in"
            ' ("device_id", "user_id", "instance_id", "profile"):\n   '
            "         _text(getattr(self, name))\n\n    def __repr__(se"
            'lf) -> str:\n        return "Caller()"\n\n    __str__ = __r'
            "epr__\n\n\n@dataclass(frozen=True, slots=True, repr=False)\n"
        ),
    ),
    (
        (
            "    tip: str\n    tool_row_id: int\n    raw_digest: bytes\n"
            "    permission_generation: tuple[int, ...] = ()\n\n    def"
            ' __post_init__(self) -> None:\n        for name in ("devi'
            'ce_id", "user_id", "instance_id", "profile", "session_id'
            '", "tip"):\n            _text(getattr(self, name))\n      '
            "  _row_id(self.tool_row_id)\n        _digest(self.raw_dig"
            "est)\n        _permission_generation(self.permission_gene"
            "ration)\n        if type(self.kind) is not SessionKind:\n "
            "           raise RegistryRefusal from None\n\n"
        ),
        (
            "    tip: str\n    tool_row_id: int\n    raw_digest: bytes\n"
            "\n    def __post_init__(self) -> None:\n        for name i"
            'n ("device_id", "user_id", "instance_id", "profile", "se'
            'ssion_id", "tip"):\n            _text(getattr(self, name)'
            ")\n        _row_id(self.tool_row_id)\n        _digest(self"
            ".raw_digest)\n        if type(self.kind) is not SessionKi"
            "nd:\n            raise RegistryRefusal from None\n\n"
        ),
    ),
    (
        (
            "            and self.user_id == caller.user_id\n         "
            "   and self.instance_id == caller.instance_id\n          "
            "  and self.profile == caller.profile\n            and sel"
            "f.permission_generation == caller.permission_generation\n"
            "        )\n\n\n"
        ),
        (
            "            and self.user_id == caller.user_id\n         "
            "   and self.instance_id == caller.instance_id\n          "
            "  and self.profile == caller.profile\n        )\n\n\n"
        ),
    ),
)


def reverse_registry_permission_generations(text: str) -> str:
    assert type(text) is str
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == CURRENT_SHA256
    for addition, historical in REVERSES:
        assert text.count(addition) == 1
        text = text.replace(addition, historical, 1)
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == ORIGINAL_SHA256
    return text
