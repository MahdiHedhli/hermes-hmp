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

from .presentation_startup_artifacts import (
    ArtifactObservationError, ExpectedArtifact, _RuntimeSource,
)


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
    error = ArtifactObservationError
    need, need_code = _need, _need.__code__
    tail, tail_code = _policy_tail, _policy_tail.__code__
    parts, parts_code = _parts, _parts.__code__
    kind = _LinkPathPolicy
    from hmp_startup.runtime_files import ExecutableLinkPlan, LinkHop

    if (ArtifactObservationError is not error
            or _need is not need or need.__code__ is not need_code
            or _policy_tail is not tail or tail.__code__ is not tail_code
            or _parts is not parts or parts.__code__ is not parts_code
            or _LinkPathPolicy is not kind):
        raise error from None
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

    def rejoin():
        # Held helper/class identities before first path decoding, after each
        # actual helper return and after construction; never adopt a callback's
        # current replacement as the factory's original dependency.
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

    rejoin()
    need(type(plan) is ExecutableLinkPlan and type(plan.target) is ExpectedArtifact
         and (hop is None or type(hop) is LinkHop))
    path = plan.target.path if hop is None else hop.path
    components = parts(path)
    rejoin()
    values = (plan, hop, index, phase, actor_uid, bound, path, components)
    constructor = pins[0][3]
    policy = constructor(kind, *values)
    rejoin()
    need(type(policy) is kind and tuple.__len__(policy) == len(values)
         and all(tuple.__getitem__(policy, i) is value for i, value in enumerate(values)))
    validated = tail(policy)
    rejoin()
    need(validated is policy)
    return policy


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


class _LinkScopeBlueprint(NamedTuple):
    owner: object
    runtime: object
    context: tuple
    lineage: object
    origin: tuple
    plan: object
    link: object
    rows: tuple

    def __repr__(self):
        return '<ExecutableLinkScopeBlueprint DATA not-native-admission redacted>'


def _scope_blueprint_guard(origin):
    # The independently anchored caller supplies the ACTUAL original origin.
    # This shape checker cannot establish independent ownership of copied DATA.
    if type(origin) is not tuple or len(origin) != 5:
        raise ArtifactObservationError from None
    own = tuple.__getitem__(origin, 2)
    if type(own) is not tuple or len(own) != 7:
        raise ArtifactObservationError from None
    row = tuple.__getitem__(own, 3)
    if (type(row) is not tuple or len(row) != 7 or type(row[0]) is not str or row[0] != 'current'
            or type(row[1]) is not FunctionType or type(row[3]) is not dict
            or any(type(k) is not str for k in row[3])
            or row[3].get('current') is not row[1]
            or row[1].__code__ is not row[2] or row[1].__globals__ is not row[3]
            or row[1].__defaults__ is not row[4] or row[1].__kwdefaults__ is not row[5]
            or type(row[5]) is not dict or type(row[6]) is not tuple
            or any(type(k) is not str for k in row[5])
            or len(row[5]) != len(row[6])
            or any(type(pair) is not tuple or len(pair) != 2 or type(pair[0]) is not str
                   or pair[0] not in row[5] or row[5][pair[0]] is not pair[1]
                   for pair in row[6])):
        raise ArtifactObservationError from None
    result = row[1](origin)
    if result is not origin:
        raise ArtifactObservationError from None
    return origin


def _scope_blueprint_cohort(cohort):
    # Raw snapshots supplied/retained by the actual publication caller. No
    # owner/class/Scope getter and no authority is inferred from these values.
    _need(type(cohort) is tuple and len(cohort) == 3
          and type(cohort[0]) is tuple and len(cohort[0]) == 5
          and type(cohort[1]) is tuple and len(cohort[1]) == 5)
    for row in cohort[0]:
        _need(type(row) is tuple and len(row) == 2)
        names, entries = row
        _need(type(names) is dict and type(entries) is tuple
              and all(type(k) is str for k in names) and len(names) == len(entries)
              and all(type(row) is tuple and len(row) == 2 and type(row[0]) is str
                      and row[0] in names and names[row[0]] is row[1] for row in entries))
    for row in cohort[1]:
        _need(type(row) is tuple and len(row) == 2)
        values, entries = row
        _need(type(values) is list and type(entries) is tuple
              and len(values) == len(entries)
              and all(values[i] is entry for i, entry in enumerate(entries)))
    _need(type(cohort[2]) is tuple and len(cohort[2]) == 5)
    for row in cohort[2]:
        _need(type(row) is tuple and len(row) == 3 and type(row[0]) is type
              and type(row[1]) is tuple and type(row[2]) is tuple)
        kind, entries, functions = row
        names = vars(kind)
        _need(all(type(k) is str for k in names) and len(names) == len(entries)
              and all(type(pair) is tuple and len(pair) == 2 and type(pair[0]) is str
                      and pair[0] in names and names[pair[0]] is pair[1] for pair in entries))
        for function, code, defaults, kw, pairs in functions:
            _need(type(function) is FunctionType and function.__code__ is code
                  and function.__defaults__ is defaults and function.__kwdefaults__ is kw)
            if kw is not None:
                _need(type(kw) is dict and all(type(k) is str for k in kw)
                      and len(kw) == len(pairs)
                      and all(k in kw and kw[k] is value for k, value in pairs))
    return cohort


def _scope_blueprint_tail(blueprint):
    error = ArtifactObservationError
    need, need_code = _need, _need.__code__
    guard, guard_code = _scope_blueprint_guard, _scope_blueprint_guard.__code__
    kind = _LinkScopeBlueprint
    if type(blueprint) is not kind:
        raise error from None
    origin = tuple.__getitem__(blueprint, 4)

    def rejoin():
        if (_need is not need or need.__code__ is not need_code
                or _scope_blueprint_guard is not guard or guard.__code__ is not guard_code):
            raise error from None
        guard(origin)
        if (_need is not need or need.__code__ is not need_code
                or _scope_blueprint_guard is not guard or guard.__code__ is not guard_code):
            raise error from None

    rejoin()
    runtime = blueprint.runtime
    plan_kind, link_kind = origin[4][3][0], origin[4][4][0]
    need(type(runtime) is _RuntimeSource and type(runtime.plan) is plan_kind
         and type(runtime.link) is link_kind
         and type(runtime.link.hops) is tuple and 1 <= len(runtime.link.hops) <= 8)
    need(blueprint.plan is runtime.plan
         and blueprint.link is runtime.link and blueprint.plan.executable_link is blueprint.link
         and type(blueprint.context) is tuple and len(blueprint.context) == 3
         and all(type(v) is int for v in blueprint.context)
         and type(blueprint.rows) is tuple
         and len(blueprint.rows) == 3 * (len(blueprint.link.hops) + 1))
    tail, tail_code = _policy_tail, _policy_tail.__code__
    ordinal = 0
    for phase in ('before', 'after', 'recheck'):
        for index in range(len(blueprint.link.hops) + 1):
            rejoin()
            if _policy_tail is not tail or tail.__code__ is not tail_code:
                raise error from None
            row = blueprint.rows[ordinal]
            need(type(row) is _LinkPathPolicy)
            hop = (None if index == len(blueprint.link.hops)
                   else blueprint.link.hops[index])
            need(type(row.index) is int and type(row.phase) is str
                 and type(row.actor_uid) is int and type(row.bound) is int
                 and row.plan is blueprint.link and row.hop is hop and row.index == index
                 and row.phase == phase and row.actor_uid is blueprint.context[1]
                 and row.bound is runtime.bound)
            actual = tail(row)
            rejoin()
            need(actual is row)
            ordinal += 1
    rejoin()
    return blueprint


def _new_scope_blueprint(owner, runtime, context, lineage, origin, cohort):
    # This function treats owner/lineage as opaque original-pointer DATA. Actual
    # entry/lineage/source authority and class seals belong to _retain, not here.
    error = ArtifactObservationError
    need, need_code = _need, _need.__code__
    guard, guard_code = _scope_blueprint_guard, _scope_blueprint_guard.__code__
    check, check_code = _scope_blueprint_cohort, _scope_blueprint_cohort.__code__
    factory, factory_code = _new_policy, _new_policy.__code__
    tail, tail_code = _scope_blueprint_tail, _scope_blueprint_tail.__code__
    kind = _LinkScopeBlueprint

    def rejoin():
        if (_need is not need or need.__code__ is not need_code
                or _scope_blueprint_guard is not guard or guard.__code__ is not guard_code
                or _scope_blueprint_cohort is not check or check.__code__ is not check_code
                or _new_policy is not factory or factory.__code__ is not factory_code
                or _scope_blueprint_tail is not tail or tail.__code__ is not tail_code):
            raise error from None
        guard(origin)
        if (_need is not need or need.__code__ is not need_code
                or _scope_blueprint_guard is not guard or guard.__code__ is not guard_code
                or _scope_blueprint_cohort is not check or check.__code__ is not check_code):
            raise error from None
        actual = check(cohort)
        if (actual is not cohort or _need is not need or need.__code__ is not need_code
                or _scope_blueprint_guard is not guard or guard.__code__ is not guard_code
                or _scope_blueprint_cohort is not check or check.__code__ is not check_code
                or _new_policy is not factory or factory.__code__ is not factory_code
                or _scope_blueprint_tail is not tail or tail.__code__ is not tail_code):
            raise error from None

    rejoin()
    plan_kind, link_kind = origin[4][3][0], origin[4][4][0]
    need(type(runtime) is _RuntimeSource and type(runtime.plan) is plan_kind
         and type(runtime.link) is link_kind
         and type(runtime.link.hops) is tuple and 1 <= len(runtime.link.hops) <= 8
         and type(context) is tuple and len(context) == 3
         and all(type(v) is int for v in context)
         and runtime.plan.executable_link is runtime.link)
    rows = []
    for phase in ('before', 'after', 'recheck'):
        for index in range(len(runtime.link.hops) + 1):
            rejoin()
            hop = None if index == len(runtime.link.hops) else runtime.link.hops[index]
            row = factory(runtime.link, hop, index, phase, context[1], runtime.bound)
            rejoin()
            need(type(row) is _LinkPathPolicy and row.plan is runtime.link
                 and row.hop is hop and row.index == index and row.phase == phase
                 and row.actor_uid is context[1] and row.bound is runtime.bound)
            rows.append(row)
    rejoin()
    values = (owner, runtime, context, lineage, origin, runtime.plan, runtime.link, tuple(rows))
    constructor = vars(kind)['__new__']
    if type(constructor) is staticmethod:
        constructor = constructor.__func__
    result = constructor(kind, *values)
    rejoin()
    need(type(result) is kind and tuple.__len__(result) == len(values)
         and all(tuple.__getitem__(result, i) is value for i, value in enumerate(values)))
    actual = tail(result)
    rejoin()
    need(actual is result)
    return result
