"""Fixed link traversal DATA controls, not native/ACK/character acceptance."""
import pytest

from hmp_startup.runtime_files import ExecutableLinkPlan, LinkHop
from hmp_plugin import presentation_link_path_policy as policy
from hmp_plugin.presentation_startup_artifacts import ArtifactObservationError, ExpectedArtifact

ROOT = (1, 10, 0o040755, 0, 0)
PARENT = (1, 11, 0o040700, 1000, 1000)
LINK = (1, 12, 0o120777, 1000, 1000, 1, 6, 1, 2)
TARGET = (1, 13, 0o100700, 1000, 1000, 1, 10, 1, 2)


def _policy(phase='before', target=False):
    hop = LinkHop('/parent/python', b'target', '/parent/target')
    plan = ExecutableLinkPlan((hop,), ExpectedArtifact('/parent/target', 10, '0' * 64),
                              1000, 0o700, 6)
    return policy._new_policy(plan, None if target else hop, 1 if target else 0,
                              phase, 1000, 4096)


def _step(cursor):
    kind, argument, parent = policy._action(cursor)
    if kind == 'open':
        return policy._advance(cursor, 'opened')
    if kind == 'readlink':
        return policy._advance(cursor, 'returned', b'target')
    if kind == 'fstat':
        value = (ROOT, PARENT)[argument]
    elif argument in ('/', 'parent'):
        value = ROOT if parent is None else PARENT
    else:
        value = TARGET if cursor.policy.hop is None else LINK
    return policy._advance(cursor, 'returned', value)


def _at(position, p=None):
    cursor = policy._start(_policy() if p is None else p)
    for _ in range(position):
        cursor = _step(cursor)
    return cursor


@pytest.mark.parametrize('phase,target,read', [
    ('before', False, True), ('after', False, True), ('recheck', False, False),
    ('before', True, False), ('after', True, False), ('recheck', True, False),
])
def test_complete_fixed_traversal_and_literal_policy_predecessors(phase, target, read):
    cursor = policy._start(_policy(phase, target))
    leaf = 'target' if target else 'python'
    expected = [('open', '/', None), ('fstat', 0, None),
                ('open', 'parent', 0), ('fstat', 1, None), ('stat', leaf, 1)]
    if read:
        expected.append(('readlink', 'python', 1))
    expected += [('stat', leaf, 1), ('fstat', 0, None), ('stat', '/', None),
                 ('fstat', 1, None), ('stat', 'parent', 0)]
    actions = []
    while policy._action(cursor) is not None:
        actions.append(policy._action(cursor))
        previous = cursor
        cursor = _step(cursor)
        assert cursor.predecessor is previous
        assert cursor.policy is previous.policy
    assert actions == expected
    assert policy._outcome(cursor) == (
        TARGET if target else LINK, (('/', ROOT), ('parent', PARENT)), 6 if read else None)
    with pytest.raises(ArtifactObservationError):
        policy._advance(cursor, 'returned', LINK)


@pytest.mark.parametrize('position', (1, 3, 4, 6, 7, 8, 9, 10))
def test_changed_metadata_at_each_consumption_site_refuses(position):
    cursor = _at(position)
    kind, argument, parent = policy._action(cursor)
    if position == 4:
        value = (*LINK[:6], 999, *LINK[7:])
    elif position == 6:
        value = (99, *LINK[1:])
    else:
        base = ROOT if (kind == 'fstat' and argument == 0 or kind == 'stat' and parent is None) else PARENT
        # Initial directories must be safe; final identities must match exactly.
        value = (99, *base[1:]) if position >= 7 else (*base[:2], 0o040777, 1000, 1000)
    with pytest.raises(ArtifactObservationError):
        policy._advance(cursor, 'returned', value)
    assert cursor.position == position


@pytest.mark.parametrize('value', (b'other!', b'', 'python', b'x' * 4096))
def test_readlink_requires_exact_bounded_bytes(value):
    with pytest.raises(ArtifactObservationError):
        policy._advance(_at(5), 'returned', value)


@pytest.mark.parametrize('position', (0, 1, 4, 5, 7))
def test_missing_error_or_open_category_cannot_be_relabeled_as_success(position):
    cursor = _at(position)
    with pytest.raises(ArtifactObservationError):
        policy._advance(cursor, 'reported_missing')


def test_actual_readlink_return_bytes_are_not_retained_as_policy_history():
    actual = bytes(bytearray(b'target'))
    cursor = policy._advance(_at(5), 'returned', actual)
    assert cursor.link_length == 6
    while cursor is not None:
        assert all(field is not actual for field in cursor)
        cursor = cursor.predecessor


def test_foreign_inputs_never_invoke_protocol_hooks():
    class Foreign:
        def __getattribute__(self, name):
            raise AssertionError('foreign getattr')
        def __eq__(self, other):
            raise AssertionError('foreign equality')
        def __iter__(self):
            raise AssertionError('foreign iteration')
    foreign = Foreign()
    p = _policy()
    cursor = policy._start(p)
    for operation in (
        lambda: policy._policy_tail(foreign),
        lambda: policy._cursor_tail(foreign),
        lambda: policy._policy_tail(p._replace(components=(foreign,))),
        lambda: policy._policy_tail(p._replace(plan=foreign)),
        lambda: policy._policy_tail(p._replace(
            plan=p.plan._replace(target=p.plan.target._replace(path=foreign)))),
        lambda: policy._advance(cursor, foreign),
        lambda: policy._advance(_at(5), 'returned', foreign),
    ):
        with pytest.raises(ArtifactObservationError):
            operation()


@pytest.mark.parametrize('field,value', [
    ('phase', 'caller-selected'), ('index', True), ('bound', 4097),
    ('path', '/other/python'), ('components', ('/', '..', 'python')),
])
def test_invalid_policy_fields_refuse(field, value):
    with pytest.raises(ArtifactObservationError):
        policy._start(_policy()._replace(**{field: value}))


@pytest.mark.parametrize('field,value', [('uid', 1001), ('mode', 0o777),
                                       ('mode', 0o600), ('mode', 0o4700)])
def test_target_privilege_policy_drift_refuses(field, value):
    p = _policy()
    with pytest.raises(ArtifactObservationError):
        policy._start(p._replace(plan=p.plan._replace(**{field: value})))


def test_multi_hop_continuity_and_selected_hop_identity():
    first = LinkHop('/parent/python', b'next', '/parent/next')
    second = LinkHop('/parent/next', b'target', '/parent/target')
    original = _policy().plan
    plan = original._replace(hops=(first, second), text_bytes=10)
    p = policy._new_policy(plan, second, 1, 'before', 1000, 4096)
    assert p.hop is second and p.path is second.path
    with pytest.raises(ArtifactObservationError):
        policy._new_policy(plan, first, 1, 'before', 1000, 4096)
    broken = plan._replace(hops=(first, second._replace(path='/other/next')))
    with pytest.raises(ArtifactObservationError):
        policy._new_policy(broken, first, 0, 'before', 1000, 4096)
    with pytest.raises(ArtifactObservationError):
        policy._new_policy(plan._replace(target=original.target._replace(path='/other/target')),
                           first, 0, 'before', 1000, 4096)


@pytest.mark.parametrize('path', ('/python', '/same/same/python'))
def test_parent_role_order_handles_root_and_repeated_component_names(path):
    p = _policy()
    target_path = path.rsplit('/', 1)[0] + '/target'
    hop = p.hop._replace(path=path, destination=target_path)
    plan = p.plan._replace(hops=(hop,), target=p.plan.target._replace(path=target_path))
    p = policy._new_policy(plan, hop, 0, 'before', 1000, 4096)
    cursor = policy._start(p)
    parents = len(p.components) - 1
    signatures = tuple((1, i + 10, 0o040755, 0, 0) for i in range(parents))
    while (action := policy._action(cursor)) is not None:
        kind, name, parent = action
        if kind == 'open':
            cursor = policy._advance(cursor, 'opened')
        elif kind == 'readlink':
            cursor = policy._advance(cursor, 'returned', b'target')
        elif kind == 'fstat':
            cursor = policy._advance(cursor, 'returned', signatures[name])
        elif name == 'python' and parent == parents - 1:
            cursor = policy._advance(cursor, 'returned', LINK)
        else:
            index = 0 if parent is None else parent + 1
            cursor = policy._advance(cursor, 'returned', signatures[index])
    assert len(policy._outcome(cursor)[1]) == parents


@pytest.mark.parametrize('uid,accepted', [(0, True), (1000, False)])
def test_only_root_sticky_writable_parent_is_safe(uid, accepted):
    cursor = _at(1)
    value = (1, 10, 0o041777, uid, 0)
    if accepted:
        assert policy._advance(cursor, 'returned', value).directories == (value,)
    else:
        with pytest.raises(ArtifactObservationError):
            policy._advance(cursor, 'returned', value)


@pytest.mark.parametrize('index,value', [(2, 0o100777), (3, 999), (5, 2), (6, 11)])
def test_final_target_metadata_matches_original_privilege_and_size(index, value):
    cursor = _at(4, _policy(target=True))
    changed = list(TARGET)
    changed[index] = value
    with pytest.raises(ArtifactObservationError):
        policy._advance(cursor, 'returned', tuple(changed))


def test_component_and_utf8_path_bounds():
    assert len(policy._parts('/' + '/'.join(['a'] * 64))) == 65
    assert policy._parts('/' + 'é' * 2047)
    for path in ('/' + '/'.join(['a'] * 65), '/' + 'é' * 2048, '/x/../python', '/x/\ud800'):
        with pytest.raises(ArtifactObservationError):
            policy._parts(path)
