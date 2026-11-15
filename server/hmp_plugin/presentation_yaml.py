"""Pure, closed BI1 projection from a separately qualified YAML event stream.

The input parser is deliberately absent. This module never loads a YAML object,
opens a file, or imports a YAML provider. A future owned worker must supply a
reviewed streaming YAML 1.1 event adapter and run this within its shared deadline.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

RAW_LIMIT = 65_536
NODE_LIMIT = 256
DEPTH_LIMIT = 8
SCALAR_UTF8_LIMIT = 1024
EVENT_LIMIT = 1024

_STRING_FIELDS = frozenset(
    {
        ("display_name",),
        ("ui_meta", "hermes-bots", "title"),
        ("ui_meta", "hermes-bots", "shape"),
        ("ui_meta", "hermes-bots", "color"),
    }
)
_CUSTOM_FIELD = ("ui_meta", "hermes-bots", "custom")
_FIELDS = _STRING_FIELDS | {_CUSTOM_FIELD}
_PREFIXES = frozenset(path[:n] for path in _FIELDS for n in range(len(path)))
_BOOL_TRUE = frozenset(("y", "Y", "yes", "Yes", "YES", "true", "True", "TRUE", "on", "On", "ON"))
_BOOL_FALSE = frozenset(
    ("n", "N", "no", "No", "NO", "false", "False", "FALSE", "off", "Off", "OFF")
)
_NULL = frozenset(("", "~", "null", "Null", "NULL"))
_INTEGER = re.compile(
    r"""^(?:[-+]?0b[0-1_]+|[-+]?0?[0-7_]+|[-+]?(?:0|[1-9][0-9_]*)
    |[-+]?0x[0-9a-fA-F_]+|[-+]?[1-9][0-9_]*(?::[0-5]?[0-9])+)$""",
    re.VERBOSE | re.ASCII,
)
_FLOAT = re.compile(
    r"""^(?:[-+]?(?:[0-9][0-9_]*)\.[0-9_]*(?:[eE][-+]?[0-9]+)?
    |[-+]?(?:[0-9][0-9_]*)(?:[eE][-+]?[0-9]+)
    |\.[0-9_]+(?:[eE][-+][0-9]+)?
    |[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\.[0-9_]*
    |[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN))$""",
    re.VERBOSE | re.ASCII,
)
_TIMESTAMP = re.compile(
    r"""^(?:[0-9]{4}-[0-9]{2}-[0-9]{2}
    |[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}
      (?:[Tt]|[ \t]+)[0-9]{1,2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]*)?
      (?:[ \t]*(?:Z|[-+][0-9]{1,2}(?::[0-9]{2})?))?)$""",
    re.VERBOSE | re.ASCII,
)


class PresentationYamlError(Exception):
    """Closed refusal; labels contain no YAML content."""

    def __init__(self, label: str):
        super().__init__(label)
        self.label = label


@dataclass(frozen=True)
class YamlEvent:
    """Minimal event-adapter envelope; parser/source parity is a later gate.

    ``style`` is one of plain/single/double/literal/folded for scalar events.
    ``tag`` is an explicit source tag, never a resolved implicit type.
    """

    kind: str
    value: str | None = None
    style: str | None = None
    anchor: str | None = None
    tag: str | None = None
    directives: tuple[str, ...] = ()


@dataclass(frozen=True)
class RawPresentationFields:
    display_name: str | None
    title: str | None
    shape: str | None
    color: str | None
    custom: bool | None


@dataclass
class _Frame:
    kind: str
    path: tuple[str, ...] | None
    expecting_key: bool = True
    pending_key: str | None = None
    seen: set[str] = field(default_factory=set)


def _scalar_type(value: str, style: str) -> tuple[str, str | bool | None]:
    if style != "plain":
        return "string", value
    if value in _BOOL_TRUE:
        return "bool", True
    if value in _BOOL_FALSE:
        return "bool", False
    if value in _NULL:
        return "null", None
    if value in ("<<", "=") or _INTEGER.fullmatch(value) or _FLOAT.fullmatch(value):
        return "other", value
    if _TIMESTAMP.fullmatch(value):
        return "other", value
    return "string", value


def _event_schema(event: object) -> YamlEvent:
    if type(event) is not YamlEvent or type(event.kind) is not str:
        raise PresentationYamlError("EVENT_SCHEMA")
    if len(event.kind) > 32:
        raise PresentationYamlError("EVENT_SCHEMA")
    if event.value is not None and type(event.value) is not str:
        raise PresentationYamlError("EVENT_SCHEMA")
    if event.style is not None and type(event.style) is not str:
        raise PresentationYamlError("EVENT_SCHEMA")
    if event.anchor is not None or event.tag is not None or event.directives:
        raise PresentationYamlError("YAML_FEATURE")
    if type(event.directives) is not tuple:
        raise PresentationYamlError("EVENT_SCHEMA")
    if event.kind == "scalar":
        if event.value is None or event.style not in (
            "plain",
            "single",
            "double",
            "literal",
            "folded",
        ):
            raise PresentationYamlError("EVENT_SCHEMA")
    elif event.value is not None or event.style is not None:
        raise PresentationYamlError("EVENT_SCHEMA")
    return event


def reduce_presentation_events(
    raw: bytes,
    events: Iterable[YamlEvent],
    *,
    clock: Callable[[], float],
    deadline: float,
    charge_node: Callable[[], None] | None = None,
) -> RawPresentationFields:
    """Validate the whole stream before returning any allowlisted fields.

    The trusted worker must parse ``raw`` into ``events`` with a separately
    reviewed YAML 1.1 streaming adapter. This reducer is not an event/raw
    correspondence proof and does not make an unqualified parser safe.
    """
    if type(raw) is not bytes or not 1 <= len(raw) <= RAW_LIMIT:
        raise PresentationYamlError("RAW_SIZE")
    if type(deadline) is not float or not 0 < deadline < float("inf"):
        raise PresentationYamlError("DEADLINE_SCHEMA")
    text = raw[3:] if raw.startswith(b"\xef\xbb\xbf") else raw
    try:
        decoded = text.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise PresentationYamlError("RAW_UTF8") from exc
    if "\x00" in decoded or decoded.startswith("\ufeff"):
        raise PresentationYamlError("RAW_UTF8")

    def tick() -> None:
        try:
            now = clock()
        except BaseException as exc:
            raise PresentationYamlError("CLOCK") from exc
        if type(now) is not float or not math.isfinite(now) or now < 0 or not now < deadline:
            raise PresentationYamlError("DEADLINE")

    try:
        iterator = iter(events)
    except BaseException as exc:
        raise PresentationYamlError("EVENT_ITERATOR") from exc

    phase = 0  # stream, document, root, document-end, stream-end.
    frames: list[_Frame] = []
    nodes = 0
    event_count = 0
    selected: dict[tuple[str, ...], str | bool | None] = {}

    def claim_value() -> tuple[str, ...] | None:
        if not frames:
            if phase != 2:
                raise PresentationYamlError("ROOT_SCHEMA")
            return ()
        parent = frames[-1]
        if parent.kind == "sequence":
            return None
        if parent.expecting_key or parent.pending_key is None:
            raise PresentationYamlError("MAPPING_GRAMMAR")
        path = (*parent.path, parent.pending_key) if parent.path is not None else None
        parent.pending_key = None
        parent.expecting_key = True
        return path

    while True:
        tick()
        try:
            event = next(iterator)
        except StopIteration:
            break
        except BaseException as exc:
            raise PresentationYamlError("EVENT_ADVANCE") from exc
        tick()
        event_count += 1
        if event_count > EVENT_LIMIT:
            raise PresentationYamlError("EVENT_LIMIT")
        event = _event_schema(event)

        if event.kind == "stream_start" and phase == 0:
            phase = 1
            continue
        if event.kind == "document_start" and phase == 1:
            phase = 2
            continue
        if event.kind == "document_end" and phase == 3:
            phase = 4
            continue
        if event.kind == "stream_end" and phase == 4:
            phase = 5
            continue
        if phase != 2 or event.kind in ("alias", "document_start", "stream_start"):
            raise PresentationYamlError("DOCUMENT_GRAMMAR")

        if event.kind in ("mapping_start", "sequence_start"):
            if charge_node is not None:
                charge_node()
            nodes += 1
            if nodes > NODE_LIMIT or len(frames) >= DEPTH_LIMIT:
                raise PresentationYamlError("STRUCTURE_LIMIT")
            path = claim_value()
            if not frames and event.kind != "mapping_start":
                raise PresentationYamlError("ROOT_SCHEMA")
            if path in _FIELDS or (path in _PREFIXES and event.kind != "mapping_start"):
                raise PresentationYamlError("SELECTED_TYPE")
            tracked = path if path in _PREFIXES else None
            frames.append(_Frame(event.kind.removesuffix("_start"), tracked))
            continue

        if event.kind in ("mapping_end", "sequence_end"):
            kind = event.kind.removesuffix("_end")
            if not frames or frames[-1].kind != kind:
                raise PresentationYamlError("CONTAINER_GRAMMAR")
            frame = frames[-1]
            if frame.kind == "mapping" and not frame.expecting_key:
                raise PresentationYamlError("MAPPING_GRAMMAR")
            frames.pop()
            if not frames:
                phase = 3
            continue

        if event.kind != "scalar" or not frames:
            raise PresentationYamlError("EVENT_GRAMMAR")
        if charge_node is not None:
            charge_node()
        nodes += 1
        if nodes > NODE_LIMIT:
            raise PresentationYamlError("NODE_LIMIT")
        value = event.value
        style = event.style
        if value is None or style is None:
            raise PresentationYamlError("EVENT_SCHEMA")
        if len(value) > SCALAR_UTF8_LIMIT:
            raise PresentationYamlError("SCALAR_LIMIT")
        try:
            scalar_bytes = value.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise PresentationYamlError("SCALAR_UTF8") from exc
        if len(scalar_bytes) > SCALAR_UTF8_LIMIT:
            raise PresentationYamlError("SCALAR_LIMIT")
        scalar_kind, resolved = _scalar_type(value, style)
        frame = frames[-1]
        if frame.kind == "mapping" and frame.expecting_key:
            if scalar_kind != "string" or value == "<<" or value in frame.seen:
                raise PresentationYamlError("MAPPING_KEY")
            frame.seen.add(value)
            frame.pending_key = value
            frame.expecting_key = False
            continue
        path = claim_value()
        if path in _PREFIXES:
            raise PresentationYamlError("SELECTED_TYPE")
        if path in _STRING_FIELDS:
            if scalar_kind != "string":
                raise PresentationYamlError("SELECTED_TYPE")
            selected[path] = value
        elif path == _CUSTOM_FIELD:
            if scalar_kind not in ("bool", "null"):
                raise PresentationYamlError("SELECTED_TYPE")
            selected[path] = resolved

    tick()
    if phase != 5 or frames:
        raise PresentationYamlError("DOCUMENT_INCOMPLETE")
    return RawPresentationFields(
        display_name=selected.get(("display_name",)),
        title=selected.get(("ui_meta", "hermes-bots", "title")),
        shape=selected.get(("ui_meta", "hermes-bots", "shape")),
        color=selected.get(("ui_meta", "hermes-bots", "color")),
        custom=selected.get(_CUSTOM_FIELD),
    )
