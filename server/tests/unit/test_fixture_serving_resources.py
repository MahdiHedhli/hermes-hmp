"""Fixture-only resource ownership with inert filesystem/scheduler objects."""

import contextlib
import stat
import sys
import unittest
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from types import FunctionType, ModuleType, SimpleNamespace

from . import test_fixture_work as work_models

CAUSALS = []


def _load_cli_subject():
    path = Path(__file__).resolve().parents[2] / "hmp_plugin/cli.py"
    # Dataclasses inspect cls.__module__ on Python 3.11. Use this actual collected
    # test module's existing identity, with isolated declaration globals; never
    # install a synthetic module in sys.modules or mutate the production CLI.
    module = ModuleType(__name__)
    namespace = vars(module)
    namespace.update(__file__=str(path), __package__="hmp_plugin")
    FunctionType(compile(path.read_bytes(), str(path), "exec"), namespace)()
    return module


class InertFiles:
    O_RDONLY = 0
    O_WRONLY = 1
    O_CREAT = 2
    O_EXCL = 4
    O_NOFOLLOW = 8
    O_DIRECTORY = 16

    def __init__(self):
        self.parent_inode = 1
        self.parent_name_inode = 1
        self.next_inode = 10
        self.next_fd = 100
        self.files = {}
        self.fds = {}
        self.offsets = {}
        self.effects = []
        self.hooks = {}
        self.closed = []
        self.token = 0

    def effect(self, stage):
        self.effects.append(stage)
        callback = self.hooks.get(stage)
        if callback is not None:
            callback()

    def token_hex(self, size):
        self.token += 1
        return f"{self.token:0{size * 2}x}"

    def getpid(self):
        return 99

    def getuid(self):
        return 501

    def info(self, inode, directory=False):
        return SimpleNamespace(
            st_dev=4,
            st_ino=inode,
            st_uid=501,
            st_mode=(stat.S_IFDIR | 0o700) if directory else (stat.S_IFREG | 0o600),
        )

    def open(self, name, flags, mode=None, *, dir_fd=None):
        del mode
        stage = (
            "parent_open"
            if flags & self.O_DIRECTORY
            else ("temp_open" if flags & self.O_CREAT else "read_open")
        )
        self.effect(stage + "_before")
        if flags & self.O_DIRECTORY:
            node = {"inode": self.parent_inode, "directory": True}
        elif flags & self.O_CREAT:
            assert dir_fd in self.fds and name not in self.files
            node = {"inode": self.next_inode, "body": b""}
            self.next_inode += 1
            self.files[name] = node
        else:
            assert dir_fd in self.fds
            node = self.files[name]
        fd = self.next_fd
        self.next_fd += 1
        self.fds[fd] = node
        self.offsets[fd] = 0
        self.effect(stage + "_after")
        return fd

    def fstat(self, fd):
        self.effect("fstat")
        node = self.fds[fd]
        return self.info(node["inode"], node.get("directory", False))

    def lstat(self, path):
        del path
        self.effect("parent_lstat")
        return self.info(self.parent_name_inode, True)

    def stat(self, name, *, dir_fd, follow_symlinks):
        assert dir_fd in self.fds and follow_symlinks is False
        self.effect("named_stat")
        if name not in self.files:
            raise FileNotFoundError
        return self.info(self.files[name]["inode"])

    def fchmod(self, fd, mode):
        assert fd in self.fds and mode == 0o600
        self.effect("fchmod")

    def write(self, fd, body):
        self.effect("write_before")
        self.fds[fd]["body"] += body
        self.effect("write_after")
        return len(body)

    def fsync(self, fd):
        assert fd in self.fds
        self.effect("fsync")

    def close(self, fd):
        assert fd in self.fds and fd not in self.closed
        self.effect("close_before")
        self.closed.append(fd)
        self.effect("close_after")

    def replace(self, old, new, *, src_dir_fd, dst_dir_fd):
        assert src_dir_fd == dst_dir_fd and src_dir_fd in self.fds
        self.effect("replace_before")
        self.files[new] = self.files.pop(old)
        self.effect("replace_after")

    def read(self, fd, limit):
        self.effect("read")
        offset = self.offsets[fd]
        body = self.fds[fd]["body"][offset : offset + limit]
        self.offsets[fd] += len(body)
        return body

    def unlink(self, name, *, dir_fd):
        assert dir_fd in self.fds
        self.effect("unlink_before")
        self.files.pop(name)
        self.effect("unlink_after")


class ServingResourceTests(unittest.TestCase):
    def setUp(self):
        self.harness = work_models.WorkTests(
            "test_real_default_refuses_before_mutex_or_context_access"
        )
        self.harness.setUp()
        self.cli = _load_cli_subject()

    def tearDown(self):
        self.harness.tearDown()

    def test_cli_loader_preserves_dataclass_and_existing_module_identity(self):
        registered = sys.modules[__name__]
        old_synthetic = sys.modules.get("hmp_plugin._fixture_cli_test_subject")
        module = _load_cli_subject()
        self.assertIs(sys.modules[__name__], registered)
        self.assertIs(sys.modules.get("hmp_plugin._fixture_cli_test_subject"), old_synthetic)
        self.assertIsNot(module, registered)
        self.assertEqual(module.ListenerRecord.__module__, __name__)
        self.assertEqual(tuple(item.name for item in fields(module.ListenerRecord)), (
            "host", "port", "iid", "pid", "nonce", "profiles", "health_checked_at", "health",
        ))
        record = module.ListenerRecord("localhost", 8210, "iid", 1, "nonce")
        self.assertIsNone(record.profiles)
        with self.assertRaises(FrozenInstanceError):
            record.host = "changed"
        CAUSALS.append("full actual CLI loader preserves frozen dataclass without module injection")

    def world(self):
        work, loop, _worker, _task = self.harness.scenario()
        module = self.harness.module
        ctx = SimpleNamespace(
            iid="iid",
            identity=SimpleNamespace(
                custody=SimpleNamespace(anchor_dir=Path("/fixture/hmp/identity"))
            ),
        )
        ctx._fixture_work = work
        ctx._fixture_adapter = work.adapter
        work.context = work.lifecycle.ctx = ctx
        work._carriers = (ctx, work.adapter)
        work._component_bind_complete = True
        scope = module._ServingResources(work)
        work.lifecycle.resources = scope
        scope.server = SimpleNamespace(bound=("127.0.0.1", 8210))

        def stop(error):
            work.lifecycle.stopping = True
            work.lifecycle.first_failure = error

        work.lifecycle.request_stop = stop
        frame = module._WorkRecord(work, module._WorkSite.CW002, "task", None)
        frame.body_entered = True
        work._records.append(frame)
        module._CURRENT_FRAME.set(frame)
        self.cli._ServingResources = module._ServingResources
        self.cli._WorkRefusedError = module._WorkRefusedError
        self.cli._publication = module._publication
        self.cli._require_fixture_resource_policy = lambda lifecycle: None
        fs = InertFiles()
        self.cli.os = fs
        self.cli.secrets = SimpleNamespace(token_hex=fs.token_hex)
        path = self.cli.listener_record_path(ctx.identity.custody.anchor_dir)
        owner = self.cli._ListenerRecordOwner(scope, path, "a" * 32)
        return owner, scope, loop, fs

    def write(self, owner):
        return self.cli.write_listener_record(
            owner.path,
            host="127.0.0.1",
            port=8210,
            iid=owner.iid,
            nonce=owner.nonce,
            profiles=[("profile", "Profile")],
            _fixture_owner=owner,
        )

    def test_known_publication_refresh_and_removal_close_each_fd_once(self):
        owner, scope, _loop, fs = self.world()
        self.write(owner)
        first = owner.published.inode
        self.write(owner)
        assert owner.published.inode != first
        scope.work.request_stop(RuntimeError("stop"))
        self.cli.remove_listener_record(owner.path, _fixture_owner=owner)
        assert owner.removed and not fs.files and len(fs.closed) == len(set(fs.closed))
        assert all(a.close_returned for a in owner.attempts if a.fd is not None)
        assert owner.parent.close_returned
        CAUSALS.append("known publication refresh/remove with one-use FD close")

    def test_direct_owner_body_type_bound_and_generation_fields_precede_effects(self):
        for body in (b"x" * (self.cli.MAX_RECORD_BYTES + 1), bytearray(b"{}"), b"{}"):
            owner, _scope, _loop, fs = self.world()
            with self.assertRaises(self.harness.module._WorkRefusedError):
                owner.write(owner.path, body, owner.nonce, owner.iid)
            assert fs.effects == [] and owner.first_failure is not None
            CAUSALS.append("direct write type/size/full-scope refusal before filesystem")

    def test_acquisition_and_write_failures_retain_actual_attempts(self):
        stages = (
            "parent_open_before",
            "parent_open_after",
            "temp_open_before",
            "temp_open_after",
            "fchmod",
            "write_before",
            "write_after",
            "fsync",
            "close_before",
            "close_after",
            "replace_before",
            "replace_after",
        )
        for stage in stages:
            owner, _scope, _loop, fs = self.world()
            error = RuntimeError(stage)

            def fail(error=error):
                raise error

            fs.hooks[stage] = fail
            with self.assertRaises(RuntimeError):
                self.write(owner)
            assert owner.first_failure is error and owner.unknown
            if stage.startswith("parent_open"):
                assert owner.parent.open_attempted and owner.parent.open_unknown
            else:
                attempt = owner.attempts[0]
                assert attempt.open_attempted
                if stage.startswith("temp_open"):
                    assert attempt.open_unknown
                elif stage == "fchmod":
                    assert attempt.fchmod_attempted and not attempt.fchmod_returned
                elif stage.startswith("write"):
                    assert attempt.write_attempts == [(0, len(fs.fds[attempt.fd]["body"]))] or (
                        attempt.write_attempts[0][0] == 0 and not attempt.write_returns
                    )
                elif stage == "fsync":
                    assert attempt.fsync_attempted and not attempt.fsync_returned
                elif stage.startswith("close"):
                    assert attempt.close_attempted and not attempt.close_returned
                elif stage.startswith("replace"):
                    assert attempt.rename_attempted and not attempt.rename_returned
                    assert owner.published is None
            assert len(fs.closed) == len(set(fs.closed))
            CAUSALS.append("retained source filesystem failure " + stage)

    def test_stop_and_caught_write_reentry_prevent_later_rename(self):
        for action in ("stop", "reentry"):
            owner, scope, _loop, fs = self.world()

            def hook(action=action, owner=owner, scope=scope):
                if action == "stop":
                    scope.work.request_stop(RuntimeError("stop in fsync"))
                else:
                    with contextlib.suppress(self.harness.module._WorkRefusedError):
                        self.write(owner)

            fs.hooks["fsync"] = hook
            with self.assertRaises(self.harness.module._WorkRefusedError):
                self.write(owner)
            assert "replace_before" not in fs.effects
            assert owner.published is None and owner.unknown
            CAUSALS.append("write callback " + action + " has zero later rename")

    def test_replaced_inode_nonce_parent_refuse_removal_before_unlink(self):
        for change in ("inode", "nonce", "parent"):
            owner, scope, _loop, fs = self.world()
            self.write(owner)
            if change == "inode":
                fs.files[owner.path.name] = {"inode": 900, "body": b"{}"}
            elif change == "nonce":
                fs.files[owner.path.name]["body"] = fs.files[owner.path.name]["body"].replace(
                    b"a" * 32, b"b" * 32
                )
            else:
                fs.parent_name_inode = 900
            scope.work.request_stop(RuntimeError("stop"))
            with self.assertRaises(self.harness.module._WorkRefusedError):
                owner.remove(owner.path)
            assert "unlink_before" not in fs.effects and not owner.removed
            assert owner.parent.close_attempted and owner.parent.close_returned
            CAUSALS.append("remove replacement " + change + " has zero unlink")

    def test_unlink_and_parent_close_keep_both_failures_no_retry(self):
        owner, scope, _loop, fs = self.world()
        self.write(owner)
        scope.work.request_stop(RuntimeError("stop"))
        unlink_error, close_error = RuntimeError("unlink"), RuntimeError("close")

        def fail_unlink():
            def fail_close():
                raise close_error

            fs.hooks["close_before"] = fail_close
            raise unlink_error

        fs.hooks["unlink_before"] = fail_unlink
        with self.assertRaises(RuntimeError) as caught:
            owner.remove(owner.path)
        assert caught.exception is unlink_error
        assert owner.remove_failure is unlink_error
        assert owner.parent.cleanup_failures == [close_error]
        before = list(fs.effects)
        with self.assertRaises(self.harness.module._WorkRefusedError):
            owner.remove(owner.path)
        assert fs.effects == before and not owner.removed
        CAUSALS.append("unlink original + failed parent close retained; repeat has zero effects")

    def server_world(self):
        _owner, scope, loop, _fs = self.world()
        work = scope.work
        effects = []

        class Deadline:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

        class BaseSite:
            @staticmethod
            async def stop(site):
                del site
                effects.append("deregister")

        self.harness.module.asyncio.timeout = lambda seconds: Deadline()
        selected = self.harness.selected(
            "server",
            {
                "_FixtureSockSite": (
                    "close_owned",
                    "stop",
                    "_close_source_owned",
                    "_stop_source_owned",
                    "_wait_source_closed",
                ),
                "HmpServer": ("_close_owned_fixture_socket", "_stop_owned_fixture"),
            },
            {"web": SimpleNamespace(BaseSite=BaseSite), "SHUTDOWN_TIMEOUT_S": 5.0},
        )
        server = selected.HmpServer.__new__(selected.HmpServer)
        server._starting = False
        server._fixture_used = True
        scope.server = server
        site = selected._FixtureSockSite.__new__(selected._FixtureSockSite)
        site._fixture_resources = scope
        site._fixture_close_started = site._fixture_closed = False
        acknowledgement = work_models.ModelFuture(loop)
        request_ack = work_models.ModelFuture(loop)

        class Transport:
            def close(self):
                effects.append("acceptor_close")

            async def wait_closed(self):
                effects.append("wait_closed")
                await acknowledgement
                effects.append("client_acknowledged")

        class Runner:
            async def cleanup(self):
                effects.append("request_shutdown")
                await request_ack
                effects.append("request_acknowledged")
                acknowledgement.set_result(None)

        for name, kind, value in (("site", "LISTENER", site), ("runner", "RUNNER", Runner())):
            record = scope.attempt(getattr(self.harness.module._ResourceSite, kind), server)
            scope.returned(record, value)
            setattr(scope, name, record)
        scope.site.transferred = True
        scope.site.transfer_target = site._server = Transport()
        # The synthetic startup frame has actually exited before stop is called.
        frame = self.harness.module._CURRENT_FRAME.get()
        frame.body_exited = frame.collected = True
        return work, loop, scope, server, site, effects, request_ack

    def test_actual_server_drain_orders_request_shutdown_before_client_wait(self):
        _work, loop, scope, server, site, effects, request_ack = self.server_world()

        async def prior_order():
            await site.stop()
            await site._wait_source_closed(scope)
            await scope.runner.object.cleanup()

        prior = loop.start_caller(prior_order())
        loop.run()
        assert not prior.done() and effects == ["acceptor_close", "deregister", "wait_closed"]
        assert not scope.runner.close_attempted and not scope.site.wait_returned
        CAUSALS.append("prior draft ordering blocks on held client before request shutdown")
        # Separate world: the source correction must make progress through request cleanup.
        _work, loop, scope, server, _site, effects, request_ack = self.server_world()
        task = loop.start_caller(server._stop_owned_fixture(scope))
        loop.run()
        assert not task.done() and not scope.stop_returned
        assert effects == ["acceptor_close", "deregister", "request_shutdown"]
        request_ack.set_result(None)
        loop.run()
        assert task.done() and task.error is None and scope.stop_returned
        assert effects == [
            "acceptor_close",
            "deregister",
            "request_shutdown",
            "request_acknowledged",
            "wait_closed",
            "client_acknowledged",
        ]
        assert scope.site.wait_returned and scope.runner.close_returned
        again = loop.start_caller(server._stop_owned_fixture(scope))
        loop.run()
        assert again.error is not None and effects.count("acceptor_close") == 1
        CAUSALS.append("corrected actual drain waits for request and client acknowledgements once")

    def test_actual_wait_closed_deadline_retains_object_and_debt(self):
        _work, loop, scope, _server, site, effects, _request_ack = self.server_world()
        stop = loop.start_caller(site.stop())
        loop.run()
        assert stop.error is None
        waiter = loop.start_caller(site._wait_source_closed(scope))
        loop.run()
        assert not waiter.done()
        failure = TimeoutError("inert deadline")
        waiter.step(error=failure)
        assert waiter.error is failure and scope.site.unknown
        assert scope.site.close_failure is failure and not scope.site.wait_returned
        retained = scope.site.transfer_target
        retry = loop.start_caller(site._wait_source_closed(scope))
        loop.run()
        assert retry.error is not None and scope.site.transfer_target is retained
        assert effects.count("wait_closed") == 1 and effects.count("acceptor_close") == 1
        assert not scope.stop_returned
        CAUSALS.append(
            "actual wait_closed timeout retains actual server and prevents replay/closure"
        )

    def test_unknown_site_acquisition_never_guesses_raw_close(self):
        _work, loop, scope, server, _site, effects, request_ack = self.server_world()
        original = RuntimeError("constructor transferred before throwing")
        scope.site.unknown = True
        scope.site.failure = original
        request_ack.set_result(None)
        task = loop.start_caller(server._stop_owned_fixture(scope))
        loop.run()
        assert task.error is not None and not scope.stop_returned
        assert "acceptor_close" not in effects and "wait_closed" not in effects
        assert scope.site.failure is original and scope.site.transfer_target is not None
        CAUSALS.append("unknown site acquisition retains custody and refuses guessed raw close")

    def test_actual_wait_users_observes_retained_writer_and_http_ack(self):
        for name in ("OPERATOR_WRITER", "HTTP_TRANSPORT"):
            with self.subTest(name=name):
                _owner, scope, loop, _fs = self.world()
                frame = self.harness.module._CURRENT_FRAME.get()
                frame.body_exited = frame.collected = True
                record = scope.attempt(
                    getattr(self.harness.module._ResourceSite, name), scope.server
                )
                scope.returned(record, object())
                task = loop.start_caller(scope.wait_users())
                loop.run()
                assert not task.done() and not scope.context_close_started
                record.close_returned = True
                scope.notify()
                loop.run()
                assert not task.done()  # close return is not actual transport acknowledgement.
                record.wait_returned = True
                scope.notify()
                loop.run()
                assert task.done() and task.error is None
                assert not scope.context_close_started  # wait_users cannot authorize context close.
                CAUSALS.append(f"actual retained {name} blocks users drain until acknowledgement")

    def test_actual_resource_post_return_stop_retains_object(self):
        _owner, scope, _loop, _fs = self.world()
        work = scope.work
        record = scope.attempt(self.harness.module._ResourceSite.EXECUTOR, scope.server)
        actual = object()
        reason = RuntimeError("inert constructor stopped owner")
        work.request_stop(reason)
        with self.assertRaises(self.harness.module._WorkRefusedError):
            scope.returned(record, actual)
        assert record.acquired and record.object is actual and not record.close_attempted
        with self.assertRaises(self.harness.module._WorkRefusedError):
            scope.attempt(self.harness.module._ResourceSite.MEDIA, scope.server)
        assert work.first_failure is reason
        CAUSALS.append(
            "actual post-acquisition stop retains object before refusal; no next acquisition"
        )

    def operator_world(self):
        _publication, scope, loop, _fs = self.world()
        work = scope.work
        effects, hooks = [], {}
        directory = SimpleNamespace(st_dev=4, st_ino=1, st_uid=501, st_mode=stat.S_IFDIR | 0o700)
        entry = SimpleNamespace(st_dev=4, st_ino=22, st_uid=501, st_mode=stat.S_IFSOCK | 0o600)
        state = SimpleNamespace(bound=False, inode=entry, fd=20, closed=[])
        service = SimpleNamespace(
            ctx=work.context,
            path=Path("/fixture/operator.sock"),
            nonce="a" * 32,
            _fixture_resource=None,
            _stopping=False,
            _handle=object(),
        )
        record = scope.attempt(self.harness.module._ResourceSite.OPERATOR, scope.server)
        scope.returned(record, service)
        scope.operator = record

        def effect(name):
            effects.append(name)
            if name in hooks:
                hooks[name]()

        def open_directory(*args, **kwargs):
            del args, kwargs
            effect("directory_open")
            state.fd += 1
            return state.fd

        def close_directory(fd):
            assert fd not in state.closed
            state.closed.append(fd)
            effect("directory_close")

        def socket_entry(_fd):
            if not state.bound:
                raise FileNotFoundError
            return state.inode

        def unlink(name, *, dir_fd):
            assert name == "operator.sock" and dir_fd == owner.parent
            effect("unlink")
            state.bound = False

        def umask(value):
            effect("umask_install" if value == 0o077 else "umask_restore")
            return 0o022

        class Raw:
            def bind(self, path):
                assert path == str(service.path)
                state.bound = True
                effect("bind")

            def listen(self, count):
                assert count == 2
                effect("listen")

            def setblocking(self, value):
                assert value is False
                effect("nonblocking")

            def close(self):
                effect("raw_close")

        class Acceptor:
            def close(self):
                effect("acceptor_close")

            async def wait_closed(self):
                effect("acceptor_wait")

        class Deadline:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

        raw, acceptor = Raw(), Acceptor()

        def socket_factory(family, kind):
            assert family == "unix" and kind == "stream"
            effect("socket_factory")
            return raw

        async def start_unix(callback, *, sock, limit):
            assert callback is service._handle and sock is raw and limit == 4096
            effect("acceptor_factory")
            return acceptor

        async def wait_for(awaitable, bound):
            assert bound == 2.0
            return await awaitable

        fake_os = SimpleNamespace(
            O_RDONLY=0,
            O_DIRECTORY=1,
            O_NOFOLLOW=2,
            open=open_directory,
            close=close_directory,
            stat=lambda *args, **kwargs: directory,
            fstat=lambda fd: directory,
            lstat=lambda path: state.inode if path == service.path else directory,
            getuid=lambda: 501,
            fsencode=lambda path: str(path).encode(),
            umask=umask,
            unlink=unlink,
        )
        self.harness.module.asyncio.timeout = lambda seconds: Deadline()
        self.harness.module.asyncio.wait_for = wait_for
        self.harness.module.asyncio.start_unix_server = start_unix
        selected = self.harness.selected(
            "operator_read",
            {
                "_OperatorResourceOwner": (
                    "__init__",
                    "_check",
                    "_directory_open",
                    "_directory_close",
                    "_bound_identity",
                    "start",
                    "retain_writer",
                    "close_writer",
                    "stop",
                ),
                "_fixture_parent_fd": (),
            },
            {
                "_require_fixture_resource_policy": lambda lifecycle: None,
                "os": fake_os,
                "contextlib": contextlib,
                "stat": stat,
                "_entry": socket_entry,
                "socket": SimpleNamespace(
                    AF_UNIX="unix", SOCK_STREAM="stream", socket=socket_factory
                ),
                "_NONCE": SimpleNamespace(fullmatch=lambda value: value == "a" * 32),
                "MAX_REQUEST": 4096,
                "DEADLINE_S": 2.0,
                "SOCKET_NAME": "operator.sock",
                "OperatorUnavailableError": RuntimeError,
            },
        )
        owner = selected._OperatorResourceOwner(service, scope)
        return owner, scope, loop, effects, hooks, state

    def test_actual_operator_acquisition_and_exact_once_stop(self):
        owner, scope, loop, effects, _hooks, state = self.operator_world()
        start = loop.start_caller(owner.start())
        loop.run()
        assert start.error is None and owner.acceptor.acquired
        assert owner.bind_returned and owner.listen_returned and owner.nonblocking_returned
        assert owner.raw.transferred and owner.raw.transfer_target is owner.acceptor.object
        assert owner.umask_restored and len(owner.directories) == 2
        stop = loop.start_caller(owner.stop())
        loop.run()
        assert stop.error is None and owner.stop_returned and not state.bound
        assert effects[-4:] == ["acceptor_close", "acceptor_wait", "unlink", "directory_close"]
        assert len(state.closed) == len(set(state.closed)) == 2
        before = list(effects)
        again = loop.start_caller(owner.stop())
        loop.run()
        assert again.error is None and effects == before
        assert not scope.context_close_started
        CAUSALS.append(
            "actual operator acquisition preserves policy flags and exact one-use close/unlink"
        )

    def test_actual_operator_unknown_transfer_refuses_raw_close_and_unlink(self):
        owner, scope, loop, effects, hooks, state = self.operator_world()
        error = RuntimeError("acceptor acquired then throw")

        def fail():
            raise error

        hooks["acceptor_factory"] = fail
        start = loop.start_caller(owner.start())
        loop.run()
        assert start.error is error and owner.acceptor.unknown and owner.raw.transferred
        stop = loop.start_caller(owner.stop())
        loop.run()
        assert stop.error is not None and owner.failure is error and not owner.stop_returned
        assert "raw_close" not in effects and "unlink" not in effects and state.bound
        assert any(record.unknown for record in scope.resources)
        CAUSALS.append(
            "unknown acceptor acquisition retains endpoint custody; no raw close/unlink/replay"
        )

    def test_actual_operator_stop_and_caught_reentry_fence_next_effect(self):
        for stage, forbidden in (
            ("bind", "listen"),
            ("listen", "nonblocking"),
            ("nonblocking", "acceptor_factory"),
        ):
            owner, scope, loop, effects, hooks, _state = self.operator_world()
            failure = RuntimeError("inert operation stopped")
            hooks[stage] = lambda scope=scope, failure=failure: scope.work.request_stop(failure)
            start = loop.start_caller(owner.start())
            loop.run()
            assert start.error is not None and forbidden not in effects
            assert scope.work.first_failure is failure and owner.umask_restored
            CAUSALS.append(f"operator stop during {stage} forbids later {forbidden}")
        owner, scope, loop, effects, hooks, _state = self.operator_world()

        def nested():
            with contextlib.suppress(self.harness.module._WorkRefusedError):
                scope.attempt(self.harness.module._ResourceSite.OPERATOR_SOCKET, owner.service)

        hooks["socket_factory"] = nested
        start = loop.start_caller(owner.start())
        loop.run()
        assert start.error is not None and owner.raw.acquired
        assert "bind" not in effects and scope.work.stopping
        CAUSALS.append("caught constructor reentry retains raw socket and forbids bind")

    def test_actual_operator_writer_close_ack_and_failure_are_independent(self):
        for fail_close in (False, True):
            owner, scope, loop, _effects, _hooks, _state = self.operator_world()
            acknowledgement = work_models.ModelFuture(loop)
            calls = []
            failure = RuntimeError("writer close unknown")

            class Writer:
                def close(self, calls=calls, fail_close=fail_close, failure=failure):
                    calls.append("close")
                    if fail_close:
                        raise failure

                async def wait_closed(self, calls=calls, acknowledgement=acknowledgement):
                    calls.append("wait")
                    await acknowledgement

            record = owner.retain_writer(object(), Writer())
            close = loop.start_caller(owner.close_writer(record))
            loop.run()
            if fail_close:
                assert close.error is failure and record.close_failure is failure and record.unknown
                assert calls == ["close"] and not record.wait_returned
            else:
                assert not close.done() and record.close_returned and not record.wait_returned
                acknowledgement.set_result(None)
                loop.run()
                assert close.error is None and record.wait_returned
            again = loop.start_caller(owner.close_writer(record))
            loop.run()
            assert again.error is None and calls.count("close") == 1
            assert not scope.context_close_started
            CAUSALS.append(
                f"actual operator writer close fail={fail_close}: retained acknowledgement/debt"
            )

    def test_actual_lifecycle_context_close_follows_late_worker_and_server_ack(self):
        work, loop, scope, _server, _site, effects, request_ack = self.server_world()
        module = self.harness.module
        lifecycle = work.lifecycle
        scope.publication = None
        selected = self.harness.selected(
            "adapter",
            {
                "_FixtureLifecycle": ("_drain_serving_owned", "_cleanup_owned"),
            },
            {"server": SimpleNamespace(SHUTDOWN_TIMEOUT_S=5.0)},
        )
        from types import MethodType

        lifecycle._drain_serving_owned = MethodType(
            selected._FixtureLifecycle._drain_serving_owned, lifecycle
        )
        lifecycle.serving, lifecycle.resources = work, scope
        lifecycle.setup = None
        lifecycle.cleanup_failures = []
        lifecycle.prompt_close_attempted = lifecycle.store_close_attempted = False
        lifecycle.context_closed = lifecycle.unknown_context = False
        lifecycle.adapter._close_generation = lambda ctx: effects.append("prompt_close")
        work.context.store = SimpleNamespace(close=lambda: effects.append("store_close"))
        lifecycle.alias.state = "SERVER_OWNED"
        frame = module._CURRENT_FRAME.get()

        async def completed_start():
            return None

        frame.task = loop.start_caller(completed_start())
        scope.start = frame
        frame.body_exited = frame.collected = True
        loop.run()
        worker = work.launch_worker(
            next(iter(module._WORKER_SITES)), lambda: effects.append("late_worker_body")
        )
        loop.run()
        assert worker.worker_submitting and not worker.worker_exited
        waiter = loop.start_caller(work.collect(worker))
        loop.run()
        waiter.cancel()
        loop.run()
        assert isinstance(waiter.error, work_models.ModelCancellation)
        cleanup = loop.start_caller(selected._FixtureLifecycle._cleanup_owned(lifecycle))
        loop.run()
        assert not cleanup.done() and "store_close" not in effects
        request_ack.set_result(None)
        loop.run()
        assert scope.stop_returned and not cleanup.done() and "store_close" not in effects
        loop.finish_worker()
        assert cleanup.done() and cleanup.error is None and lifecycle.context_closed
        assert worker.worker_exited and worker.body_exited and worker.collected
        # A queued worker sees sticky stop and makes no ordinary Store call.
        assert "late_worker_body" not in effects
        assert effects[-2:] == ["prompt_close", "store_close"]
        assert scope.context_close_started and not lifecycle.unknown_context
        CAUSALS.append("actual context close waits for cancelled awaiter worker body + server ack")

    def test_actual_lifecycle_cancellation_during_worker_body_keeps_context_live(self):
        work, loop, scope, _server, _site, effects, request_ack = self.server_world()
        module = self.harness.module
        lifecycle = work.lifecycle
        scope.publication = None
        selected = self.harness.selected(
            "adapter",
            {
                "_FixtureLifecycle": ("_drain_serving_owned", "_cleanup_owned"),
            },
            {"server": SimpleNamespace(SHUTDOWN_TIMEOUT_S=5.0)},
        )
        from types import MethodType

        lifecycle._drain_serving_owned = MethodType(
            selected._FixtureLifecycle._drain_serving_owned, lifecycle
        )
        lifecycle.serving, lifecycle.resources = work, scope
        lifecycle.setup = None
        lifecycle.cleanup_failures = []
        lifecycle.prompt_close_attempted = lifecycle.store_close_attempted = False
        lifecycle.context_closed = lifecycle.unknown_context = False
        lifecycle.adapter._close_generation = lambda ctx: effects.append("prompt_close")
        work.context.store = SimpleNamespace(close=lambda: effects.append("store_close"))
        lifecycle.alias.state = "SERVER_OWNED"
        frame = module._CURRENT_FRAME.get()

        async def completed_start():
            return None

        frame.task = loop.start_caller(completed_start())
        scope.start = frame
        frame.body_exited = frame.collected = True
        loop.run()
        cleanup_tasks = []

        def running_body():
            assert worker.worker_entered and not worker.worker_exited
            waiter.cancel()
            loop.run()
            assert isinstance(waiter.error, work_models.ModelCancellation)
            cleanup = loop.start_caller(selected._FixtureLifecycle._cleanup_owned(lifecycle))
            cleanup_tasks.append(cleanup)
            loop.run()
            request_ack.set_result(None)
            loop.run()
            assert scope.stop_returned and not cleanup.done()
            assert 'store_close' not in effects and 'prompt_close' not in effects
            # The actual admitted synchronous body is still using this exact context.
            assert work.context.store is lifecycle.ctx.store
            effects.append('late_worker_body')
            return None

        worker = work.launch_worker(next(iter(module._WORKER_SITES)), running_body)
        loop.run()
        waiter = loop.start_caller(work.collect(worker))
        loop.run()
        loop.finish_worker()
        cleanup = cleanup_tasks[0]
        assert cleanup.done() and cleanup.error is None and lifecycle.context_closed
        assert worker.worker_exited and worker.body_exited and worker.collected
        assert effects.count("late_worker_body") == 1
        assert effects[-2:] == ["prompt_close", "store_close"]
        assert scope.context_close_started and not lifecycle.unknown_context
        CAUSALS.append(
            "actual entered worker retains live context across stop/cancel "
            "until synchronous body exit"
        )

    def test_actual_lifecycle_unknown_user_keeps_store_and_prompt_open(self):
        work, loop, scope, _server, _site, effects, request_ack = self.server_world()
        module = self.harness.module
        lifecycle = work.lifecycle
        selected = self.harness.selected(
            "adapter",
            {
                "_FixtureLifecycle": ("_drain_serving_owned", "_cleanup_owned"),
            },
            {"server": SimpleNamespace(SHUTDOWN_TIMEOUT_S=5.0)},
        )
        from types import MethodType

        lifecycle._drain_serving_owned = MethodType(
            selected._FixtureLifecycle._drain_serving_owned, lifecycle
        )
        lifecycle.serving, lifecycle.resources = work, scope
        lifecycle.setup = None
        lifecycle.cleanup_failures = []
        lifecycle.prompt_close_attempted = lifecycle.store_close_attempted = False
        lifecycle.context_closed = lifecycle.unknown_context = False
        lifecycle.adapter._close_generation = lambda ctx: effects.append("prompt_close")
        work.context.store = SimpleNamespace(close=lambda: effects.append("store_close"))
        lifecycle.alias.state = "SERVER_OWNED"
        frame = module._CURRENT_FRAME.get()

        async def completed_start():
            return None

        frame.task = loop.start_caller(completed_start())
        scope.start = frame
        loop.run()
        original = RuntimeError("unknown submitted work")
        work.retain_unknown_acquisition(next(iter(module._WORKER_SITES)), original)
        request_ack.set_result(None)
        cleanup = loop.start_caller(selected._FixtureLifecycle._cleanup_owned(lifecycle))
        loop.run()
        assert cleanup.error is not None and lifecycle.unknown_context
        assert not lifecycle.context_closed and not scope.context_close_started
        assert "prompt_close" not in effects and "store_close" not in effects
        assert work.first_failure is original
        CAUSALS.append(
            "actual unknown acquisition blocks prompt and Store close after listener drain"
        )
