"""Startup-bound YAML scanner/events for the native presentation reducer.

No YAML graph construction, filesystem or native authority. Dependency classes
are selected at listener setup, never named/imported by a phone request. This
shares the trusted installed parser premise; it is not executable attestation.
"""

from __future__ import annotations

from .presentation_budget import PresentationWorkLedger
from .presentation_yaml import (
    RAW_LIMIT,
    PresentationYamlError,
    YamlEvent,
    reduce_presentation_events,
)


class NativePresentationYaml:
    def __init__(self):
        # Fixed installed dependency, before a request/worker can be admitted.
        from yaml import error, events, tokens
        from yaml.loader import SafeLoader

        self._loader = SafeLoader
        self._error = error.YAMLError
        self._directive = tokens.DirectiveToken
        self._document = events.DocumentStartEvent
        self._scalar = events.ScalarEvent
        self._kinds = {
            events.StreamStartEvent: "stream_start",
            events.StreamEndEvent: "stream_end",
            events.DocumentStartEvent: "document_start",
            events.DocumentEndEvent: "document_end",
            events.MappingStartEvent: "mapping_start",
            events.MappingEndEvent: "mapping_end",
            events.SequenceStartEvent: "sequence_start",
            events.SequenceEndEvent: "sequence_end",
            events.ScalarEvent: "scalar",
            events.AliasEvent: "alias",
        }

    def _events(self, raw, work):
        styles = {None: "plain", "'": "single", '"': "double", "|": "literal", ">": "folded"}
        loader = None
        try:
            # The parser silently drops unknown directives; inspect tokens first.
            loader = self._loader(raw)
            try:
                while True:
                    work.tick()
                    if not loader.check_token():
                        break
                    work.charge_yaml_token()
                    token = loader.get_token()
                    if isinstance(token, self._directive):
                        raise PresentationYamlError("YAML_FEATURE")
                    token = None
            finally:
                loader.dispose()
                loader = None
            # Only one loader is live at a time; no construct/get_data methods.
            loader = self._loader(raw)
            try:
                while True:
                    work.tick()
                    if not loader.check_event():
                        break
                    event = loader.get_event()
                    kind = self._kinds.get(type(event))
                    if kind is None:
                        raise PresentationYamlError("EVENT_SCHEMA")
                    directives = ()
                    if isinstance(event, self._document) and (event.version or event.tags):
                        directives = ("explicit-directive",)
                    scalar = isinstance(event, self._scalar)
                    yield YamlEvent(
                        kind=kind,
                        value=event.value if scalar else None,
                        style=styles.get(event.style) if scalar else None,
                        anchor=getattr(event, "anchor", None),
                        tag=getattr(event, "tag", None),
                        directives=directives,
                    )
                    event = None
            finally:
                loader.dispose()
                loader = None
        except self._error:
            raise PresentationYamlError("PARSER_REFUSED") from None
        finally:
            # Do not let a failed generator retain token/event/raw aliases.
            raw = event = token = loader = None

    def parse(self, raw: bytes, work: PresentationWorkLedger):
        if (
            type(raw) is not bytes
            or not 1 <= len(raw) <= RAW_LIMIT
            or type(work) is not PresentationWorkLedger
        ):
            raise PresentationYamlError("NATIVE_YAML_SCOPE")
        work.begin_yaml()
        events = self._events(raw, work)
        try:
            return reduce_presentation_events(
                raw,
                events,
                clock=work.clock,
                deadline=work.deadline,
                charge_node=work.charge_yaml_node,
            )
        finally:
            events.close()
