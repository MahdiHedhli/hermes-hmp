"""Worker-only PyYAML event adapter; never constructs a profile object graph.

Only the closed presentation reducer can select fields. Parser errors are
content-free. Input, events, nodes, scalar sizes and deadline remain bounded by
that reducer; the disposable worker's supervisor must enforce its hard deadline.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator

from .presentation_yaml import (
    RAW_LIMIT, PresentationYamlError, RawPresentationFields, YamlEvent,
    reduce_presentation_events,
)


def _events(raw: bytes) -> Iterator[YamlEvent]:
    import yaml

    kinds = {
        yaml.events.StreamStartEvent: 'stream_start',
        yaml.events.StreamEndEvent: 'stream_end',
        yaml.events.DocumentStartEvent: 'document_start',
        yaml.events.DocumentEndEvent: 'document_end',
        yaml.events.MappingStartEvent: 'mapping_start',
        yaml.events.MappingEndEvent: 'mapping_end',
        yaml.events.SequenceStartEvent: 'sequence_start',
        yaml.events.SequenceEndEvent: 'sequence_end',
        yaml.events.ScalarEvent: 'scalar',
        yaml.events.AliasEvent: 'alias',
    }
    styles = {None: 'plain', "'": 'single', '"': 'double', '|': 'literal', '>': 'folded'}
    try:
        for event in yaml.parse(raw, Loader=yaml.SafeLoader):
            kind = kinds.get(type(event))
            if kind is None:
                raise PresentationYamlError('EVENT_SCHEMA')
            directives = ()
            if isinstance(event, yaml.events.DocumentStartEvent) and (event.version or event.tags):
                directives = ('explicit-directive',)
            scalar = isinstance(event, yaml.events.ScalarEvent)
            yield YamlEvent(
                kind=kind,
                value=event.value if scalar else None,
                style=styles.get(event.style) if scalar else None,
                anchor=getattr(event, 'anchor', None),
                tag=getattr(event, 'tag', None),
                directives=directives,
            )
    except yaml.YAMLError:
        raise PresentationYamlError('PARSER_REFUSED') from None


def parse_presentation_yaml(raw: bytes, *, clock: Callable[[], float], deadline: float) -> RawPresentationFields:
    if type(raw) is not bytes or not 1 <= len(raw) <= RAW_LIMIT:
        raise PresentationYamlError('RAW_SIZE')
    return reduce_presentation_events(raw, _events(raw), clock=clock, deadline=deadline)
