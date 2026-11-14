"""Actual retained-audit count/cost evidence, never permission or speed acceptance."""
import json

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


def test_actual_original_nested_audit_and_cost_without_new_work(tmp_path, monkeypatch, request):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    marker = 'original_bytes=plugin._bytes_read'
    assert script.count(marker) == 1
    script = script[:script.index(marker)]
    script += r'''
import time,statistics
parent=entry._scope.native_files.link_policy
assert parent is entry._started_cell[5].link_policy
parent_current=parent[2][3][1]
assert parent_current(parent) is parent
packet=parent[0][6][6]
pkg_call=packet[5][0][0];recipe_call=packet[5][1][0]
selected_current=parent[0][6][3][1][1]
assert selected_current(packet) is packet
assert pkg_call is GatewayPackageOwner._retained_binding
assert recipe_call is GatewayRecipeOwner._retained_binding
ledger=entry._scope.native_files.ledger
before=(tuple(ledger.counts),len(ledger.attempts),recipe._bytes_read,plugin._bytes_read)
base_recipe=recipe_call(recipe);base_package=pkg_call(plugin)
manifest=base_package[0].expected
held_binding=manifest.recipe_binding
assert manifest.recipe is recipe
assert len(manifest.recipe_binding)==len(base_recipe)==6
assert all(a is b for a,b in zip(manifest.recipe_binding[:5],base_recipe[:5],strict=True))
assert all(a is b for a,b in zip(manifest.recipe_binding[5],base_recipe[5],strict=True))
samples={}
for name,fn,arg in (('recipe',recipe_call,recipe),('package',pkg_call,plugin),
                    ('parent_current',parent_current,parent),('selected_current',selected_current,packet)):
    values=[]
    for _ in range(24):
        started=time.perf_counter_ns();fn(arg);values.append(time.perf_counter_ns()-started)
    samples[name]=dict(median_ns=statistics.median(values),minimum_ns=min(values),samples=len(values))
recipe_code=recipe_call.__code__;package_code=pkg_call.__code__
nested=[];direct=[]
def observe(frame,event,value):
    if event=='call' and frame.f_code is recipe_code and frame.f_locals.get('self') is recipe:
        (nested if frame.f_back.f_code is package_code else direct).append(True)
assert sys.getprofile() is None and sys.gettrace() is None
sys.setprofile(observe)
try:
    recipe_call(recipe)
    returned=pkg_call(plugin)
finally:sys.setprofile(None)
assert nested==[True] and direct==[True],(nested,direct)
assert returned[0] is base_package[0] and returned[0].expected is manifest
assert manifest.recipe is recipe and manifest.recipe_binding is held_binding
assert parent_current(parent) is parent
assert before==(tuple(ledger.counts),len(ledger.attempts),recipe._bytes_read,plugin._bytes_read)
evidence=dict(source_only_candidate=True,nested_original_recipe_calls=1,direct_original_recipe_calls=1,
    actual_package_scope_rejoined=True,no_new_work_or_bytes=True,guard_samples=samples,
    conservative_two_parent_checks_ns=2*samples['parent_current']['median_ns'],
    conservative_two_selected_checks_ns=2*samples['selected_current']['median_ns'],
    removable_direct_recipe_ns=samples['recipe']['median_ns'],
    is_full_startup_acceptance=False,is_optimization_implemented=False,
    is_adversarial_original_caller_qualification=False)
destination=base/'retained-audit-cost.json'
destination.write_text(json.dumps(evidence,sort_keys=True));destination.chmod(0o600)
assert sys.getprofile() is None and sys.gettrace() is None
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
    evidence = json.loads((tmp_path / 'retained-audit-cost.json').read_text())
    assert evidence['nested_original_recipe_calls'] == 1
    assert evidence['direct_original_recipe_calls'] == 1
    assert evidence['no_new_work_or_bytes'] is True
    # Preserve timing observations, not a pass threshold or a native speed claim.
    destination = tmp_path / 'retained-audit-cost-summary.json'
    destination.write_text(json.dumps(evidence, sort_keys=True))
    destination.chmod(0o600)

    request.node.user_properties.append(('retained_audit_cost', json.dumps(evidence, sort_keys=True)))
