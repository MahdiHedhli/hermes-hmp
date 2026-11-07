"""Actual recipe-to-package IO, not complete runtime/native factory admission."""
from __future__ import annotations

import pytest

from . import test_presentation_gateway_package as base

MAKE_RECIPE = r'''
child_bodies = [manifest_raw]
for kind in ("HMP_GATEWAY_ENTRY", "HMP_GATEWAY_DEPENDENCIES", "HMP_GATEWAY_INTERPRETER"):
    child_bodies.append(json.dumps(dict(schema=1, kind=kind, generation="1" * 64),
                                  sort_keys=True, separators=(",", ":")).encode("ascii"))
refs = {name: dict(size=len(body), sha256=hashlib.sha256(body).hexdigest())
        for name, body in zip(("plugin", "entry", "dependencies", "interpreter"), child_bodies)}
recipe_raw = json.dumps(dict(schema=1, kind="HMP_GATEWAY_RECIPE", generation="1" * 64, **refs),
                        sort_keys=True, separators=(",", ":")).encode("ascii")
for filename, body in zip(("gateway-recipe.json", "gateway-package.json", "gateway-entry.json",
                           "gateway-dependencies.json", "gateway-interpreter.json"),
                          (recipe_raw, *child_bodies)):
    (fixture / filename).write_bytes(body)
    (fixture / filename).chmod(0o600)
'''
LOAD = r'''
recipe = p.GatewayRecipeOwner.load(loaded, len(recipe_raw))
original_count = recipe._fact_cell[4]
foreign_recipe_fact = object()
if mutation == "count_drift": recipe._bytes_read += 1
if mutation == "source_swap":
    actual_hash = p.hashlib.sha256
    def replace_recipe_fact(data=b""):
        if data is manifest_raw or data == manifest_raw:
            recipe._fact_cell = owner._recipe_fact_cell = foreign_recipe_fact
        return actual_hash(data)
    p.hashlib.sha256 = replace_recipe_fact
if mutation == "package_count_swap":
    actual_origins = p.GatewayPackageOwner._origins
    def replace_count_after_origins(active):
        result = actual_origins(active)
        active._count_cell = (active, active._origin, active._bytes_read)
        return result
    p.GatewayPackageOwner._origins = replace_count_after_origins
if mutation == "recipe_post_context":
    actual_pid = p.os.getpid
    def change_after_package_scope():
        value = actual_pid()
        active = owner._package_owner
        if active is not None and active._origin is not None:
            recipe._fact_cell = owner._recipe_fact_cell = foreign_recipe_fact
        return value
    p.os.getpid = change_after_package_scope
'''


def _configuration():
    text = base.CONFIG_PREFIX.replace("schema=(2 if package_mutation == 'selection_v2' else 1)",
                                      "schema=2")
    text = text.replace("package_mutation == 'selection_v2'", "True")
    text = text.replace("hashlib.sha256(manifest_raw).hexdigest()",
                        "hashlib.sha256(recipe_raw).hexdigest()")
    return text.replace("document = dict(", MAKE_RECIPE + "\ndocument = dict(", 1)


def _package():
    text = base.PACKAGE_SUFFIX.replace('success = mutation == "normal"',
                                       LOAD + '\nsuccess = mutation == "normal"')
    text = text.replace('if mutation == "selection_v2":',
                        'if mutation in ("count_drift", "copied_fact"):')
    text = text.replace('checked = p.GatewayPackageOwner.verify(loaded, manifest_raw)',
                        'checked = p.GatewayPackageOwner.verify_recipe(\n'
                        '        recipe._fact_cell if mutation == "copied_fact" else recipe)')
    text = text.replace('sum(row["size"] for row in rows)',
                        'original_count[2] + sum(row["size"] for row in rows)')
    text = text.replace('assert checked._bytes_read == 0',
                        'assert checked._bytes_read == original_count[2]')
    text = text.replace('try: p.GatewayPackageOwner.verify(loaded, manifest_raw)',
                        'if mutation == "normal":\n'
                        '    sys.path[1] = "/synthetic/later-generation/site-packages"\n'
                        '    sys.modules["gateway.run"] = ModuleType("gateway.run")\n'
                        'try: p.GatewayPackageOwner.verify_recipe(\n'
                        '    recipe._fact_cell if mutation == "copied_fact" else recipe)')
    return text.replace('print(json.dumps({"mutation": mutation,', '''
if mutation in ("source_swap", "recipe_post_context"):
    assert owner._recipe_fact_cell is foreign_recipe_fact
    assert recipe._fact_cell is foreign_recipe_fact
if mutation == "normal":
    assert checked._origin.expected.recipe is recipe
    assert checked._origin.expected.recipe_binding[4][4] is original_count
    assert recipe._count_cell is original_count
print(json.dumps({"mutation": mutation,''')


@pytest.mark.parametrize("mutation", [
    "normal", "extra", "missing", "changed", "after_hash_replace", "source_swap",
    "count_drift", "copied_fact", "recipe_post_context", "history_late", "history_namespace",
    "history_paths", "history_thread", "package_count_swap",
])
def test_package_from_actual_retained_recipe(tmp_path, monkeypatch, mutation):
    monkeypatch.setattr(base, "CONFIG_PREFIX", _configuration())
    monkeypatch.setattr(base, "PACKAGE_SUFFIX", _package())
    base.test_pinned_complete_hmp_package(tmp_path, mutation)
