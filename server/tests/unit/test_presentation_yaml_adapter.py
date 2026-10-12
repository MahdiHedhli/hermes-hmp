"""Actual parser/reducer correspondence on synthetic documents, no live files."""

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
