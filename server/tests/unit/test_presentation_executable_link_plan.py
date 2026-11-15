"""Original selected-link retention over disposable symlinks; no completion here."""
from __future__ import annotations

import pytest

from . import test_presentation_entry_files as base
from .test_presentation_runtime_files import runtime_script

PREPARE_LINK = r'''
fake_executable=(entry_root if mutation == "link_in_tree" else base)/"runtime-python"
if mutation == "link_leading_parent":
    (base/"bin").mkdir(mode=0o700);fake_executable=base/"bin/runtime-python"
fake_stdlib=base/"stdlib";fake_stdlib.mkdir(mode=0o700)
fake_target=fake_stdlib/"runtime-target"
fake_target.write_bytes(b'SYNTHETIC_INTERPRETER_NOT_EXECUTED')
fake_target.chmod(0o700)
second=base/"runtime-intermediate"
if mutation == "link_multi":
    second.symlink_to(fake_target)
    fake_executable.symlink_to(second)
    hop_rows=[dict(path=str(fake_executable),target=str(second),destination=str(second)),
              dict(path=str(second),target=str(fake_target),destination=str(fake_target))]
else:
    target_text=("stdlib/runtime-target" if mutation == "link_relative" else
                 "../stdlib/runtime-target" if mutation == "link_leading_parent"
                 else str(fake_target))
    fake_executable.symlink_to(target_text)
    hop_rows=[dict(path=str(fake_executable),target=target_text,destination=str(fake_target))]
'''
LINK_DOCUMENT = r'''
interpreter["schema"]=2
interpreter["files"]=[artifact(fake_target)]
policy=dict(hops=hop_rows, final=dict(artifact(fake_target),uid=a.os.geteuid(),mode=0o700))
interpreter["executable_link"]=policy
if mutation in ("link_erased_private","link_erased_alias","link_dot","link_empty_component"):
    text={"link_erased_private":"secrets/../stdlib/runtime-target",
          "link_erased_alias":"alias/../stdlib/runtime-target",
          "link_dot":"./stdlib/runtime-target",
          "link_empty_component":"stdlib//runtime-target"}[mutation]
    policy["hops"][0]["target"]=text
    fake_executable.unlink();fake_executable.symlink_to(text)
if mutation == "link_start":policy["hops"][0]["path"]=str(base/"other")
if mutation == "link_destination":policy["hops"][0]["destination"]=str(base/"other")
if mutation == "link_cycle":
    policy["hops"].append(dict(path=str(fake_target),target=str(fake_executable),
                               destination=str(fake_executable)))
    policy["final"]["path"]=str(fake_executable)
if mutation == "link_duplicate":policy["hops"].append(dict(policy["hops"][0]))
if mutation == "link_empty":policy["hops"]=[]
if mutation == "link_over":policy["hops"]*=9
if mutation == "link_unknown":policy["command"]="SYNTHETIC_FORBIDDEN"
if mutation == "link_hop_unknown":policy["hops"][0]["command"]="SYNTHETIC_FORBIDDEN"
if mutation == "link_final_unknown":policy["final"]["command"]="SYNTHETIC_FORBIDDEN"
if mutation == "link_target_nul":policy["hops"][0]["target"]="bad\0target"
if mutation == "link_target_large":policy["hops"][0]["target"]="x"*4097
if mutation == "link_target_unicode_bytes":policy["hops"][0]["target"]="é"*2049
if mutation == "link_target_surrogate":policy["hops"][0]["target"]="\ud800"
if mutation == "link_private":
    policy["hops"][0].update(target=str(base/".ssh/secret"),destination=str(base/".ssh/secret"))
if mutation == "link_native":
    policy["hops"][0].update(target=str(base/"native/binary"),
                             destination=str(base/"native/binary"))
if mutation == "link_final_path":policy["final"]["path"]=str(base/"other")
if mutation == "link_final_missing":interpreter["files"]=[]
if mutation == "link_final_conflict":policy["final"]["sha256"]="0"*64
if mutation == "link_uid_bool":policy["final"]["uid"]=True
if mutation == "link_uid_wrong":policy["final"]["uid"]=a.os.geteuid()+100000
if mutation == "link_mode_bool":policy["final"]["mode"]=True
if mutation == "link_mode_write":policy["final"]["mode"]=0o722
if mutation == "link_mode_setid":policy["final"]["mode"]=0o4700
if mutation == "link_mode_noexec":policy["final"]["mode"]=0o600
if mutation == "link_regular_conflict":interpreter["files"].append(artifact(fake_executable))
if mutation == "link_shared":
    interpreter["packages"]=[dict(path=str(fake_stdlib),entries=table(fake_stdlib))]
children.extend([canonical(dependency),canonical(interpreter)])
'''
FINISH = r'''
from hmp_startup import runtime_files as runtime_module
original_bytes=plugin._bytes_read
if mutation in ("link_file_boundary","link_file_over","link_byte_boundary","link_byte_over"):
    actual_expected=runtime_module._expected
    def set_boundary(rows):
        actual_expected(rows)
        if len(rows)>1 and rows[0].path.endswith("/gateway-startup.json"):
            if mutation.startswith("link_file"):
                a._MAX_FILES=len(rows)+len(hop_rows)-(1 if mutation.endswith("over") else 0)
            else:
                a._MAX_TOTAL=sum(row.size for row in rows)+2*sum(
                    len(row["target"].encode("utf-8")) for row in hop_rows)
                if mutation.endswith("over"):a._MAX_TOTAL-=1
    runtime_module._expected=set_boundary
successes=("link_absolute","link_relative","link_leading_parent","link_multi","link_shared",
           "link_file_boundary","link_byte_boundary")
try:
    retained=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
except EntryFilesError as error:
    assert mutation not in successes,mutation
    assert error.failed_owner is entry._activation._entry_files_owner
    assert error.failed_owner._failed
else:
    assert mutation in successes,mutation
    plan=retained._inputs.runtime_plan;link=plan.executable_link
    assert link is not None and plan.recipe_binding[0].expected.recipe_schema==2
    assert link.hops[0].path==str(fake_executable) and link.target.path==str(fake_target)
    assert any(link.target is row for row in plan.all_files)
    assert not any(row.path==str(fake_executable) for row in plan.all_files)
    assert link.uid==a.os.geteuid() and link.mode==0o700
    assert link.text_bytes==sum(len(row["target"].encode("utf-8")) for row in hop_rows)
    assert retained._inputs.io_slot==[None] and not retained._ready
    if mutation=="link_shared":
        assert len([row for row in plan.all_files if row.path==str(fake_target)])==1
        assert len([row for row,held in plan.declarations if held is link.target])==2
    if mutation=="link_byte_boundary":
        assert original_bytes+sum(row.size for row in plan.pending)+2*link.text_bytes==a._MAX_TOTAL
assert entry._activation._artifact_owner is None
assert entry._activation._entry_files_fact_cell is None
assert plugin._bytes_read==original_bytes
try:EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
except EntryFilesError:pass
else:raise AssertionError("link plan recaptured")
print(json.dumps({"mutation":mutation,"runtime_admitted":False}))
'''


def link_script():
    script = runtime_script()
    a = script.index('fake_executable=base/"runtime-python"')
    b = script.index('sys._stdlib_dir=', a)
    script = script[:a] + PREPARE_LINK + script[b:]
    script = script.replace(
        'children.extend([canonical(dependency),canonical(interpreter)])', LINK_DOCUMENT, 1,
    ).replace(
        'canonical(dict(schema=1, kind="HMP_GATEWAY_RECIPE"',
        'canonical(dict(schema=2, kind="HMP_GATEWAY_RECIPE"',
    ).replace(
        'recipe = GatewayRecipeOwner.load(configuration,len(recipe_raw))',
        'recipe = GatewayRecipeOwner.load_executable_links(configuration,len(recipe_raw))',
    )
    script = script[:script.index('retained = None\n')] + FINISH
    return script


@pytest.mark.parametrize("mutation", [
    "link_absolute", "link_relative", "link_leading_parent", "link_multi", "link_shared",
    "link_erased_private", "link_erased_alias", "link_dot", "link_empty_component", "link_start",
    "link_destination", "link_cycle", "link_duplicate", "link_empty", "link_over",
    "link_unknown", "link_hop_unknown", "link_final_unknown", "link_target_nul",
    "link_target_large", "link_target_unicode_bytes", "link_target_surrogate",
    "link_private", "link_native", "link_final_path", "link_final_missing",
    "link_final_conflict", "link_uid_bool", "link_uid_wrong", "link_mode_bool",
    "link_mode_write", "link_mode_setid", "link_mode_noexec", "link_regular_conflict",
    "link_in_tree", "link_file_boundary", "link_file_over", "link_byte_boundary", "link_byte_over",
])
def test_original_link_plan_retention(tmp_path, monkeypatch, mutation):
    monkeypatch.setattr(base, "SCRIPT", link_script())
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
