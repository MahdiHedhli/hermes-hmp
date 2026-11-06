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
        self.thread = threading.Thread(target=self._run, name="synthetic-c6b-writer", daemon=False)
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
