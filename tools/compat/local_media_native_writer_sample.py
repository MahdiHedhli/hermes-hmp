"""Owned native-writer fixture foundations; inert import, no live-home discovery.

This module alone performs no native operation. Caller-supplied jobs must use
only reviewed public APIs on a disposable DB. An actor is retained before thread
start; neither a failed start nor a failed release can masquerade as safe closure.
"""

READS = ("get_session", "get_session_by_title", "get_compression_lineage",
         "resolve_resume_session_id", "get_active_message_ids", "get_messages")
MAX_READ_EVENTS = 10000


def require(ok):
    if not ok:
        raise RuntimeError("native_media_writer_sample_refused")


class OwnedWriter:
    """One abortable gate, one retained thread and at most one native borrow.

    A job's return means its own commit/fact assertions succeeded, not that this
    class invents transaction authority. Release requires an exact True witness
    and is attempted once, never replayed after an exception. Caller must settle
    before restoring hooks or closing DBs.
    """

    def __init__(self, owners, acquire, release, job):
        import contextvars
        import threading

        require(type(owners) is list and all(callable(value) for value in (acquire, release, job)))
        self.acquire, self.release, self.job = acquire, release, job
        self.ready, self.go, self.done = (threading.Event() for _ in range(3))
        self.abort_event = threading.Event()
        self.start_attempted = self.started = self.fired = self.joined = False
        self.acquire_attempted = self.acquire_known = self.release_attempted = False
        self.release_known = self.committed = False
        self.handle = None
        self.error = None
        self.sealed = False
        self.context = contextvars.copy_context()
        self.thread = threading.Thread(target=self.context.run, args=(self._run,),
                                       name="synthetic-c6b-writer", daemon=False)
        owners.append(self)  # Own the actual Thread BEFORE start can create an OS actor.

    def start(self):
        require(not self.start_attempted and not self.sealed)
        self.start_attempted = True
        try:
            self.thread.start()
            self.started = True
            self.ready.wait()  # Scheduling evidence, never a sleep or a successful timeout.
        except BaseException as exc:
            self.error = exc
            self.abort_event.set()
            self.go.set()
            raise

    def _run(self):
        self.ready.set()
        self.go.wait()
        try:
            if self.abort_event.is_set():
                return
            self.acquire_attempted = True
            self.handle = self.acquire()
            require(self.handle is not None)
            self.acquire_known = True
            self.job(self.handle)
            self.committed = True
        except BaseException as exc:
            self.error = exc
        finally:
            if self.acquire_known:
                self.release_attempted = True
                try:
                    require(self.release(self.handle) is True)
                    self.release_known = True
                    self.handle = None
                except BaseException as exc:
                    self.error = exc
            self.done.set()

    def fire(self):
        require(self.started and self.ready.is_set() and not self.fired and not self.sealed and
                not self.abort_event.is_set())
        self.fired = True
        self.go.set()
        self.done.wait()  # Parent's unchanged observation budget handles an overdue experiment.
        require(self.error is None and self.committed and self.release_known)

    def settle(self):
        """Seal against future admission and join the SAME actual actor, even after failure."""
        self.sealed = True
        self.abort_event.set()
        self.go.set()
        if not self.start_attempted:
            self.joined = True  # No start effects were attempted; sealed against any later start.
        elif self.started or self.thread.ident is not None:
            self.thread.join()
            self.joined = not self.thread.is_alive() and self.done.is_set()
        # An attempted start with no observable actor is UNKNOWN, not proof it never started.
        return self.safe_to_close()

    def safe_to_close(self):
        return (self.sealed and self.joined and
                (not self.acquire_attempted or (self.acquire_known and self.release_known)))


class ReadHooks:
    """Genuine native reads with metadata-only before/after scheduling seams.

    Only the reader thread fires seams. A writer's verification reads cannot
    recursively trigger itself. Exact original instance attributes are retained
    BEFORE replacement, and restored only after all supplied actors are safe.
    """

    def __init__(self, db, owners, callback):
        import threading

        require(type(owners) is list and callable(callback))
        self.db, self.owners, self.callback = db, owners, callback
        self.reader = threading.get_ident()
        self.originals, self.counts, self.events = {}, {}, []
        self.installed = []
        self.restored = False
        self.entered = False

    def install(self):
        import threading

        require(not self.entered and not self.restored)
        self.entered = True
        for name in READS:
            original = getattr(self.db, name)
            require(callable(original))
            self.originals[name] = (name in vars(self.db), vars(self.db).get(name), original)
        for name in READS:
            original = self.originals[name][2]

            def wrapped(*args, _name=name, _original=original, **kwargs):
                if threading.get_ident() != self.reader:
                    return _original(*args, **kwargs)
                count = self.counts.get(_name, 0) + 1
                self.counts[_name] = count
                self._event("before", _name, count)
                result = _original(*args, **kwargs)
                self._event("after", _name, count)
                return result

            self.installed.append(name)  # Retain restoration debt before assignment effects.
            setattr(self.db, name, wrapped)

    def _event(self, phase, name, count):
        require(len(self.events) < MAX_READ_EVENTS)
        event = (phase, name, count)
        self.events.append(event)  # Never arguments, returned rows, IDs, content or paths.
        self.callback(event)

    def restore(self):
        require(not self.restored and all(type(owner) is OwnedWriter and owner.safe_to_close()
                                         for owner in self.owners))
        for name in reversed(self.installed):
            present, value, _ = self.originals[name]
            if present:
                setattr(self.db, name, value)
            elif name in vars(self.db):
                delattr(self.db, name)
        self.installed.clear()
        self.restored = True


SEAMS = {"ids0": ("after", "get_active_message_ids", 1),
         "page": ("before", "get_messages", 1),
         "ids1": ("before", "get_active_message_ids", 2)}
GENERAL = ("control", "append", "deactivate", "eligibility", "tip_move", "aba",
           "branch_child", "reset_child")
BOT_ONLY = ("ambiguous", "kind_swap", "title_guard", "archive")


def validate_request(case, selector, request):
    if request is None:
        return
    require(type(case) is int and 0 <= case < 8 and type(selector) is int and
            selector in (1, 16, 128) and type(request) is str)
    allowed = [f"{scenario}:{seam}" for scenario in GENERAL for seam in SEAMS]
    allowed += ["residual:last", "aba:last"]
    if case < 4:
        allowed += [f"{scenario}:{seam}" for scenario in BOT_ONLY for seam in SEAMS]
    require(request in allowed)


def declared_requests(case):
    """Closed full request inventory; no filesystem, native calls or actor admission."""
    require(type(case) is int and 0 <= case < 8)
    requests = tuple(f"{scenario}:{seam}" for scenario in GENERAL for seam in SEAMS)
    requests += ("residual:last", "aba:last")
    if case < 4:
        requests += tuple(f"{scenario}:{seam}" for scenario in BOT_ONLY for seam in SEAMS)
    require(len(requests) == len(set(requests)))
    return requests


def paired_plan():
    """Plan every declared phase once, two fresh DB scopes per future process.

    This only plans. It never reuses a mutated DB, launches a process, increases
    its deadline, or declares the paired fixture implemented/qualified.
    """
    plan = []
    for case in range(8):
        requests = declared_requests(case)
        require(len(requests) % 2 == 0)
        for selector in (1, 16, 128):
            for start in range(0, len(requests), 2):
                pair = requests[start:start + 2]
                for request in pair:
                    validate_request(case, selector, request)
                plan.append((case, selector, pair))
    return tuple(plan)


def barrier(owners, hooks):
    return (type(owners) is list and type(hooks) is list and
            all(type(owner) is OwnedWriter and owner.safe_to_close() for owner in owners) and
            all(type(hook) is ReadHooks and hook.restored for hook in hooks))


def expected_outcomes(scenario, kind, selected):
    require(scenario in (*GENERAL, *BOT_ONLY, "residual") and kind in ("bot_chat", "phone") and
            type(selected) is tuple and len(selected) in (1, 16, 128) and
            all(type(value) is int and value > 0 for value in selected) and
            tuple(sorted(set(selected), reverse=True)) == selected)
    if scenario in BOT_ONLY:
        require(kind == "bot_chat")
    ok = ("ok", kind, selected)
    def closed(reason):
        return (reason, None, ())
    if scenario in ("control", "aba", "title_guard", "branch_child", "reset_child"):
        return ok, ok
    if scenario == "append":
        return closed("rows_changed"), ok
    if scenario == "deactivate":
        return closed("rows_changed"), ("ok", kind, selected[1:])
    if scenario in ("eligibility", "ambiguous", "archive"):
        return closed("tip_changed"), closed("not_eligible")
    if scenario == "tip_move":
        return closed("tip_changed"), closed("provenance_mismatch")
    if scenario == "kind_swap":
        return closed("tip_changed"), ("ok", "phone", selected)
    return ok, closed("not_eligible")  # residual, after the last genuine native read


def construct_isolated_child(handle, tip, scenario):
    """Public-API synthetic child facts, NOT gateway branch/reset admission or routing."""
    require(scenario in ("branch_child", "reset_child"))
    child = "synthetic-c6b-writer-" + scenario
    marker = "_branched_from" if scenario == "branch_child" else "_reset_from"
    require(handle.get_session(child) is None)
    require(handle.create_session(child, "api_server", parent_session_id=tip,
                                  model_config={marker: tip}) == child)
    row = handle.get_session(child)
    require(type(row) is dict and row.get("id") == child and
            row.get("parent_session_id") == tip)
    config = row.get("model_config")
    if type(config) is str:
        import json
        config = json.loads(config)
    require(type(config) is dict and config.get(marker) == tip)
    message = handle.append_message(child, "user", content="SYNTHETIC_ISOLATED_CHILD_ONLY")
    require(type(message) is int and message > 0 and
            message in handle.get_active_message_ids(child) and
            handle.resolve_resume_session_id(tip) == tip)
    return 2


def _checked_outcome(value, reference, candidate, expected):
    reason, kind, selected = expected
    require(type(value) is type(reference) and value.sidecar is candidate and
            value.reason == reason and value.accepted == selected and
            (value.kind is None if kind is None else value.kind is not None and
             value.kind.value == kind))
    return {"reason": reason, "kind": kind, "accepted_count": len(selected),
            "selection_verified": True}


def run_scenario(fx, db, candidate, reference, selected, shape, extra, *,
                 case, request, user, profile, chat, owners, hooks,
                 acquire_native, release_native):
    """One genuine native/synthetic-store writer phase on an already verified scratch shape."""
    validate_request(case, len(selected), request)
    require(request is not None)
    scenario, seam = request.split(":")
    kind, root, tip = shape["kind"], shape["root"], shape["tip"]
    require(kind == ("bot_chat" if case < 4 else "phone") and
            candidate.user_id == user and candidate.profile == profile and
            candidate.session_id == root and candidate.query_tip == tip and
            candidate.provenance_consistent is True and reference.sidecar is candidate and
            reference.ok and reference.accepted == selected and reference.kind is not None and
            reference.kind.value == kind and callable(acquire_native) and callable(release_native))
    oracle = expected_outcomes(scenario, kind, selected)
    bind = fx.native.bridge.bind_media_batch
    unchanged = ("ok", kind, selected)
    discovery = ReadHooks(db, owners, lambda _: None)
    hooks.append(discovery)  # Retain partial instrumentation before assignment effects.
    try:
        discovery.install()
        _checked_outcome(bind(candidate), reference, candidate, unchanged)
        after = [event for event in discovery.events if event[0] == "after"]
        require(after)
        target = after[-1] if seam == "last" else SEAMS[seam]
        require(discovery.events.count(target) == 1)
    finally:
        discovery.restore()

    facts = {"native_mutations_verified": 0, "synthetic_store_calls": 0,
             "native_guard_refused": False}

    def own_is(sid):
        value = fx.native.bridge.conversation_ref(user, profile)
        require(value is not None and value.user_id == user and value.profile == profile and
                value.session_id == sid)

    def phone_to(sid):
        before = fx.native.bridge.conversation_ref(user, profile)
        require(before is not None and before.session_id != sid)
        fx.native.world.start_conversation(profile, chat, sid)
        own_is(sid)
        facts["synthetic_store_calls"] += 1

    def hidden(handle, value):
        require(handle.set_session_hidden(root, value) is True)
        require(handle.get_session(root)["hidden"] == int(value))
        facts["native_mutations_verified"] += 1

    def lose(handle):
        if kind == "bot_chat":
            hidden(handle, False)
        else:
            require(handle.get_session(extra) is not None)
            phone_to(extra)

    def job(handle):
        require(handle is db)
        if scenario == "control":
            before = handle.get_session(root).get("last_read_at")
            require(handle.set_session_read(root, True) is True)
            after = handle.get_session(root)["last_read_at"]
            require(after > 0 and after != before)
            facts["native_mutations_verified"] += 1
        elif scenario == "append":
            before = set(handle.get_active_message_ids(tip))
            row = handle.append_message(tip, "user", content="SYNTHETIC_NATIVE_WRITER_ONLY")
            require(type(row) is int and row > 0 and row not in before and
                    row in handle.get_active_message_ids(tip))
            facts["native_mutations_verified"] += 1
        elif scenario == "deactivate":
            changed = handle.deactivate_message(tip, selected[0])
            require(type(changed) is int and changed == 1 and
                    selected[0] not in handle.get_active_message_ids(tip))
            facts["native_mutations_verified"] += 1
        elif scenario in ("eligibility", "residual", "aba"):
            lose(handle)
            if scenario == "aba":
                if kind == "bot_chat":
                    hidden(handle, True)
                else:
                    phone_to(root)
        elif scenario in ("branch_child", "reset_child"):
            facts["native_mutations_verified"] += construct_isolated_child(handle, tip, scenario)
        elif scenario == "tip_move":
            child = "synthetic-c6b-writer-compression-child"
            require(handle.get_session(child) is None)
            handle.end_session(tip, "compression")
            require(handle.create_session(child, "api_server", parent_session_id=tip) == child and
                    handle.resolve_resume_session_id(root) == child)
            facts["native_mutations_verified"] += 2
        elif scenario == "archive":
            require(handle.set_session_archived(root, True, notify=False) is True and
                    handle.get_session(root)["archived"] == 1)
            facts["native_mutations_verified"] += 1
        elif scenario == "ambiguous":
            phone_to(root)
        elif scenario == "kind_swap":
            hidden(handle, False)
            phone_to(root)
        else:
            require(scenario == "title_guard")
            try:
                handle.set_session_title(tip, "")
            except ValueError:
                facts["native_guard_refused"] = True
            require(facts["native_guard_refused"] and
                    handle.get_session_by_title("Bot Chat")["id"] == tip and
                    handle.get_session(root)["hidden"] == 1)

    path = fx.native.home_path / "state.db"

    # Explicit fixture ports: acquire checks selected path/object; release checks
    # actual registry True + tracked debt and returns an exact True witness.
    writer = OwnedWriter(owners, lambda: acquire_native(path), release_native, job)

    def trigger(event):
        if event == target:
            writer.fire()

    phase = ReadHooks(db, owners, trigger)
    hooks.append(phase)
    try:
        phase.install()
        writer.start()
        first = bind(candidate)
        require(writer.fired and writer.committed and writer.error is None and writer.release_known)
        first_summary = _checked_outcome(first, reference, candidate, oracle[0])
    finally:
        safe = writer.settle()
        if safe:
            phase.restore()
        require(safe)
    second = bind(candidate)
    second_summary = _checked_outcome(second, reference, candidate, oracle[1])
    require(barrier(owners, hooks) and phase.events.count(target) == 1)
    return {"case": case, "request": request, "kind": kind, "selector": len(selected),
            "first": first_summary, "second": second_summary, **facts,
            "job_verified": writer.committed, "writer_joined": writer.joined,
            "release_verified": writer.release_known, "hooks_restored": True,
            "read_events": len(phase.events), "trigger": list(target),
            "residual_acceptance": scenario == "residual", "aba_acceptance": scenario == "aba"}


def validate_report(report, case, selector, request):
    validate_request(case, selector, request)
    require(request is not None and type(report) is dict and set(report) == {
        "case", "request", "kind", "selector", "first", "second", "native_mutations_verified",
        "synthetic_store_calls", "native_guard_refused", "job_verified", "writer_joined",
        "release_verified", "hooks_restored", "read_events", "trigger", "residual_acceptance",
        "aba_acceptance"})
    kind = "bot_chat" if case < 4 else "phone"
    scenario, seam = request.split(":")
    require(type(report["case"]) is int and report["case"] == case and
            type(report["selector"]) is int and report["selector"] == selector and
            report["kind"] == kind and report["request"] == request and
            all(report[key] is True for key in ("job_verified", "writer_joined",
                "release_verified", "hooks_restored")) and
            report["residual_acceptance"] is (scenario == "residual") and
            report["aba_acceptance"] is (scenario == "aba") and
            type(report["read_events"]) is int and 1 <= report["read_events"] <= MAX_READ_EVENTS)
    expected = expected_outcomes(scenario, kind, tuple(range(selector, 0, -1)))
    for key, (reason, expected_kind, ids) in zip(("first", "second"), expected, strict=True):
        value = report[key]
        require(type(value) is dict and set(value) == {"reason", "kind", "accepted_count",
                "selection_verified"} and value["reason"] == reason and
                value["kind"] == expected_kind
                and type(value["accepted_count"]) is int and value["accepted_count"] == len(ids)
                and value["selection_verified"] is True)
    trigger = report["trigger"]
    require(type(trigger) is list and len(trigger) == 3 and trigger[0] in ("before", "after") and
            trigger[1] in READS and type(trigger[2]) is int and 1 <= trigger[2] <= MAX_READ_EVENTS)
    require(trigger[0] == "after" if seam == "last" else tuple(trigger) == SEAMS[seam])
    if scenario == "title_guard":
        native, store = 0, 0
    elif scenario == "ambiguous":
        native, store = 0, 1
    elif scenario == "kind_swap":
        native, store = 1, 1
    elif scenario in ("eligibility", "residual", "aba"):
        amount = 2 if scenario == "aba" else 1
        native, store = (amount, 0) if kind == "bot_chat" else (0, amount)
    else:
        native, store = (2 if scenario in ("tip_move", "branch_child", "reset_child") else 1), 0
    require(type(report["native_mutations_verified"]) is int and
            report["native_mutations_verified"] == native and
            type(report["synthetic_store_calls"]) is int and
            report["synthetic_store_calls"] == store
            and report["native_guard_refused"] is (scenario == "title_guard"))
