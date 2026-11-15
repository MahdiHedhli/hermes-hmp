"""Run only the reviewed BI1 cases and join JUnit identities to real collection.

CI helper only: imports pytest lazily in main; no HMP/native imports of its own.
Parameterized IDs come from the actual single pytest run, never guessed.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from xml.parsers import expat

MANIFEST = {
    "tests/unit/test_bi1_unicode17.py": {
        "sha256": "68cd0b0ba03d968c0a81f0c577f999f4d7288b8cb56b36c1adcc51279f8c3fa9",
        "bytes": 5587,
        "functions": {
            "test_normalization_official_20034_by_five": 1,
            "test_extended_grapheme_official_766": 1,
            "test_scalar_limit_type_and_range_refuses": 6,
            "test_input_output_bounds_and_scalar_validation": 1,
            "test_hangul_boundary_and_equal_class_blocking": 1,
            "test_unassigned_and_formatting_policy_for_host_titles": 1,
            "test_tables_have_no_mutable_global_cache": 1,
            "test_presentation_revision_excludes_observation_and_avatar": 1,
        },
        "cases": 13,
        "classname": "tests.unit.test_bi1_unicode17",
    },
    "tests/unit/test_presentation_pure.py": {
        "sha256": "dc3914ebad41d673f44ca4d8b7fa9471fa5ec84d2e555ab9c93c5f664a5907ad",
        "bytes": 12531,
        "functions": {
            "test_primary_closed_character_and_frozen_revision": 1,
            "test_title_then_profile_name_then_canonical_fallback": 1,
            "test_metadata_revision_is_independent_of_avatar_and_time": 1,
            "test_all_closed_classic_shapes": 7,
            "test_closed_blobatar_projection": 3,
            "test_unrepresentable_character_falls_back_without_raw_passthrough": 5,
            "test_current_primary_default_overrides_unpersisted_seed": 1,
            "test_exact_unicode_grapheme_boundary_requires_generated_unicode17_provider": 1,
            "test_joiners_survive_before_exact_grapheme_count_and_digest": 1,
            "test_supported_emoji_tag_sequence_retained_and_stray_tag_refused": 1,
            "test_explicit_bidi_and_display_controls_neutralized": 1,
            "test_declared_controls_only_are_removed_before_clustering": 21,
            "test_arabic_formatting_marks_survive_before_clustering": 3,
            "test_other_format_and_joiner_characters_are_not_category_erased": 1,
            "test_name_keeps_newer_assigned_character_when_stdlib_reports_cn": 1,
            "test_closed_identity_time_and_avatar_schema": 10,
            "test_metadata_revision_rejects_self_or_avatar_field_cycle": 1,
            "test_revision_helper_rejects_noncanonical_direct_fields": 9,
            "test_observation_time_i_json_inclusive_bound": 2,
            "test_observation_time_rejects_outside_i_json_integer_domain": 12,
        },
        "cases": 83,
        "classname": "tests.unit.test_presentation_pure",
    },
}


def need(condition: bool, label: str) -> None:
    if not condition:
        raise RuntimeError(label)


class Selection:
    def __init__(self) -> None:
        self.identities: set[tuple[str, str]] | None = None

    def pytest_collection_finish(self, session) -> None:
        need(self.identities is None, "collection repeated")
        need(len(session.items) == 96, "selected collection count")
        identities = set()
        counts = {path: dict.fromkeys(row["functions"], 0) for path, row in MANIFEST.items()}
        for item in session.items:
            parts = item.nodeid.split("::", 1)
            need(len(parts) == 2 and parts[0] in MANIFEST, "unlisted module or nested case")
            path, name = parts
            row = MANIFEST[path]
            original = item.originalname
            need(type(name) is str and name == item.name and len(name) <= 2048, "case name")
            need(original in row["functions"], "unlisted test function")
            need(
                name == original or (name.startswith(original + "[") and name.endswith("]")),
                "case/function join",
            )
            identity = (row["classname"], name)
            need(identity not in identities, "duplicate collected identity")
            identities.add(identity)
            counts[path][original] += 1
        for path, row in MANIFEST.items():
            need(counts[path] == row["functions"], "selected function coverage")
            need(sum(counts[path].values()) == row["cases"], "selected module coverage")
        self.identities = identities


def report_identities(body: bytes) -> list[tuple[str, str]]:
    """Bounded JUnit structure; DTD/entities and nonpassing records are refused."""
    need(type(body) is bytes and 0 < len(body) <= 1048576, "report byte bound")
    parser = expat.ParserCreate()
    stack = []
    identities = []
    elements = 0

    def refuse(*_args):
        raise RuntimeError("XML DTD/entities forbidden")

    def start(name, attrs):
        nonlocal elements
        elements += 1
        need(elements <= 1024 and len(stack) < 8, "XML structural bound")
        need(
            name
            in {
                "testsuites",
                "testsuite",
                "testcase",
                "properties",
                "property",
                "system-out",
                "system-err",
            },
            "nonpassing/unknown XML element",
        )
        need(len(attrs) <= 64, "XML attribute bound")
        if not stack:
            need(name == "testsuites", "report root")
        if name == "testcase":
            need(stack == ["testsuites", "testsuite"], "case position")
            need(
                type(attrs.get("classname")) is str and type(attrs.get("name")) is str,
                "case attributes",
            )
            identities.append((attrs["classname"], attrs["name"]))
            need(len(identities) <= 96, "extra case")
        stack.append(name)

    def end(name):
        need(stack and stack[-1] == name, "XML nesting")
        stack.pop()

    parser.StartDoctypeDeclHandler = refuse
    parser.EntityDeclHandler = refuse
    parser.ExternalEntityRefHandler = refuse
    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.Parse(body, True)
    need(not stack, "XML completion")
    return identities


def validate_report(body: bytes, selection: Selection) -> None:
    need(type(body) is bytes and 0 < len(body) <= 1048576, "report byte bound")
    need(
        selection.identities is not None and len(selection.identities) == 96,
        "no qualified collection",
    )
    cases = report_identities(body)
    need(len(cases) == 96, "report count")
    found = set()
    modules = {row["classname"]: 0 for row in MANIFEST.values()}
    for identity in cases:
        need(
            identity in selection.identities and identity not in found, "report identity/duplicate"
        )
        found.add(identity)
        modules[identity[0]] += 1
    need(found == selection.identities, "missing selected case")
    need(
        modules == {row["classname"]: row["cases"] for row in MANIFEST.values()},
        "report module coverage",
    )


def main() -> None:
    import pytest

    need(pytest.__version__ == "9.1.1", "reviewed locked pytest version")
    root = Path(__file__).resolve().parents[2]
    for path, row in MANIFEST.items():
        source = root / "server" / path
        need(source.stat().st_size == row["bytes"], "selected source size")
        body = source.read_bytes()
        need(
            len(body) == row["bytes"] and hashlib.sha256(body).hexdigest() == row["sha256"],
            "selected source hash",
        )
    report = Path(os.environ["RUNNER_TEMP"]) / "bi1-unicode.xml"
    need(not report.exists(), "report must be fresh")
    selection = Selection()
    code = pytest.main(
        [
            "--rootdir=" + str(root / "server"),
            *(str(root / "server" / path) for path in MANIFEST),
            "-q",
            "-ra",
            "--import-mode=importlib",
            "--durations=5",
            "--junitxml=" + str(report),
        ],
        plugins=[selection],
    )
    need(code == 0, "selected pytest failed")
    need(0 < report.stat().st_size <= 1048576, "report size")
    validate_report(report.read_bytes(), selection)
    print("BI1 exact collected identities: 13 + 83 passed, no skips or duplicates")


if __name__ == "__main__":
    main()
