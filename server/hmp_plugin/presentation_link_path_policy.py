"""Closed executable-link ordering DATA, never native admission or a receipt.

Not connected to the native caller. The future driver must independently retain
original plans/callees/descriptors, debit actual work, consume the real result,
retire raw data and hold literal ACK/finish returns across reserved cleanup.
The plan must already be the independently validated original runtime plan;
these consistency checks do not replace its path allowlist/lexical resolution.
"""
from __future__ import annotations

import sys
from types import FunctionType, ModuleType
from typing import NamedTuple

from .presentation_startup_artifacts import ArtifactObservationError, ExpectedArtifact


def _need(value):
    if value is not True:
        raise ArtifactObservationError from None


class _LinkPathPolicy(NamedTuple):
    plan: object
    hop: object
    index: int
    phase: str
    actor_uid: int
    bound: int
    path: str
    components: tuple

    def __repr__(self):
        return '<ExecutableLinkPathPolicy DATA not-admission redacted>'


class _LinkPathCursor(NamedTuple):
    policy: _LinkPathPolicy
    position: int
    directories: tuple
    leaf: object
    link_length: object
    predecessor: object

    def __repr__(self):
        return '<ExecutableLinkPathCursor DATA not-native-return redacted>'


def _parts(path):
    _need(type(path) is str and 1 < len(path) <= 4096
          and path.startswith('/')
          and all(32 <= ord(c) != 127 and not 0xD800 <= ord(c) <= 0xDFFF
                  for c in path))
    parts = tuple(path[1:].split('/'))
    _need(1 <= len(parts) <= 64 and 1 < len(path.encode('utf-8')) <= 4096
          and all(part not in ('', '.', '..') for part in parts))
    return ('/', *parts)


def _policy_tail(policy):
    from hmp_startup.runtime_files import ExecutableLinkPlan, LinkHop

    _need(type(policy) is _LinkPathPolicy)
    plan = policy.plan
    _need(type(plan) is ExecutableLinkPlan and type(plan.hops) is tuple
          and 1 <= len(plan.hops) <= 8 and type(plan.target) is ExpectedArtifact
          and type(plan.uid) is int and plan.uid >= 0
          and type(plan.mode) is int and 0 <= plan.mode <= 0o777
          and not plan.mode & 0o022 and bool(plan.mode & 0o111)
          and type(plan.target.size) is int and 0 <= plan.target.size <= 128 * 1024 * 1024
          and type(plan.text_bytes) is int and plan.text_bytes > 0
          and type(policy.index) is int and 0 <= policy.index <= len(plan.hops)
          and type(policy.phase) is str and policy.phase in ('before', 'after', 'recheck')
          and type(policy.actor_uid) is int and policy.actor_uid >= 0
          and plan.uid in (0, policy.actor_uid)
          and type(policy.bound) is int and policy.bound in (1024, 4096)
          and type(policy.components) is tuple
          and all(type(part) is str for part in policy.components))
    _parts(plan.target.path)  # exact primitive fence before continuity equality
    text_bytes, previous, seen = 0, None, set()
    for hop in plan.hops:
        _need(type(hop) is LinkHop and type(hop.target) is bytes
              and 0 < len(hop.target) < policy.bound)
        _parts(hop.path)
        _parts(hop.destination)
        _need(hop.path not in seen and (previous is None or hop.path == previous))
        seen.add(hop.path)
        _need(hop.destination not in seen)
        previous = hop.destination
        text_bytes += len(hop.target)
    _need(text_bytes == plan.text_bytes and previous == plan.target.path)
    if policy.hop is None:
        _need(policy.index == len(plan.hops) and policy.path is plan.target.path)
    else:
        _need(policy.index < len(plan.hops) and policy.hop is plan.hops[policy.index]
              and policy.path is policy.hop.path)
    _need(policy.components == _parts(policy.path))
    return policy


def _new_policy(plan, hop, index, phase, actor_uid, bound):
    from hmp_startup.runtime_files import ExecutableLinkPlan, LinkHop

    _need(type(plan) is ExecutableLinkPlan and type(plan.target) is ExpectedArtifact
          and (hop is None or type(hop) is LinkHop))
    path = plan.target.path if hop is None else hop.path
    values = (plan, hop, index, phase, actor_uid, bound, path, _parts(path))
    error = ArtifactObservationError
    need, need_code = _need, _need.__code__
    tail, tail_code = _policy_tail, _policy_tail.__code__
    parts, parts_code = _parts, _parts.__code__
    kind = _LinkPathPolicy
    native_module = sys.modules.get('hmp_startup.runtime_files')
    need(type(native_module) is ModuleType)
    dispatch_names = ('__getattribute__', '__getattr__', '__getitem__', '__len__',
                      '__iter__', '__setattr__', '__delattr__')
    pins = []
    for selected in (kind, ExecutableLinkPlan, LinkHop, ExpectedArtifact):
        namespace = vars(selected)
        fields = namespace.get('_fields')
        constructor = namespace.get('__new__')
        if type(constructor) is staticmethod:
            constructor = constructor.__func__
        need(type(selected) is type and type(fields) is tuple
             and all(type(name) is str for name in fields)
             and type(constructor) is FunctionType)
        pins.append((selected, fields, tuple(namespace.get(name) for name in fields),
                     constructor, constructor.__code__, selected.__bases__,
                     tuple(namespace.get(name) for name in dispatch_names)))
    constructor = pins[0][3]
    policy = constructor(kind, *values)
    # Refuse changed helpers before calling one. Use the held exception class,
    # tuple primitives and type dictionaries before any returned-object getter.
    if (ArtifactObservationError is not error
            or _need is not need or need.__code__ is not need_code
            or _policy_tail is not tail or tail.__code__ is not tail_code
            or _parts is not parts or parts.__code__ is not parts_code
            or _LinkPathPolicy is not kind
            or sys.modules.get('hmp_startup.runtime_files') is not native_module
            or vars(native_module).get('ExecutableLinkPlan') is not ExecutableLinkPlan
            or vars(native_module).get('LinkHop') is not LinkHop):
        raise error from None
    for selected, fields, members, original, code, bases, dispatch in pins:
        namespace = vars(selected)
        current = namespace.get('__new__')
        if type(current) is staticmethod:
            current = current.__func__
        need(namespace.get('_fields') is fields and current is original
             and original.__code__ is code and selected.__bases__ is bases
             and all(namespace.get(name) is member
                     for name, member in zip(fields, members, strict=True))
             and all(namespace.get(name) is member
                     for name, member in zip(dispatch_names, dispatch, strict=True)))
    need(type(policy) is kind and tuple.__len__(policy) == len(values)
         and all(tuple.__getitem__(policy, i) is value for i, value in enumerate(values)))
    return tail(policy)


def _sites(policy):
    """Fixed roles, not native args: indices aren't FDs; names aren't encoded.

    The driver must retain the original native fsencode return for readlink,
    rather than assuming UTF-8 filesystem encoding from this DATA descriptor.
    """
    _policy_tail(policy)
    count = len(policy.components) - 1
    sites = []
    for i, name in enumerate(policy.components[:-1]):
        sites.extend((('open', name, None if i == 0 else i - 1),
                      ('fstat', i, None)))
    leaf = policy.components[-1]
    sites.append(('stat', leaf, count - 1))
    if policy.hop is not None and policy.phase != 'recheck':
        sites.append(('readlink', leaf, count - 1))
    sites.append(('stat', leaf, count - 1))
    for i, name in enumerate(policy.components[:-1]):
        sites.extend((('fstat', i, None),
                      ('stat', name, None if i == 0 else i - 1)))
    return tuple(sites)


def _directory(identity, policy):
    _need(type(identity) is tuple and len(identity) == 5
          and all(type(v) is int for v in identity))
    mode, uid = identity[2:4]
    _need(mode & 0o170000 == 0o040000 and uid in (0, policy.actor_uid)
          and not mode & 0o6000
          and (not mode & 0o022 or (uid == 0 and bool(mode & 0o1000))))
    return identity


def _leaf(identity, policy):
    _need(type(identity) is tuple and len(identity) == 9
          and all(type(v) is int for v in identity) and identity[5] == 1)
    mode, uid, size = identity[2], identity[3], identity[6]
    if policy.hop is None:
        _need(mode & 0o170000 == 0o100000 and uid == policy.plan.uid
              and mode & 0o7777 == policy.plan.mode and size == policy.plan.target.size)
    else:
        _need(mode & 0o170000 == 0o120000 and uid in (0, policy.actor_uid)
              and not mode & 0o6000 and size == len(policy.hop.target))
    return identity


def _cursor_tail(cursor):
    _need(type(cursor) is _LinkPathCursor)
    policy = _policy_tail(cursor.policy)
    sites = _sites(policy)
    count = len(policy.components) - 1
    _need(type(cursor.position) is int and 0 <= cursor.position <= len(sites)
          and type(cursor.directories) is tuple
          and len(cursor.directories) == min(cursor.position // 2, count)
          and ((cursor.position == 0 and cursor.predecessor is None)
               or (cursor.position > 0 and type(cursor.predecessor) is _LinkPathCursor
                   and cursor.predecessor.policy is policy
                   and type(cursor.predecessor.position) is int
                   and cursor.predecessor.position == cursor.position - 1)))
    for identity in cursor.directories:
        _directory(identity, policy)
    if cursor.position <= 2 * count:
        _need(cursor.leaf is None and cursor.link_length is None)
    else:
        _leaf(cursor.leaf, policy)
        observed = policy.hop is not None and policy.phase != 'recheck'
        if observed and cursor.position > 2 * count + 1:
            _need(type(cursor.link_length) is int
                  and cursor.link_length == len(policy.hop.target))
        else:
            _need(cursor.link_length is None)
    return cursor


def _start(policy):
    _policy_tail(policy)
    return _LinkPathCursor(policy, 0, (), None, None, None)


def _action(cursor):
    _cursor_tail(cursor)
    sites = _sites(cursor.policy)
    return None if cursor.position == len(sites) else sites[cursor.position]


def _advance(cursor, category, value=None):
    """Consume decoded DATA; neither a native result nor an admission token."""
    _cursor_tail(cursor)
    action = _action(cursor)
    _need(action is not None and type(category) is str)
    policy, pos = cursor.policy, cursor.position
    count = len(policy.components) - 1
    directories, leaf, length = cursor.directories, cursor.leaf, cursor.link_length
    kind, argument, _ = action
    if kind == 'open':
        _need(category == 'opened' and value is None)
    elif kind == 'readlink':
        _need(category == 'returned' and type(value) is bytes
              and len(value) < policy.bound and value == policy.hop.target)
        length = len(value)  # do not retain the actual result bytes in history
    else:
        _need(category == 'returned')  # no absence/error-as-success interpretation
        if pos < 2 * count:
            directories = (*directories, _directory(value, policy))
        elif kind == 'stat' and argument == policy.components[-1] and action[2] == count - 1:
            actual = _leaf(value, policy)
            if leaf is None:
                leaf = actual
            else:
                _need(actual == leaf)
        else:
            index = argument if kind == 'fstat' else next(
                i for i, name in enumerate(policy.components[:-1])
                if name == argument and (None if i == 0 else i - 1) == action[2])
            _need(_directory(value, policy) == directories[index])
    result = _LinkPathCursor(policy, pos + 1, directories, leaf, length, cursor)
    return _cursor_tail(result)


def _outcome(cursor):
    _cursor_tail(cursor)
    _need(_action(cursor) is None)
    return cursor.leaf, tuple(zip(cursor.policy.components[:-1], cursor.directories,
                                  strict=True)), cursor.link_length
