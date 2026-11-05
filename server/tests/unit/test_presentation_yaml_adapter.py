"""Actual parser/reducer correspondence on synthetic documents, no live files."""

from contextlib import suppress

import pytest

from hmp_plugin.presentation_yaml import PresentationYamlError
from hmp_plugin.presentation_yaml_adapter import parse_presentation_yaml


def parse(raw):
    return parse_presentation_yaml(raw, clock=lambda: 1.0, deadline=2.0)


def test_actual_parser_selects_only_character_fields():
    result = parse(b"""display_name: Profile label
private: {secret: synthetic-never-projected}
ui_meta:
  hermes-bots:
    title: Desktop name
    shape: hexagon
    color: '#8b5cf6'
    custom: true
""")
    assert vars(result) == {
        "display_name": "Profile label",
        "title": "Desktop name",
        "shape": "hexagon",
        "color": "#8b5cf6",
        "custom": True,
    }
    assert "synthetic-never-projected" not in repr(result)


@pytest.mark.parametrize(
    "raw",
    [
        b"ui_meta: &a {hermes-bots: {title: Name}}\ncopy: *a\n",
        b"display_name: !!str Name\n",
        b"%YAML 1.1\n---\ndisplay_name: Name\n",
        b"display_name: One\ndisplay_name: Two\n",
        b"---\ndisplay_name: One\n---\ndisplay_name: Two\n",
        b"ui_meta: [wrong-type]\n",
        b"display_name: [Name]\n",
        b'display_name: "unterminated\n',
        b"display_name: \xff\n",
    ],
)
def test_actual_parser_rejects_unsafe_or_ambiguous_documents(raw):
    with pytest.raises(PresentationYamlError):
        parse(raw)


@pytest.mark.parametrize("token", [b"yes", b"true", b"on"])
def test_actual_plain_boolean_parity(token):
    assert parse(b"ui_meta: {hermes-bots: {custom: " + token + b"}}").custom is True


def test_quoted_boolean_is_not_silently_coerced():
    with pytest.raises(PresentationYamlError):
        parse(b'ui_meta: {hermes-bots: {custom: "true"}}')


def test_parser_cannot_bypass_shared_expired_deadline():
    with pytest.raises(PresentationYamlError):
        parse_presentation_yaml(b"display_name: Name", clock=lambda: 2.0, deadline=2.0)


def test_unknown_directive_is_not_silently_discarded_by_parser():
    with pytest.raises(PresentationYamlError):
        parse(b"%FOO synthetic\n---\ndisplay_name: Label\n")


def test_directive_like_text_inside_block_scalar_is_preserved():
    assert parse(b"display_name: |-\n  %FOO synthetic\n").display_name == "%FOO synthetic"


def test_token_event_projection_never_constructs_yaml_graph(monkeypatch):
    from yaml.loader import SafeLoader

    def forbidden(*args, **kwargs):
        pytest.fail("YAML graph construction invoked")

    for name in (
        "get_data",
        "get_single_data",
        "get_node",
        "get_single_node",
        "construct_object",
        "construct_document",
    ):
        monkeypatch.setattr(SafeLoader, name, forbidden)
    result = parse(b"display_name: Label\nprivate: {nested: [one, two]}\n")
    assert result.display_name == "Label"


@pytest.mark.parametrize(
    "raw, expected_disposals",
    [
        (b"display_name: Label\n", 2),
        (b"%YAML 1.1\n---\ndisplay_name: Label\n", 1),
        (b"display_name: One\ndisplay_name: Two\n", 2),
    ],
)
def test_both_loaders_dispose_on_success_or_early_refusal(monkeypatch, raw, expected_disposals):
    from yaml.loader import SafeLoader

    disposed = []
    original = SafeLoader.dispose

    def record(loader):
        disposed.append(loader)
        original(loader)

    monkeypatch.setattr(SafeLoader, "dispose", record)
    with suppress(PresentationYamlError):
        parse(raw)
    assert len(disposed) == expected_disposals
    assert len({id(loader) for loader in disposed}) == expected_disposals


def test_explicit_event_generator_close_disposes_parser(monkeypatch):
    from yaml.loader import SafeLoader

    from hmp_plugin.presentation_yaml_adapter import _events

    disposed = []
    original = SafeLoader.dispose

    def record(loader):
        disposed.append(loader)
        original(loader)

    monkeypatch.setattr(SafeLoader, "dispose", record)
    events = _events(b"display_name: Label", lambda: 1.0, 2.0, None)
    assert next(events).kind == "stream_start"
    assert len(disposed) == 1  # token scan completed first
    events.close()
    assert len(disposed) == 2
