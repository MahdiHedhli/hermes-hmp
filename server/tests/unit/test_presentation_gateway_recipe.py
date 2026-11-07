"""Actual private recipe/child IO; no executable-table or runtime admission."""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from .test_presentation_gateway_activation import MODULE
from .test_presentation_startup_selection import ARTIFACT_MODULE, PREFIX, SELECTION_MODULE, SUFFIX

RECIPE_MODULE = ARTIFACT_MODULE.with_name("presentation_gateway_recipe.py")
INSERT = r'''
recipe_mutation = sys.argv[8]
filenames = ("gateway-package.json", "gateway-entry.json", "gateway-dependencies.json",
             "gateway-interpreter.json")
roles = ("HMP_GATEWAY_PACKAGE", "HMP_GATEWAY_ENTRY", "HMP_GATEWAY_DEPENDENCIES",
         "HMP_GATEWAY_INTERPRETER")
children = []
for filename, kind in zip(filenames, roles):
    body = dict(schema=1, kind=kind, generation="1" * 64)
    if recipe_mutation == "child_kind" and filename == filenames[1]: body["kind"] = roles[0]
    if recipe_mutation == "child_generation": body["generation"] = "9" * 64
    if recipe_mutation == "child_schema_bool": body["schema"] = True
    raw_child = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("ascii")
    if recipe_mutation == "child_duplicate": raw_child = b'{"schema":1,' + raw_child[1:]
    if recipe_mutation == "child_noncanonical": raw_child += b"\n"
    (fixture / filename).write_bytes(raw_child)
    (fixture / filename).chmod(0o600)
    children.append(raw_child)
refs = {name: dict(size=len(raw_child), sha256=hashlib.sha256(raw_child).hexdigest())
        for name, raw_child in zip(("plugin", "entry", "dependencies", "interpreter"), children)}
recipe = dict(schema=1, kind="HMP_GATEWAY_RECIPE", generation="1" * 64, **refs)
if recipe_mutation == "kind": recipe["kind"] = "HMP_GATEWAY_PACKAGE"
if recipe_mutation == "generation": recipe["generation"] = "9" * 64
if recipe_mutation == "unknown": recipe["command"] = "SYNTHETIC_FORBIDDEN"
if recipe_mutation == "recipe_nan": recipe["schema"] = float("nan")
if recipe_mutation == "schema_bool": recipe["schema"] = True
if recipe_mutation == "size_bool": refs["plugin"]["size"] = True
if recipe_mutation == "size_zero": refs["plugin"]["size"] = 0
if recipe_mutation == "size_over": refs["plugin"]["size"] = 8 * 1024 * 1024 + 1
if recipe_mutation == "aggregate":
    for ref in refs.values(): ref["size"] = 8 * 1024 * 1024
if recipe_mutation == "digest_format": refs["plugin"]["sha256"] = "X" * 64
recipe_raw = json.dumps(recipe, sort_keys=True, separators=(",", ":")).encode("ascii")
if recipe_mutation == "duplicate": recipe_raw = b'{"schema":1,' + recipe_raw[1:]
if recipe_mutation == "noncanonical": recipe_raw += b"\n"
(fixture / "gateway-recipe.json").write_bytes(recipe_raw)
(fixture / "gateway-recipe.json").chmod(0o600)
'''
CONFIG = SUFFIX[:SUFFIX.rfind("print(json.dumps")]
CONFIG = CONFIG.replace("document = dict(", INSERT + "\ndocument = dict(", 1)
CONFIG = CONFIG.replace("document = dict(schema=1",
                        "document = dict(schema=(1 if recipe_mutation == 'schema1_config' "
                        "else 2)", 1)
CONFIG = CONFIG.replace('gateway_inventory_sha256="4" * 64',
                        'gateway_inventory_sha256=hashlib.sha256(recipe_raw).hexdigest()')
CONFIG = CONFIG.replace("c.StartupSelectionOwner.load(owner, expected)",
                        "(c.StartupSelectionOwner.load if recipe_mutation == 'schema1_config' "
                        "else c.StartupSelectionOwner.load_recipe_selection)(owner, expected)")
RECIPE = r'''
package.__path__ = [str(Path(c.__file__).parent)]
recipe_spec = importlib.util.spec_from_file_location(
    package.__name__ + ".presentation_gateway_recipe", sys.argv[7])
g = importlib.util.module_from_spec(recipe_spec)
sys.modules[recipe_spec.name] = g
recipe_spec.loader.exec_module(g)
mutation = recipe_mutation
leaf = fixture / filenames[0]
if mutation == "leaf_mode": leaf.chmod(0o644)
if mutation == "directory_mode": fixture.chmod(0o755)
if mutation == "missing": leaf.unlink()
if mutation == "recipe_missing": (fixture / "gateway-recipe.json").unlink()
if mutation == "changed": leaf.write_bytes(b"X" * len(children[0]))
if mutation == "symlink":
    target = fixture / "other.json"
    leaf.rename(target)
    leaf.symlink_to(target)
if mutation == "hardlink": os.link(leaf, fixture / "alias.json")
if mutation == "late": sys.modules["gateway.run"] = ModuleType("gateway.run")
foreign = object()
actual_read, actual_close = a.os.read, a.os.close
closes = []
if mutation in ("read_retire", "read_unknown", "buffer_swap", "document_swap",
                "fact_swap", "plan_swap"):
    def read_callback(fd, count):
        result = actual_read(fd, count)
        active = owner._recipe_owner
        if active is not None and result:
            if mutation == "read_retire": owner.retire()
            if mutation == "read_unknown": raise OSError("synthetic lost read result")
            if mutation == "buffer_swap": active._buffer = bytearray(b"SYNTHETIC_FOREIGN")
            if mutation == "document_swap" and len(active._origin.expected.documents) >= 2:
                old = active._origin.expected.documents[0]
                active._origin.expected.documents[0] = (old[0], b"{}")
            if mutation == "fact_swap": owner._recipe_fact_cell = foreign
            if mutation == "plan_swap": owner._recipe_plan_cell = foreign
        return result
    a.os.read = read_callback
if mutation == "read_count_swap":
    armed = False
    replacement_count = None
    real_pid = g.os.getpid
    def arm_read(fd, count):
        global armed
        result = actual_read(fd, count)
        if result: armed = True
        return result
    def replace_count_in_guard():
        global armed, replacement_count
        value = real_pid()
        active = owner._recipe_owner
        if armed and active is not None and active._reading is False and active._bytes_read > 0:
            armed = False
            replacement_count = (active, active._origin, active._bytes_read)
            active._count_cell = replacement_count
        return value
    a.os.read = arm_read
    g.os.getpid = replace_count_in_guard
if mutation == "document_count_swap":
    real_hash = g.hashlib.sha256
    replaced_cell = None
    def replace_in_extra_hash(data=b""):
        global replaced_cell
        active = owner._recipe_owner
        if active is not None and active._origin is not None:
            if len(active._origin.expected.documents) == 4 and data == children[3]:
                replaced_cell = (active, active._origin, active._bytes_read)
                active._count_cell = replaced_cell
        return real_hash(data)
    g.hashlib.sha256 = replace_in_extra_hash
if mutation == "close_unknown":
    def close_callback(fd):
        actual_close(fd)
        closes.append(fd)
        if len(closes) == 1: raise OSError("synthetic lost close result")
    a.os.close = close_callback
size = len(recipe_raw)
if mutation == "candidate_size": size -= 1
if mutation == "candidate_bool": size = True
if mutation == "candidate_over": size = 65537
if mutation in ("document_final_swap", "final_count_swap"):
    getpid = g.os.getpid
    def final_context():
        value = getpid()
        active = owner._recipe_owner
        if active is not None and active._origin is not None:
            docs = active._origin.expected.documents
            if len(docs) == 5:
                if mutation == "document_final_swap": docs[0] = (docs[0][0], b"{}")
                else: active._count_cell = (active, active._origin, active._bytes_read)
        return value
    g.os.getpid = final_context
if mutation == "context_failure":
    getpid = g.os.getpid
    def context_callback():
        if owner._recipe_owner is not None: raise OSError("synthetic initial context failure")
        return getpid()
    g.os.getpid = context_callback
try:
    checked = g.GatewayRecipeOwner.load(loaded, size)
except g.GatewayRecipeError as error:
    assert mutation != "normal", mutation
    checked = error.failed_owner
    if mutation in ("late", "candidate_bool", "candidate_over", "schema1_config"):
        assert checked is None and owner._recipe_owner is None
    else:
        assert checked is owner._recipe_owner and checked._failed and not checked._ready
        assert checked._fact_cell is None
    if mutation == "fact_swap": assert owner._recipe_fact_cell is foreign
    else: assert owner._recipe_fact_cell is None
else:
    assert mutation == "normal", mutation
    assert checked._ready and not checked._failed and not checked._unknown
    assert checked._fact_cell is owner._recipe_fact_cell
    docs = checked._fact_cell[3]
    assert len(docs) == 5 and docs[0][1] == recipe_raw
    assert [row[1] for row in docs[1:]] == children
    assert checked._bytes_read == len(recipe_raw) + sum(map(len, children))
if mutation == "aggregate": assert checked._bytes_read == len(recipe_raw)
if mutation == "plan_swap": assert owner._recipe_plan_cell is foreign
if mutation == "document_count_swap":
    assert replaced_cell is not None and checked._count_cell is replaced_cell
if mutation == "read_count_swap":
    assert replacement_count is not None and checked._count_cell is replacement_count
    assert checked._unknown
if checked is not None and mutation != "buffer_swap": assert not checked._buffer
if checked is not None and checked._origin is not None:
    assert all(row.closed or row.unknown for row in checked._origin.records)
assert len(closes) == len(set(closes))
if mutation == "normal":
    original_scope = checked._origin
    sys.path[1] = "/synthetic/new-generation/site-packages"
    sys.modules["gateway.run"] = ModuleType("gateway.run")
try: g.GatewayRecipeOwner.load(loaded, size)
except Exception: pass
else: raise AssertionError("recipe recapture accepted")
if mutation == "normal":
    assert checked._origin is original_scope and checked._ready and not owner._uncertain
print(json.dumps({"mutation": mutation, "runtime_admitted": False}))
'''


@pytest.mark.parametrize("mutation", [
    "normal", "kind", "generation", "unknown", "schema_bool", "size_bool", "size_zero",
    "size_over", "aggregate", "digest_format", "duplicate", "noncanonical", "child_kind",
    "child_generation", "child_duplicate", "child_noncanonical", "leaf_mode", "directory_mode",
    "missing", "changed", "symlink", "hardlink", "late", "read_retire", "read_unknown",
    "buffer_swap", "document_swap", "fact_swap", "close_unknown", "candidate_size",
    "context_failure", "recipe_nan", "recipe_missing", "candidate_bool", "candidate_over",
    "document_final_swap", "plan_swap", "schema1_config", "child_schema_bool",
    "read_count_swap", "document_count_swap", "final_count_swap",
])
def test_owned_recipe_and_fixed_child_documents(tmp_path, mutation):
    if os.name != "posix" or sys.platform not in ("darwin", "linux"):
        pytest.skip("current supported POSIX startup fixture")
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", PREFIX + CONFIG + RECIPE, str(MODULE), "normal",
         "normal", str(ARTIFACT_MODULE), str(SELECTION_MODULE), str(tmp_path.resolve()),
         str(RECIPE_MODULE), mutation], env={"LANG": "C", "LC_ALL": "C"},
        capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"mutation": mutation, "runtime_admitted": False}
