"""Explicit recipe2/interpreter2 document selection; link IO is not implemented here."""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from .test_presentation_gateway_activation import MODULE
from .test_presentation_gateway_recipe import CONFIG, RECIPE, RECIPE_MODULE
from .test_presentation_startup_selection import ARTIFACT_MODULE, PREFIX, SELECTION_MODULE

LINK_CONFIG = CONFIG.replace(
    'body = dict(schema=1, kind=kind, generation="1" * 64)',
    '''body = dict(schema=(2 if filename == filenames[3] else 1),
                kind=kind, generation="1" * 64)
    if recipe_mutation == "links_old_interpreter" and filename == filenames[3]:
        body["schema"] = 1
    if recipe_mutation == "links_other_child" and filename == filenames[0]:
        body["schema"] = 2
    if recipe_mutation == "links_bool" and filename == filenames[3]:
        body["schema"] = True
    if recipe_mutation == "links_generation" and filename == filenames[3]:
        body["generation"] = "9" * 64''',
).replace(
    'recipe = dict(schema=1, kind="HMP_GATEWAY_RECIPE", generation="1" * 64, **refs)',
    '''recipe = dict(schema=(1 if recipe_mutation == "links_old_recipe" else
                          3 if recipe_mutation == "links_unknown" else 2),
              kind="HMP_GATEWAY_RECIPE", generation="1" * 64, **refs)''',
)
LINK_RECIPE = RECIPE.replace(
    'checked = g.GatewayRecipeOwner.load(loaded, size)',
    '''loader = (g.GatewayRecipeOwner.load if mutation == "links_old_loader"
              else g.GatewayRecipeOwner.load_executable_links)
    checked = loader(loaded, size)''',
).replace('("normal", "document_budget_boundary")', '("links_normal",)').replace(
    '    assert checked._ready and not checked._failed and not checked._unknown',
    '''    assert checked._ready and not checked._failed and not checked._unknown
    assert checked._origin.expected.recipe_schema == 2''',
).replace(
    'print(json.dumps({"mutation": mutation, "runtime_admitted": False}))',
    '''try: g.GatewayRecipeOwner.load_executable_links(loaded, size)
except g.GatewayRecipeError: pass
else: raise AssertionError("explicit link recipe recapture accepted")
print(json.dumps({"mutation": mutation, "runtime_admitted": False}))''',
)


@pytest.mark.parametrize("mutation", [
    "links_normal", "links_old_recipe", "links_old_loader", "links_old_interpreter",
    "links_other_child", "links_bool", "links_generation", "links_unknown",
])
def test_explicit_link_recipe_documents(tmp_path, mutation):
    if os.name != "posix" or sys.platform not in ("darwin", "linux"):
        pytest.skip("current supported POSIX startup fixture")
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", PREFIX + LINK_CONFIG + LINK_RECIPE, str(MODULE),
         "normal", "normal", str(ARTIFACT_MODULE), str(SELECTION_MODULE),
         str(tmp_path.resolve()), str(RECIPE_MODULE), mutation],
        env={"LANG": "C", "LC_ALL": "C"}, capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"mutation": mutation, "runtime_admitted": False}


def test_regular_runtime_path_refuses_link_recipe_before_artifact_io(tmp_path, monkeypatch):
    from . import test_presentation_entry_files as base
    from .test_presentation_runtime_files import runtime_script

    script = runtime_script().replace(
        'children.extend([canonical(dependency),canonical(interpreter)])',
        'interpreter["schema"] = 2\n'
        'children.extend([canonical(dependency),canonical(interpreter)])',
    ).replace(
        'canonical(dict(schema=1, kind="HMP_GATEWAY_RECIPE"',
        'canonical(dict(schema=2, kind="HMP_GATEWAY_RECIPE"',
    ).replace(
        'recipe = GatewayRecipeOwner.load(configuration,len(recipe_raw))',
        'recipe = GatewayRecipeOwner.load_executable_links(configuration,len(recipe_raw))',
    ).replace(
        'assert not foreign_calls\n',
        'assert entry._activation._artifact_owner is None\n'
        'assert entry._activation._entry_files_owner is None\n'
        'assert not foreign_calls\n',
    )
    monkeypatch.setattr(base, "SCRIPT", script)
    base.test_actual_entry_and_wrapper_files(tmp_path, "runtime_link_recipe_on_regular_path")
