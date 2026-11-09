"""Historical byte gates remain fixed; composition is an exact, test-only quotient."""
import hashlib
from pathlib import Path

import pytest

from . import approved_lifecycle_composition_witness as witness

PACKAGE = Path(__file__).resolve().parents[2] / "hmp_plugin"
CASES = (
    ("adapter.py", witness.ADAPTER_EDITS, witness.ADAPTER_BASE_SHA256),
    ("server.py", witness.SERVER_EDITS, witness.SERVER_BASE_SHA256),
    ("local_media_registry.py", witness.REGISTRY_EDITS, witness.REGISTRY_BASE_SHA256),
)


@pytest.mark.parametrize("name,edits,old_hash", CASES)
def test_exact_reviewed_inverse_preserves_original_hash(name, edits, old_hash):
    source = witness.read_witness_source(PACKAGE / name)
    candidates = {
        "adapter.py": witness.ADAPTER_CANDIDATE_SHA256,
        "server.py": witness.SERVER_CANDIDATE_SHA256,
        "local_media_registry.py": witness.REGISTRY_CANDIDATE_SHA256,
    }
    assert hashlib.sha256(source.encode()).hexdigest() == candidates[name]
    restored = witness._reverse(source, edits)
    assert hashlib.sha256(restored.encode()).hexdigest() == old_hash


@pytest.mark.parametrize("name,edits,old_hash", CASES)
def test_unrelated_dynamic_lookup_survives_inverse_and_fails_original_hash(name, edits, old_hash):
    marker = '\n\ndef outside_composition():\n    return __import__("unexpected")\n'
    restored = witness._reverse(witness.read_witness_source(PACKAGE / name) + marker, edits)
    assert restored.endswith(marker)
    assert hashlib.sha256(restored.encode()).hexdigest() != old_hash


@pytest.mark.parametrize("name,edits,old_hash", CASES)
def test_unknown_edit_inside_composition_delta_is_refused(name, edits, old_hash):
    source = witness.read_witness_source(PACKAGE / name)
    current = edits[0][0]
    middle = len(current) // 2
    damaged = current[:middle] + "UNREVIEWED_MUTATION" + current[middle:]
    with pytest.raises(AssertionError):
        witness._reverse(source.replace(current, damaged, 1), edits)


@pytest.mark.parametrize("name,edits,old_hash", CASES)
@pytest.mark.parametrize("newline", (b"\r\n", b"\r"))
def test_actual_witness_reader_preserves_line_ending_mutations(tmp_path, name, edits,
                                                              old_hash, newline):
    original = (PACKAGE / name).read_bytes()
    damaged = original.replace(b"\n", newline, 1)
    assert damaged != original
    path = tmp_path / name
    path.write_bytes(damaged)
    source = witness.read_witness_source(path)
    assert source.encode("utf-8") == damaged
    try:
        restored = witness._reverse(source, edits)
    except AssertionError:
        return  # changed exact anchor is safely refused
    assert hashlib.sha256(restored.encode()).hexdigest() != old_hash
