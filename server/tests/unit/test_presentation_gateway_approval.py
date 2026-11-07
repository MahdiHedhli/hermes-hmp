"""Disposable operator files and native-root stub; no installed approval or keys."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from .test_presentation_gateway_entry import BOOTSTRAP, PACKAGE
from .test_presentation_gateway_entry import SCRIPT as ENTRY_SCRIPT

BODY = r'''
from pathlib import Path
import hashlib, os, threading
from hmp_startup.gateway_approval import GatewayApprovalOwner, GatewayApprovalError
from hmp_startup import gateway_approval as approval_module
from hmp_plugin import presentation_startup_artifacts as artifacts
from hmp_plugin.presentation_startup_selection import StartupSelectionOwner, SelectionLoadError
import hermes_constants as constants
case = sys.argv[5]
default = Path(constants.ROOT)
directory = default / 'plugin-data/hmp/presentation/gateway-startup'
path = directory / 'gateway-approval.json'
selection_path = directory / 'gateway-startup.json'
selected = dict(schema=2,kind='HMP_GATEWAY_STARTUP_SELECTION',iid='a'*52,protocol=2,
    algorithm='Ed25519',credential_generation='1'*64,gateway_public='2'*64,
    broker_public='3'*64,gateway_inventory_sha256='4'*64,broker_inventory_sha256='5'*64,
    loader_policy='darwin-system-loader-trust' if sys.platform=='darwin'
    else 'linux-system-loader-trust')
canonical = lambda d: json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
selection_raw=canonical(selected)
selection_path.write_bytes(selection_raw);selection_path.chmod(0o600)
document=dict(schema=1,kind='HMP_GATEWAY_OPERATOR_APPROVAL',selection_schema=2,
    selection_size=len(selection_raw),selection_sha256=hashlib.sha256(selection_raw).hexdigest(),
    recipe_schema=2,recipe_size=321)
if case=='schema_bool':document['schema']=True
if case=='selection_schema':document['selection_schema']=1
if case=='recipe_bool':document['recipe_schema']=True
if case=='recipe_size':document['recipe_size']=0
if case=='unknown_path':document['path']='/SYNTHETIC_FORBIDDEN_PATH'
if case=='bad_hex':document['selection_sha256']='G'*64
if case=='selection_digest':document['selection_sha256']='0'*64
raw=canonical(document)
if case=='noncanonical':raw+=b'\n'
if case=='duplicate':raw=b'{"schema":1,'+raw[1:]
if case=='oversize':raw=b'x'*4097
if case=='empty':raw=b''
path.write_bytes(raw);path.chmod(0o600)
if case=='missing':path.unlink()
if case=='leaf_mode':path.chmod(0o644)
if case=='directory_mode':directory.chmod(0o755)
if case=='symlink':
    path.rename(directory/'original.json');path.symlink_to(directory/'original.json')
if case=='hardlink':os.link(path,directory/'alias.json')
if case=='ancestor_link':
    directory.rename(directory.parent/'renamed');directory.symlink_to(directory.parent/'renamed')
actual_read,actual_close=artifacts.os.read,artifacts.os.close
actual_open=artifacts.os.open;open_calls=[]
def observed_open(*args,**kwargs):
    open_calls.append(True);return actual_open(*args,**kwargs)
artifacts.os.open=observed_open
if case=='lookalike':
    constants.__file__=str(default/'untrusted/hermes_constants.py')
    constants.__spec__.origin=constants.__file__
    constants.get_default_hermes_root.__code__=constants.get_default_hermes_root.__code__.replace(
        co_filename=constants.__file__)
if case=='function_origin':
    constants.get_default_hermes_root.__code__=constants.get_default_hermes_root.__code__.replace(
        co_filename=str(default/'untrusted.py'))
read_calls=[];close_calls=[];foreign_counter=None;foreign_fact=object();foreign_root=object()
old_function=constants.get_default_hermes_root
if case in ('root_read','function_read','read_unknown','count_copy','read_retire','reads_copy'):
    def read_callback(fd,count):
        global foreign_counter
        data=actual_read(fd,count);read_calls.append(len(data))
        active=owner._activation._approval_owner
        if case=='root_read':constants.ROOT += '-changed'
        if case=='function_read':constants.get_default_hermes_root=lambda:default
        if case=='read_unknown':raise OSError('synthetic read outcome unknown')
        if case=='count_copy':
            foreign_counter=tuple(list(active._count_cell));active._count_cell=foreign_counter
        if case=='read_retire':owner._activation.retire()
        if case=='reads_copy':
            effect=active._origin.reads[-1]
            active._origin.reads[-1]=artifacts._ReadEffect(effect.before)
        return data
    artifacts.os.read=read_callback
if case=='close_unknown':
    def close_callback(fd):
        actual_close(fd);close_calls.append(fd)
        if len(close_calls)==1:raise OSError('synthetic close outcome unknown')
    artifacts.os.close=close_callback
original_decode=approval_module._decode
if case in ('fact_replaced','root_replaced','closed_changed','ledger_copy'):
    def decode_callback(raw,directory):
        result=original_decode(raw,directory)
        active=owner._activation._approval_owner
        if case=='fact_replaced':owner._activation._approval_fact_cell=foreign_fact
        if case=='root_replaced':owner._activation._approval_cell=foreign_root
        if case=='closed_changed':active._origin.records[0].closed=False
        if case=='ledger_copy':
            row=active._origin.reads[0]
            active._origin.reads[0]=artifacts._ReadEffect(row.before,row.after,row.returned,row.unknown)
        return result
    approval_module._decode=decode_callback
successes=('normal','operator_selection','selection_digest','current_root','current_function',
           'current_fact_copy','current_root_copy','wrong_thread','duplicate_load','counts',
           'selection_parent_replaced','recipe_variant','recipe_size_mismatch')
try:
    loaded=GatewayApprovalOwner.load(owner)
except GatewayApprovalError as error:
    assert case not in successes,case
    active=owner._activation._approval_owner
    assert error.failed_owner is active and active._failed and not active._ready
    assert active._buffer==bytearray()
    if case in ('lookalike','function_origin','callback_origin','callback_loader'):
        assert open_calls==[]
    assert owner._activation._approval_fact_cell is (
        foreign_fact if case=='fact_replaced' else None)
    if case=='root_replaced':assert owner._activation._approval_cell is foreign_root
    if case=='count_copy':
        assert active._count_cell is foreign_counter
        assert active._origin.reads[0].after[2]==len(raw)
    if case=='read_unknown':assert len(read_calls)==1 and active._unknown
    if case=='close_unknown':
        assert len(close_calls)==len(set(close_calls)) and active._unknown
    if case=='closed_changed':
        assert not active._origin.records[0].closed
        assert all(r.close_attempted for r in active._origin.records)
    if active._origin is not None and case not in (
            'close_unknown','root_replaced','closed_changed'):
        assert all(r.fd is None or r.closed for r in active._origin.records),case
    before=len(read_calls)
    try:GatewayApprovalOwner.load(owner)
    except GatewayApprovalError:pass
    else:raise AssertionError('failed owner recaptured')
    assert len(read_calls)==before
else:
    assert case in successes,case
    binding=loaded.current_binding();s,cell,root,fact=binding
    assert fact[2].selection.path==str(selection_path)
    assert fact[2].selection.size==len(selection_raw) and fact[2].recipe_size==321
    assert fact[2].recipe_schema==2
    assert fact[3][2]==len(raw) and loaded._buffer==bytearray()
    assert fact[4].count is fact[3] and fact[5].sha256==hashlib.sha256(raw).hexdigest()
    assert str(default) not in repr(loaded) and str(default) not in repr(fact[2])
    assert all(r.closed and not r.unknown for r in s.records)
    assert 'gateway.run' not in sys.modules and owner._activation._artifact_owner is None
    if case in ('operator_selection','selection_digest','counts','selection_parent_replaced',
                'recipe_variant','recipe_size_mismatch'):
        if case=='selection_parent_replaced':
            armed=False
            old_parent=GatewayApprovalOwner.current_binding
            old_activation=approval_module.GatewayActivationOwner.current
            def parent_query(self):
                global armed
                armed=False
                value=old_parent(self);armed=True;return value
            def late_activation(self):
                value=old_activation(self)
                if armed and self._selection_owner is not None:
                    approval_module._FACT=foreign_fact
                return value
            GatewayApprovalOwner.current_binding=parent_query
            approval_module.GatewayActivationOwner.current=late_activation
        try:selection=StartupSelectionOwner.load_operator_selection(loaded)
        except SelectionLoadError:
            assert case in ('selection_digest','selection_parent_replaced')
            assert owner._activation._selection_owner._failed
            assert owner._activation._selection_fact_cell is None
            if case=='selection_parent_replaced':assert approval_module._FACT is foreign_fact
        else:
            assert case not in ('selection_digest','selection_parent_replaced')
            assert selection.retained_data().iid=='a'*52
            assert selection._bytes_read==len(raw)+len(selection_raw)
            assert selection._origin.parent.owner is loaded
            assert selection._origin.expected[0] is fact[2].selection
            from hmp_plugin.presentation_startup_selection import _configuration_rows
            rows=_configuration_rows(selection)
            assert len(rows)==2 and rows[0] is fact[5] and rows[1] is fact[2].selection
            if case in ('recipe_variant','recipe_size_mismatch'):
                from hmp_plugin.presentation_gateway_recipe import (
                    GatewayRecipeOwner, GatewayRecipeError)
                opens=len(open_calls)
                try:
                    if case=='recipe_variant':GatewayRecipeOwner.load(selection,fact[2].recipe_size)
                    else:GatewayRecipeOwner.load_executable_links(selection,fact[2].recipe_size+1)
                except GatewayRecipeError:pass
                else:raise AssertionError('approval variant/size bypass')
                assert len(open_calls)==opens and owner._activation._recipe_owner is None
    if case=='wrong_thread':
        refused=[]
        def wrong():
            try:loaded.current_binding()
            except GatewayApprovalError:refused.append(True)
        thread=threading.Thread(target=wrong);thread.start();thread.join()
        assert refused==[True] and not loaded._failed
        assert loaded.current_binding()[3] is fact
    if case=='duplicate_load':
        try:GatewayApprovalOwner.load(owner)
        except GatewayApprovalError:pass
        else:raise AssertionError('duplicate anchor acquisition')
        assert loaded.current_binding()[3] is fact
    if case.startswith('current_'):
        if case=='current_root':constants.ROOT+='-changed'
        if case=='current_function':constants.get_default_hermes_root=lambda:default
        if case=='current_fact_copy':
            replacement=tuple(list(fact));loaded._fact_cell=replacement
            owner._activation._approval_fact_cell=replacement
        if case=='current_root_copy':
            replacement=tuple(list(root));loaded._root_cell=replacement
            owner._activation._approval_cell=replacement
        try:loaded.current_binding()
        except GatewayApprovalError:pass
        else:raise AssertionError('stale root/API/fact accepted')
        constants.ROOT=str(default);constants.get_default_hermes_root=old_function
        loaded._fact_cell=owner._activation._approval_fact_cell=fact
        loaded._root_cell=owner._activation._approval_cell=root
        try:loaded.current_binding()
        except GatewayApprovalError:pass
        else:raise AssertionError('restoration resurrected admission')
print(json.dumps({'case':case,'runtimeQualified':False,'hostChanged':False}))
'''

CASES = (
    'normal', 'operator_selection', 'counts', 'missing', 'leaf_mode', 'directory_mode',
    'symlink', 'hardlink', 'ancestor_link', 'empty', 'oversize', 'noncanonical', 'duplicate',
    'schema_bool', 'selection_schema', 'recipe_bool', 'recipe_size', 'unknown_path', 'bad_hex',
    'selection_digest', 'root_read', 'function_read', 'read_unknown', 'count_copy', 'read_retire',
    'reads_copy', 'close_unknown', 'fact_replaced', 'root_replaced', 'closed_changed',
    'ledger_copy',
    'current_root', 'current_function', 'current_fact_copy', 'current_root_copy', 'wrong_thread',
    'duplicate_load', 'lookalike', 'function_origin', 'callback_origin', 'callback_loader',
    'selection_parent_replaced', 'recipe_variant', 'recipe_size_mismatch',
)


@pytest.mark.parametrize('case', CASES)
def test_fixed_operator_approval(tmp_path: Path, case: str):
    if os.name != 'posix' or os.sys.platform not in ('darwin', 'linux'):
        pytest.skip('supported POSIX startup')
    native = tmp_path / 'native'
    (native / 'pm').mkdir(parents=True)
    (native / 'pm/__init__.py').write_text('')
    (native / 'pm/environments.py').write_text('def activate_dependencies():\n    pass\n')
    (native / 'hermes_bootstrap.py').write_text(BOOTSTRAP)
    default = tmp_path / 'instance'
    directory = default / 'plugin-data/hmp/presentation/gateway-startup'
    directory.mkdir(parents=True, mode=0o700)
    callback = ''
    if case == 'callback_origin':
        callback = '    __spec__.origin += ".changed"\n'
    if case == 'callback_loader':
        callback = '    __spec__.loader = object()\n'
    (native / 'hermes_constants.py').write_text(
        'from pathlib import Path\nROOT=' + repr(str(default))
        + '\ndef get_default_hermes_root():\n' + callback + '    return Path(ROOT)\n')
    environment = tmp_path / 'generation/lib/python3.14/site-packages'
    environment.mkdir(parents=True)
    script = tmp_path / 'entry.py'
    source = ENTRY_SCRIPT[:ENTRY_SCRIPT.rfind('print(json.dumps')]
    source = source.replace('package, root, environment, mutation = sys.argv[1:]',
                            'package, root, environment, mutation = sys.argv[1:5]')
    script.write_text(source + BODY)
    result = subprocess.run(
        [os.sys.executable, '-I', '-B', str(script), str(PACKAGE), str(native),
         str(environment), 'normal', case], capture_output=True, text=True, timeout=30,
        env={'LANG': 'C', 'LC_ALL': 'C'})
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['case'] == case


@pytest.mark.parametrize("variant", ["entry", "runtime", "links", "document_boundary"])
def test_operator_approval_composes_with_original_snapshot(tmp_path, monkeypatch, variant):
    from . import test_presentation_entry_files as base
    from .test_presentation_executable_link_io import io_script
    from .test_presentation_runtime_files import runtime_script

    script = io_script() if variant == "links" else (
        runtime_script() if variant == "runtime" else base.SCRIPT)
    prefix = r'''
from hmp_startup.gateway_approval import GatewayApprovalOwner
operator_root=base/"operator-instance"
(base/"native/hermes_constants.py").write_text(
    "from pathlib import Path\nROOT="+repr(str(operator_root))+
    "\ndef get_default_hermes_root():\n    return Path(ROOT)\n")
'''
    script = script.replace("entry = GatewayEntryOwner.start()", prefix
                            + "\nentry = GatewayEntryOwner.start()", 1)
    script = script.replace('private = base / "private"',
                            'private = operator_root / '
                            '"plugin-data/hmp/presentation/gateway-startup"'
                            '\nprivate.mkdir(parents=True,mode=0o700)')
    old = """configuration = StartupSelectionOwner.load_recipe_selection(entry._activation,
    a.ExpectedArtifact(str(path),len(selection),hashlib.sha256(selection).hexdigest()))"""
    replacement = r'''
operator_raw=canonical(dict(schema=1,kind="HMP_GATEWAY_OPERATOR_APPROVAL",selection_schema=2,
    selection_size=len(selection),selection_sha256=hashlib.sha256(selection).hexdigest(),
    recipe_schema=2,recipe_size=len(recipe_raw)))
operator_path=private/"gateway-approval.json"
operator_path.write_bytes(operator_raw);operator_path.chmod(0o600)
approval=GatewayApprovalOwner.load(entry)
configuration=StartupSelectionOwner.load_operator_selection(approval)
assert configuration._bytes_read==len(operator_raw)+len(selection)
'''
    assert old in script
    if variant != "links":
        replacement = replacement.replace("recipe_schema=2", "recipe_schema=1")
    script = script.replace(old, replacement, 1)
    if variant == "document_boundary":
        script = script.replace("recipe = GatewayRecipeOwner.load(configuration,len(recipe_raw))",
            "from hmp_plugin import presentation_gateway_recipe as recipe_module\n"
            "recipe_module._TOTAL_LIMIT=len(recipe_raw)+sum(map(len,children))\n"
            "recipe = GatewayRecipeOwner.load(configuration,len(recipe_raw))\n"
            "assert recipe._bytes_read==len(operator_raw)+len(selection)"
            "+recipe_module._TOTAL_LIMIT")
    mutation = {"runtime": "runtime_normal", "links": "link_absolute"}.get(variant, "normal")
    monkeypatch.setattr(base, "SCRIPT", script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
