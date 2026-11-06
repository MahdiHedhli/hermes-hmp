"""Execution-owner causals using fake driver receipts; no native execution."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

PATH = Path(__file__).resolve().parents[3] / 'tools/compat/local_media_native_writer_supplement.py'
SOURCE = 'a' * 40
NATIVE = 'b' * 40
REPORT = 'c' * 64


def setup(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('_supplement_tests', PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    root = tmp_path / 'fresh'
    root.mkdir(mode=0o700)
    calls = []
    monkeypatch.setattr(module.driver, 'validate_archive_cache', lambda cache: None)
    monkeypatch.setattr(module.shutil, 'disk_usage', lambda root: SimpleNamespace(
        free=module.RESERVE + module.ALLOWANCE))

    def fixture(child, native_repository, native_commit, **kwargs):
        state = json.loads((root / 'supplement-state.json').read_text())
        assert state['stage'] == 'job_attempted' and state['current']['root'] == str(child)
        assert child.is_dir() and not any(child.iterdir())
        assert native_commit == NATIVE and kwargs['expected_hmp_commit'] == SOURCE
        assert kwargs['sample_binding_seed'] is True
        calls.append((child, kwargs))
        return {'completed': True, 'hmp_commit': SOURCE, 'native_commit': NATIVE,
                'report_sha256': REPORT}

    monkeypatch.setattr(module.driver, 'run_fixture', fixture)
    return module, root, calls, fixture


def run(module, root, cache=('explicit', 'cache')):
    return module.run_supplement(root, Path('/unused-native'), NATIVE, SOURCE,
                                 native_archive_cache=cache)


def test_complete_scope_maps_every_call_to_original_phase_without_full_pass(tmp_path, monkeypatch):
    module, root, calls, _ = setup(tmp_path, monkeypatch)
    state = run(module, root)
    plan = module.partition.supplemental_plan(module.partition.contract.paired_plan())
    assert len(calls) == len(state['completed']) == 90
    assert state['phases_planned'] == 144 and state['current'] is None
    assert state['scope_execution_completed'] is True
    assert state['full_matrix_completed'] is False and state['production_qualified'] is False
    assert state['base_phases_included'] is False
    for row, job, (_, kwargs) in zip(state['completed'], plan['jobs'], calls, strict=True):
        assert row['origin_pair'] == job['origin_pair']
        assert row['origin_phases'] == job['origin_phases']
        assert kwargs['binding_writer'] == job['request']
        assert kwargs['binding_cost_case'] == job['case']
        assert kwargs['binding_cost_selector'] == job['selector']


@pytest.mark.parametrize('bad', ['exception', 'cancel', 'unknown', 'source', 'native', 'hash'])
def test_first_ambiguous_job_retained_no_later_admission_or_retry(tmp_path, monkeypatch, bad):
    module, root, calls, fixture = setup(tmp_path, monkeypatch)

    def fail(*args, **kwargs):
        receipt = fixture(*args, **kwargs)
        if bad == 'exception':
            raise RuntimeError('fixture failed')
        if bad == 'cancel':
            raise KeyboardInterrupt
        key, value = {'unknown': ('completed', False), 'source': ('hmp_commit', 'd'*40),
                      'native': ('native_commit', 'd'*40), 'hash': ('report_sha256', 'd'*40)}[bad]
        receipt[key] = value
        return receipt

    monkeypatch.setattr(module.driver, 'run_fixture', fail)
    with pytest.raises(KeyboardInterrupt if bad == 'cancel' else RuntimeError):
        run(module, root)
    state = json.loads((root / 'supplement-state.json').read_text())
    assert len(calls) == 1 and state['stage'] == 'job_failed_no_retry'
    assert state['current']['index'] == 0 and not state['completed']
    assert not (root / 'job-001').exists()
    with pytest.raises(RuntimeError):
        run(module, root)
    assert len(calls) == 1


def test_capacity_is_checked_again_before_next_job_without_replaying_first(tmp_path, monkeypatch):
    module, root, calls, _ = setup(tmp_path, monkeypatch)
    monkeypatch.setattr(module.shutil, 'disk_usage', lambda root: SimpleNamespace(
        free=module.RESERVE + module.ALLOWANCE - (1 if calls else 0)))
    state = run(module, root)
    assert len(calls) == 1 and state['stage'] == 'capacity_refused_before_next_job'
    assert len(state['completed']) == 1 and state['current'] is None
    assert state['scope_execution_completed'] is False
    assert not (root / 'job-001').exists()


@pytest.mark.parametrize('bad', ['cache', 'nonempty', 'permissions', 'symlink', 'source'])
def test_invalid_admission_has_no_native_call(tmp_path, monkeypatch, bad):
    module, root, calls, _ = setup(tmp_path, monkeypatch)
    cache = ('explicit', 'cache')
    if bad == 'cache':
        cache = None
    elif bad == 'nonempty':
        (root / 'existing').write_text('retained')
    elif bad == 'permissions':
        root.chmod(0o755)
    elif bad == 'symlink':
        alias = tmp_path / 'alias'
        alias.symlink_to(root, target_is_directory=True)
        root = alias
    else:
        with pytest.raises(RuntimeError):
            module.run_supplement(root, Path('/unused-native'), NATIVE, True,
                                  native_archive_cache=cache)
        assert not calls
        return
    with pytest.raises(RuntimeError):
        run(module, root, cache)
    assert not calls
