"""Startup ordering DATA tests; not filesystem, native ACK or startup acceptance."""
import pytest

from hmp_plugin import presentation_startup_probe_policy as policy
from hmp_plugin.presentation_startup_artifacts import ArtifactObservationError

ROOT = (1, 10, 0o040755, 0, 0)
PARENT = (1, 11, 0o040700, 1000, 1000)
LEAF = (1, 12, 0o040700, 1000, 1000)


def _next(cursor, missing=2):
    kind = cursor.action
    if kind in ('root_open', 'component_open'):
        return policy._advance(cursor, 'opened')
    if kind == 'confirmation' or kind == 'component_stat' and cursor.component == missing:
        return policy._advance(cursor, 'reported_missing')
    identity = ROOT if kind == 'root_fstat' else PARENT
    if kind in ('pre_fstat', 'pre_stat', 'post_fstat', 'post_stat'):
        identity = (ROOT, PARENT)[cursor.ancestor]
    return policy._advance(cursor, 'returned', identity)


def _at(kind, missing=2):
    cursor = policy._start(policy._new_policy('/parent/leaf', 1000))
    for _ in range(32):
        if cursor.action == kind:
            return cursor
        cursor = _next(cursor, missing)
    raise AssertionError('requested contract boundary was not reached')


@pytest.mark.parametrize('missing,order,index,ancestors', [
    (1, ['root_open', 'root_fstat', 'component_stat', 'pre_fstat', 'pre_stat',
         'confirmation', 'post_fstat', 'post_stat'], 0, (('/', ROOT),)),
    (2, ['root_open', 'root_fstat', 'component_stat', 'component_open',
         'component_fstat', 'component_stat', 'pre_fstat', 'pre_stat',
         'pre_fstat', 'pre_stat', 'confirmation', 'post_fstat', 'post_stat',
         'post_fstat', 'post_stat'], 1, (('/', ROOT), ('parent', PARENT))),
])
def test_absence_requires_root_open_and_two_complete_ordered_ancestor_passes(
    missing, order, index, ancestors,
):
    cursor = policy._start(policy._new_policy('/parent/leaf', 1000))
    actions, actual_returns = [], []
    while cursor.action != 'finished':
        actions.append(cursor.action)
        actual_returns.append(cursor)
        following = _next(cursor, missing)
        assert following.predecessor is cursor
        assert following.sequence == cursor.sequence + 1
        cursor = following
    assert actions == order
    assert policy._action(actual_returns[0]) == ('open', '/', None)
    assert policy._action(actual_returns[1]) == ('fstat', 0, None)
    assert policy._outcome(cursor) == ('/parent/leaf', index, ancestors)
    assert policy._action(cursor) is None
    with pytest.raises(ArtifactObservationError):
        policy._advance(cursor, 'reported_missing')


@pytest.mark.parametrize('kind', ('pre_fstat', 'pre_stat', 'post_fstat', 'post_stat'))
def test_replaced_ancestor_refuses_in_either_pass(kind):
    cursor = _at(kind)
    before = cursor
    changed = (1, 999, *ROOT[2:])
    with pytest.raises(ArtifactObservationError):
        policy._advance(cursor, 'returned', changed)
    assert cursor is before


def test_appearance_at_confirmation_refuses():
    cursor = _at('confirmation')
    with pytest.raises(ArtifactObservationError):
        policy._advance(cursor, 'returned', LEAF)


def test_opened_directory_must_match_preceding_stat():
    cursor = _at('component_fstat')
    with pytest.raises(ArtifactObservationError):
        policy._advance(cursor, 'returned', (1, 999, *PARENT[2:]))


@pytest.mark.parametrize('mode,uid', ((0o040700, 1000), (0o100600, 1000),
                                   (0o120700, 1000), (0o040777, 1000),
                                   (0o044700, 1000), (0o040700, 1001)))
def test_present_leaf_or_unsafe_directory_never_becomes_absence(mode, uid):
    cursor = _at('component_stat')
    cursor = _next(_next(_next(cursor)))  # stat/open/fstat of parent
    assert cursor.action == 'component_stat' and cursor.component == 2
    with pytest.raises(ArtifactObservationError):
        policy._advance(cursor, 'returned', (1, 12, mode, uid, 1000))


@pytest.mark.parametrize('kind', ('root_open', 'root_fstat', 'component_open',
                                'component_fstat', 'pre_fstat', 'pre_stat',
                                'post_fstat', 'post_stat'))
def test_missing_is_not_accepted_at_other_operations(kind):
    cursor = _at(kind)
    with pytest.raises(ArtifactObservationError):
        policy._advance(cursor, 'reported_missing')


@pytest.mark.parametrize('path', ('relative', '/', '/a/../b', '/a/./b',
                                '/a//b', '/a/', '/a\x00b', '/a\nb'))
def test_path_contract_rejects_noncanonical_or_control_input(path):
    with pytest.raises(ArtifactObservationError):
        policy._new_policy(path, 1000)


def test_foreign_category_and_identity_refuse_without_hooks():
    hooks = []

    class Foreign:
        def __eq__(self, other):
            hooks.append('eq')
            raise AssertionError('foreign comparison')

        def __iter__(self):
            hooks.append('iter')
            raise AssertionError('foreign iterator')

    cursor = _at('root_fstat')
    with pytest.raises(ArtifactObservationError):
        policy._advance(cursor, Foreign(), ROOT)
    with pytest.raises(ArtifactObservationError):
        policy._advance(cursor, 'returned', Foreign())
    assert hooks == []
