"""Tests for tools/fixtures/manifest.py.

Covers the acceptance criteria from tasks.md T014: the validator rejects
`continuity_evidence: true`, a missing label prefix, and host names,
addresses or emails that look real — plus the reference/coverage checks
this tool adds on top of the JSON Schema.

Also covers the IR-17 fix (specs/001-connect-and-browse/reviews/interfaces.md):
`device_name_prefix` and `operator_label_prefix` must be present and equal
exactly the CS-22 scannable prefixes from contracts/fixture-format.md rule 7.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import manifest as manifest_mod
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
REAL_MANIFEST_PATH = REPO_ROOT / "fixtures" / "f1" / "instances.yaml"
REAL_SCHEMA_PATH = REPO_ROOT / "fixtures" / "f1" / "SCHEMA.json"
MANIFEST_SCRIPT = REPO_ROOT / "tools" / "fixtures" / "manifest.py"


def base_manifest() -> dict:
    """A minimal, valid manifest matching the contract shape, independent of
    the real shipped fixture file, so these tests probe the validator's
    rules rather than the content of fixtures/f1/instances.yaml."""
    return {
        "format": 1,
        "label_prefix": "[F1 SYNTHETIC]",
        "device_name_prefix": manifest_mod.CS22_DEVICE_NAME_PREFIX,
        "operator_label_prefix": manifest_mod.CS22_OPERATOR_LABEL_PREFIX,
        "continuity_evidence": False,
        "instances": [
            {
                "key": "A",
                "display_label": "Fixture A",
                "port": 0,
                "users": [{"key": "userA"}],
                "profiles": [
                    {
                        "name": "f1-alpha",
                        "display_name": "Alpha",
                        "authorize_for": ["userA"],
                        "conversation": "conv-a",
                    },
                    {
                        "name": "f1-empty",
                        "display_name": "Empty",
                        "authorize_for": ["userA"],
                        "conversation": None,
                    },
                ],
            },
            {
                "key": "B",
                "display_label": "Fixture B",
                "port": 0,
                "users": [{"key": "userB"}],
                "profiles": [
                    {
                        "name": "f1-alpha",
                        "display_name": "Alpha",
                        "authorize_for": ["userB"],
                        "conversation": "conv-b",
                    },
                    {
                        "name": "f1-empty",
                        "display_name": "Empty",
                        "authorize_for": ["userB"],
                        "conversation": None,
                    },
                ],
            },
        ],
        "conversations": {
            "conv-a": {
                "messages": [
                    {"role": "user", "text": "[F1 SYNTHETIC] hello"},
                    {"role": "assistant", "text": "[F1 SYNTHETIC] hi there"},
                ]
            },
            "conv-b": {"generate": {"count": 12, "roles": ["user", "assistant"]}},
        },
        "mutations": {
            "append": {"conversation": "conv-b", "add": 3},
        },
    }


@pytest.fixture
def manifest() -> dict:
    return copy.deepcopy(base_manifest())


@pytest.fixture
def schema() -> dict:
    return manifest_mod.load_schema(REAL_SCHEMA_PATH)


# --- valid manifest -----------------------------------------------------


def test_base_manifest_is_valid(manifest, schema):
    assert manifest_mod.validate(manifest, schema) == []


def test_base_manifest_is_valid_without_schema(manifest):
    # Semantic checks alone (no jsonschema pass) must also accept it.
    assert manifest_mod.validate(manifest, schema=None) == []


def test_real_shipped_manifest_is_valid():
    real_manifest = manifest_mod.load_manifest(REAL_MANIFEST_PATH)
    real_schema = manifest_mod.load_schema(REAL_SCHEMA_PATH)
    errors = manifest_mod.validate(real_manifest, real_schema)
    assert errors == [], errors


def test_real_schema_is_a_valid_json_schema():
    import jsonschema

    real_schema = manifest_mod.load_schema(REAL_SCHEMA_PATH)
    jsonschema.Draft202012Validator.check_schema(real_schema)


# --- continuity_evidence -------------------------------------------------


def test_rejects_continuity_evidence_true(manifest, schema):
    manifest["continuity_evidence"] = True
    errors = manifest_mod.validate(manifest, schema)
    assert errors
    assert any("continuity_evidence" in e for e in errors)


def test_rejects_missing_continuity_evidence(manifest, schema):
    del manifest["continuity_evidence"]
    errors = manifest_mod.validate(manifest, schema)
    assert any("continuity_evidence" in e for e in errors)


# --- label prefix ----------------------------------------------------


def test_rejects_missing_label_prefix_field(manifest, schema):
    del manifest["label_prefix"]
    errors = manifest_mod.validate(manifest, schema)
    assert any("label_prefix" in e for e in errors)


def test_rejects_empty_label_prefix_field(manifest, schema):
    manifest["label_prefix"] = ""
    errors = manifest_mod.validate(manifest, schema)
    assert any("label_prefix" in e for e in errors)


def test_rejects_message_missing_label_prefix(manifest, schema):
    manifest["conversations"]["conv-a"]["messages"][0]["text"] = "hello, no prefix here"
    errors = manifest_mod.validate(manifest, schema)
    assert any("label_prefix" in e for e in errors)


def test_accepts_message_with_label_prefix(manifest, schema):
    manifest["conversations"]["conv-a"]["messages"][0]["text"] = "[F1 SYNTHETIC] fine"
    assert manifest_mod.validate(manifest, schema) == []


# --- CS-22 scannable prefixes (IR-17) -----------------------------------


def test_rejects_missing_device_name_prefix(manifest, schema):
    del manifest["device_name_prefix"]
    errors = manifest_mod.validate(manifest, schema)
    assert any("device_name_prefix" in e for e in errors)


def test_rejects_missing_operator_label_prefix(manifest, schema):
    del manifest["operator_label_prefix"]
    errors = manifest_mod.validate(manifest, schema)
    assert any("operator_label_prefix" in e for e in errors)


def test_rejects_wrong_device_name_prefix(manifest, schema):
    manifest["device_name_prefix"] = "not-the-right-prefix-"
    errors = manifest_mod.validate(manifest, schema)
    assert any("device_name_prefix" in e for e in errors)


def test_rejects_wrong_operator_label_prefix(manifest, schema):
    manifest["operator_label_prefix"] = "not-the-right-prefix-"
    errors = manifest_mod.validate(manifest, schema)
    assert any("operator_label_prefix" in e for e in errors)


def test_rejects_device_name_prefix_missing_trailing_dash(manifest, schema):
    # A near-miss: right stem, wrong exact value. CS-22 requires the exact
    # string, not just "starts with the same word".
    manifest["device_name_prefix"] = "f1-fixture-device"
    errors = manifest_mod.validate(manifest, schema)
    assert any("device_name_prefix" in e for e in errors)


def test_accepts_exact_cs22_prefixes(manifest, schema):
    manifest["device_name_prefix"] = "f1-fixture-device-"
    manifest["operator_label_prefix"] = "f1-fixture-label-"
    assert manifest_mod.validate(manifest, schema) == []


def test_check_scannable_prefixes_runs_without_schema(manifest):
    # The semantic check must work even when the jsonschema pass is skipped.
    del manifest["device_name_prefix"]
    errors = manifest_mod.check_scannable_prefixes(manifest)
    assert any("device_name_prefix" in e for e in errors)


def test_real_manifest_has_exact_cs22_prefixes():
    real_manifest = manifest_mod.load_manifest(REAL_MANIFEST_PATH)
    assert real_manifest["device_name_prefix"] == "f1-fixture-device-"
    assert real_manifest["operator_label_prefix"] == "f1-fixture-label-"
    assert manifest_mod.check_scannable_prefixes(real_manifest) == []


# --- real-looking identifiers -----------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "[F1 SYNTHETIC] contact us at owner\x40realcorp.com",
        "[F1 SYNTHETIC] see https://hermes.realcorp.io for details",
        "[F1 SYNTHETIC] connect to 10.20.30.40 directly",
        "[F1 SYNTHETIC] host fe80:0000:0000:0000:0202:b3ff:fe1e:8329 seen",
    ],
)
def test_rejects_real_looking_identifiers(manifest, schema, text):
    manifest["conversations"]["conv-a"]["messages"][0]["text"] = text
    errors = manifest_mod.validate(manifest, schema)
    assert errors, f"expected a rejection for: {text!r}"


def test_accepts_reserved_domain_in_hostile_text(manifest, schema):
    # example.invalid (RFC 2606) is the contract's own example of a safe,
    # non-resolving payload for exercising hostile-content rendering.
    manifest["conversations"]["conv-a"]["messages"][0][
        "text"
    ] = "[F1 SYNTHETIC] <script>x</script> https://example.invalid"
    assert manifest_mod.validate(manifest, schema) == []


def test_display_label_with_real_looking_email_is_rejected(manifest, schema):
    manifest["instances"][0]["display_label"] = "Contact admin\x40realcorp.com"
    errors = manifest_mod.validate(manifest, schema)
    assert any("email" in e for e in errors)


# --- references --------------------------------------------------------


def test_rejects_unknown_authorize_for_user(manifest, schema):
    manifest["instances"][0]["profiles"][0]["authorize_for"] = ["nobody"]
    errors = manifest_mod.validate(manifest, schema)
    assert any("unknown user key" in e for e in errors)


def test_rejects_unknown_conversation_reference_on_profile(manifest, schema):
    manifest["instances"][0]["profiles"][0]["conversation"] = "does-not-exist"
    errors = manifest_mod.validate(manifest, schema)
    assert any("unknown conversation" in e for e in errors)


def test_rejects_unknown_conversation_reference_on_mutation(manifest, schema):
    manifest["mutations"]["append"]["conversation"] = "does-not-exist"
    errors = manifest_mod.validate(manifest, schema)
    assert any("unknown conversation" in e for e in errors)


# --- amendment A1 (session browsing): other_sessions -------------------


def test_other_sessions_accepts_a_valid_entry(manifest, schema):
    manifest["conversations"]["conv-cli"] = {
        "messages": [{"role": "user", "text": "[F1 SYNTHETIC] hi"}]
    }
    manifest["instances"][0]["profiles"][0]["other_sessions"] = [
        {
            "session_id": "cli-1",
            "source": "cli",
            "title": "A CLI session",
            "conversation": "conv-cli",
        }
    ]
    errors = manifest_mod.validate(manifest, schema)
    assert errors == []


def test_other_sessions_rejects_unknown_conversation(manifest, schema):
    manifest["instances"][0]["profiles"][0]["other_sessions"] = [
        {"session_id": "cli-1", "source": "cli", "conversation": "does-not-exist"}
    ]
    errors = manifest_mod.validate(manifest, schema)
    assert any("other_sessions[0] references unknown conversation" in e for e in errors)


def test_other_sessions_rejects_unknown_parent(manifest, schema):
    manifest["instances"][0]["profiles"][0]["other_sessions"] = [
        {"session_id": "tip-1", "source": "cli", "parent_session_id": "does-not-exist"}
    ]
    errors = manifest_mod.validate(manifest, schema)
    assert any("other_sessions[0] references unknown parent_session_id" in e for e in errors)


def test_other_sessions_rejects_hmp_source(manifest, schema):
    manifest["instances"][0]["profiles"][0]["other_sessions"] = [
        {"session_id": "s1", "source": "hmp"}
    ]
    errors = manifest_mod.validate(manifest, schema)
    assert errors != []  # schema-level: "hmp" is reserved for the phone's own conversation


def test_other_sessions_accepts_a_compression_lineage(manifest, schema):
    manifest["instances"][0]["profiles"][0]["other_sessions"] = [
        {"session_id": "root", "source": "cli", "end_reason": "compression"},
        {"session_id": "tip", "source": "cli", "parent_session_id": "root"},
    ]
    errors = manifest_mod.validate(manifest, schema)
    assert errors == []


def test_rejects_missing_required_instance(manifest, schema):
    manifest["instances"] = [manifest["instances"][0]]  # drop B
    errors = manifest_mod.validate(manifest, schema)
    assert any("required fixture instances" in e for e in errors)


def test_rejects_duplicate_instance_key(manifest, schema):
    dup = copy.deepcopy(manifest["instances"][0])
    manifest["instances"].append(dup)
    errors = manifest_mod.validate(manifest, schema)
    assert any("duplicate instance key" in e for e in errors)


# --- empty / non-empty history coverage --------------------------------


def test_rejects_instance_with_no_empty_history_profile(manifest, schema):
    # Instance A: drop the empty-history profile, leaving only non-empty.
    manifest["instances"][0]["profiles"] = [
        p for p in manifest["instances"][0]["profiles"] if p["conversation"] is not None
    ]
    errors = manifest_mod.validate(manifest, schema)
    assert any("no empty-history profile" in e for e in errors)


def test_rejects_instance_with_no_nonempty_history_profile(manifest, schema):
    # Instance B: drop the non-empty-history profile, leaving only empty.
    manifest["instances"][1]["profiles"] = [
        p for p in manifest["instances"][1]["profiles"] if p["conversation"] is None
    ]
    errors = manifest_mod.validate(manifest, schema)
    assert any("no non-empty-history profile" in e for e in errors)


def test_real_manifest_covers_empty_and_nonempty_for_both_instances():
    real_manifest = manifest_mod.load_manifest(REAL_MANIFEST_PATH)
    errors = manifest_mod.check_history_coverage(real_manifest)
    assert errors == []


# --- schema structural checks -------------------------------------------


def test_rejects_wrong_format_value(manifest, schema):
    manifest["format"] = 2
    errors = manifest_mod.validate(manifest, schema)
    assert errors


def test_rejects_bad_role(manifest, schema):
    manifest["conversations"]["conv-a"]["messages"][0]["role"] = "narrator"
    errors = manifest_mod.validate(manifest, schema)
    assert errors


def test_rejects_conversation_with_both_generate_and_messages(manifest, schema):
    manifest["conversations"]["conv-a"]["generate"] = {"count": 1, "roles": ["user"]}
    errors = manifest_mod.validate(manifest, schema)
    assert errors


def test_rejects_nonzero_port(manifest, schema):
    manifest["instances"][0]["port"] = 4443
    errors = manifest_mod.validate(manifest, schema)
    assert errors


def test_schema_pass_is_skipped_gracefully_without_jsonschema(manifest, monkeypatch):
    monkeypatch.setattr(manifest_mod, "jsonschema", None)
    # A manifest that's schema-invalid (bad format) but otherwise semantically
    # fine: with jsonschema patched out, check_schema degrades to [].
    assert manifest_mod.check_schema(manifest, {"const": "unused"}) == []


# --- CLI -----------------------------------------------------------------


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(MANIFEST_SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_accepts_the_real_manifest():
    result = _run_cli()
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_cli_rejects_continuity_evidence_true(tmp_path):
    bad = copy.deepcopy(base_manifest())
    bad["continuity_evidence"] = True
    manifest_path = tmp_path / "instances.yaml"
    manifest_path.write_text(yaml.safe_dump(bad), encoding="utf-8")

    result = _run_cli(str(manifest_path), "--schema", str(REAL_SCHEMA_PATH))
    assert result.returncode == 1
    assert "continuity_evidence" in result.stderr


def test_cli_rejects_wrong_scannable_prefixes(tmp_path):
    bad = copy.deepcopy(base_manifest())
    bad["device_name_prefix"] = "wrong-"
    bad["operator_label_prefix"] = "also-wrong-"
    manifest_path = tmp_path / "instances.yaml"
    manifest_path.write_text(yaml.safe_dump(bad), encoding="utf-8")

    result = _run_cli(str(manifest_path), "--schema", str(REAL_SCHEMA_PATH))
    assert result.returncode == 1
    assert "device_name_prefix" in result.stderr
    assert "operator_label_prefix" in result.stderr


def test_cli_rejects_missing_manifest_file(tmp_path):
    result = _run_cli(str(tmp_path / "nope.yaml"), "--schema", str(REAL_SCHEMA_PATH))
    assert result.returncode == 2
    assert "not found" in result.stderr


def test_cli_rejects_malformed_yaml(tmp_path):
    manifest_path = tmp_path / "instances.yaml"
    manifest_path.write_text("format: [1, 2\n", encoding="utf-8")  # unbalanced
    result = _run_cli(str(manifest_path), "--schema", str(REAL_SCHEMA_PATH))
    assert result.returncode == 2
    assert "YAML" in result.stderr


def test_cli_no_schema_flag_still_runs_semantic_checks(tmp_path):
    bad = copy.deepcopy(base_manifest())
    bad["continuity_evidence"] = True
    manifest_path = tmp_path / "instances.yaml"
    manifest_path.write_text(yaml.safe_dump(bad), encoding="utf-8")

    result = _run_cli(str(manifest_path), "--no-schema")
    assert result.returncode == 1
    assert "continuity_evidence" in result.stderr


def test_schema_json_is_valid_json():
    json.loads(REAL_SCHEMA_PATH.read_text(encoding="utf-8"))
