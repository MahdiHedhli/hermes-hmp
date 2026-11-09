"""Closed startup absence ordering DATA, not native admission or a receipt.

The native caller must bind the original path/owner/registration, hold each real
open and metadata return, use the shared producer/consumer/ACK machinery, and
carry the literal finish through effect/pass publication. This module performs
no filesystem calls, supplies no authorization, and is not wired into startup.
"""
from __future__ import annotations

from typing import NamedTuple

from .presentation_startup_artifacts import ArtifactObservationError


def _need(value):
    if value is not True:
        raise ArtifactObservationError from None


class _StartupPathPolicy(NamedTuple):
    path: str
    components: tuple
    actor_uid: int

    def __repr__(self):
        return '<StartupAbsencePolicy DATA not-admission>'


class _StartupCursor(NamedTuple):
    policy: _StartupPathPolicy
    action: str
    component: int
    ancestor: int
    identities: tuple
    expected: object
    missing: object
    predecessor: object
    sequence: int

    def __repr__(self):
        return '<StartupAbsenceCursor DATA not-native-return>'


_ACTIONS = ('root_open', 'root_fstat', 'component_stat', 'component_open',
            'component_fstat', 'pre_fstat', 'pre_stat', 'confirmation',
            'post_fstat', 'post_stat', 'finished')


def _new_policy(path, actor_uid):
    _need(type(path) is str and type(actor_uid) is int and actor_uid >= 0
          and path.startswith('/')
          and all(32 <= ord(char) != 127 and not 0xD800 <= ord(char) <= 0xDFFF
                  for char in path)
          and 1 < len(path.encode('utf-8')) <= 4096)
    parts = tuple(path[1:].split('/'))
    _need(1 <= len(parts) <= 64
          and all(part not in ('', '.', '..') for part in parts))
    return _StartupPathPolicy(path, ('/', *parts), actor_uid)


def _policy_tail(policy):
    _need(type(policy) is _StartupPathPolicy and type(policy.path) is str
          and type(policy.actor_uid) is int and policy.actor_uid >= 0
          and type(policy.components) is tuple and 2 <= len(policy.components) <= 65
          and all(type(part) is str for part in policy.components)
          and policy.components[0] == '/'
          and all(part not in ('', '.', '..') and '/' not in part
                  for part in policy.components[1:])
          and policy.path == '/' + '/'.join(policy.components[1:])
          and all(32 <= ord(char) != 127 and not 0xD800 <= ord(char) <= 0xDFFF
                  for char in policy.path)
          and 1 < len(policy.path.encode('utf-8')) <= 4096)
    return policy


def _directory(identity, policy):
    _need(type(identity) is tuple and len(identity) == 5
          and all(type(value) is int for value in identity))
    mode, uid = identity[2:4]
    _need(mode & 0o170000 == 0o040000 and uid in (0, policy.actor_uid)
          and not mode & 0o6000
          and (not mode & 0o022 or (uid == 0 and mode & 0o1000 != 0)))
    return identity


def _cursor_tail(cursor):
    _need(type(cursor) is _StartupCursor)
    policy = _policy_tail(cursor.policy)
    _need(type(cursor.action) is str and cursor.action in _ACTIONS
          and type(cursor.component) is int
          and 0 <= cursor.component < len(policy.components)
          and type(cursor.ancestor) is int and cursor.ancestor >= 0
          and type(cursor.identities) is tuple
          and len(cursor.identities) < len(policy.components)
          and type(cursor.sequence) is int and cursor.sequence >= 0
          and (cursor.predecessor is None or type(cursor.predecessor) is _StartupCursor)
          and (cursor.missing is None or type(cursor.missing) is int
               and 1 <= cursor.missing < len(policy.components)))
    for identity in cursor.identities:
        _directory(identity, policy)
    if cursor.expected is not None:
        _directory(cursor.expected, policy)
    if cursor.action in ('root_open', 'root_fstat'):
        _need(cursor.component == 0 and cursor.identities == ()
              and cursor.expected is None and cursor.missing is None)
    elif cursor.action.startswith('component_'):
        _need(cursor.component >= 1 and len(cursor.identities) == cursor.component
              and cursor.missing is None)
        _need((cursor.expected is None if cursor.action == 'component_stat'
               else cursor.expected is not None))
    else:
        _need(cursor.missing is not None and cursor.component == cursor.missing
              and len(cursor.identities) == cursor.missing
              and cursor.ancestor < len(cursor.identities)
              and cursor.expected is None)
    return cursor


def _start(policy):
    _policy_tail(policy)
    return _StartupCursor(policy, 'root_open', 0, 0, (), None, None, None, 0)


def _action(cursor):
    """Return a fixed operation description; descriptor indices are not FDs."""
    _cursor_tail(cursor)
    kind, policy = cursor.action, cursor.policy
    if kind == 'finished':
        return None
    if kind == 'root_open':
        return ('open', '/', None)
    if kind == 'root_fstat':
        return ('fstat', 0, None)
    if kind == 'component_open':
        return ('open', policy.components[cursor.component], cursor.component - 1)
    if kind == 'component_fstat':
        return ('fstat', cursor.component, None)
    if kind in ('component_stat', 'confirmation'):
        return ('stat', policy.components[cursor.component], cursor.component - 1)
    if kind in ('pre_fstat', 'post_fstat'):
        return ('fstat', cursor.ancestor, None)
    _need(kind in ('pre_stat', 'post_stat'))
    return ('stat', policy.components[cursor.ancestor],
            None if cursor.ancestor == 0 else cursor.ancestor - 1)


def _transition(cursor, category, identity=None):
    """Consume decoded policy DATA; this is never a native result/ACK guard."""
    _cursor_tail(cursor)
    _need(type(category) is str
          and category in ('opened', 'returned', 'reported_missing')
          and cursor.action != 'finished')
    policy, kind = cursor.policy, cursor.action
    component, ancestor = cursor.component, cursor.ancestor
    identities, expected, missing = cursor.identities, cursor.expected, cursor.missing
    if kind in ('root_open', 'component_open'):
        _need(category == 'opened' and identity is None)
        kind = 'root_fstat' if kind == 'root_open' else 'component_fstat'
    elif kind == 'component_stat' and category == 'reported_missing':
        _need(identity is None)
        kind, ancestor, missing = 'pre_fstat', 0, component
    elif kind == 'confirmation':
        _need(category == 'reported_missing' and identity is None)
        kind, ancestor = 'post_fstat', 0
    else:
        _need(category == 'returned')
        identity = _directory(identity, policy)
        if kind == 'root_fstat':
            identities, component, kind = (identity,), 1, 'component_stat'
        elif kind == 'component_stat':
            # A present leaf is never unapproved cache absence, even a directory.
            _need(component < len(policy.components) - 1)
            expected, kind = identity, 'component_open'
        elif kind == 'component_fstat':
            _need(identity == expected)
            identities, expected = (*identities, identity), None
            component, kind = component + 1, 'component_stat'
        else:
            _need(kind in ('pre_fstat', 'pre_stat', 'post_fstat', 'post_stat')
                  and identity == identities[ancestor])
            if kind in ('pre_fstat', 'post_fstat'):
                kind = 'pre_stat' if kind == 'pre_fstat' else 'post_stat'
            elif ancestor + 1 < len(identities):
                ancestor += 1
                kind = 'pre_fstat' if kind == 'pre_stat' else 'post_fstat'
            else:
                kind = 'confirmation' if kind == 'pre_stat' else 'finished'
                ancestor = 0
    return (policy, kind, component, ancestor, identities, expected, missing,
            cursor, cursor.sequence + 1)


def _validate_advance(cursor, category, identity, result):
    _cursor_tail(result)
    expected = _transition(cursor, category, identity)
    _need(result.policy is cursor.policy and result.predecessor is cursor
          and tuple.__len__(result) == len(expected)
          and all(tuple.__getitem__(result, index) == value
                  for index, value in enumerate(expected)))
    return result


def _advance(cursor, category, identity=None):
    values = _transition(cursor, category, identity)
    result = _StartupCursor(*values)
    return _validate_advance(cursor, category, identity, result)


def _outcome(cursor):
    _cursor_tail(cursor)
    _need(cursor.action == 'finished' and cursor.missing is not None)
    return (cursor.policy.path, cursor.missing - 1,
            tuple(zip(cursor.policy.components[:cursor.missing],
                      cursor.identities, strict=True)))
