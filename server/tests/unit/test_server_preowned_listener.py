"""RP01 ownership tests with normal HMP imports and scoped inert dependencies.

No socket or event loop is created by the test ports. Package import belongs to
the ordinary CI environment; these tests do not qualify kernel/TLS custody.
"""
from __future__ import annotations

import contextlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from hmp_plugin import server as hmp_server

ACTUAL_SITE = hmp_server._FixtureSockSite


class Cancelled(BaseException):
    pass


class Pause:
    def __await__(self):
        yield "serving"


class Socket:
    def __init__(self):
        self.family = 2
        self.type = 1
        self.fd = 42
        self.blocking = False
        self.listening = 1
        self.endpoint = ("127.0.0.1", 8443)
        self.closes = 0
        self.close_error = False

    def fileno(self):
        return self.fd

    def getblocking(self):
        return self.blocking

    def getsockopt(self, level, option):
        if (level, option) != (1, 30):
            raise AssertionError("unexpected socket option")
        return self.listening

    def getsockname(self):
        return self.endpoint

    def close(self):
        self.closes += 1
        if self.close_error:
            raise OSError("inert close error")
        self.fd = -1


class BaseSite:
    async def start(self):
        self._runner.sites.append(self)

    async def stop(self):
        if self._server is not None:
            raise AssertionError("server closure must precede unregister")
        self._runner.sites.remove(self)


class Server:
    def __init__(self, sock, pause=False):
        self.sockets = (sock,)
        self.sock = sock
        self.pause = pause
        self.closed = False

    async def start_serving(self):
        if self.pause:
            await Pause()

    def close(self):
        if not self.closed:
            self.closed = True
            self.sock.close()


class Watch:
    def cancel(self):
        pass

    def __await__(self):
        if False:
            yield None
        raise Cancelled()


class Loop:
    def __init__(self, failure=None):
        self.failure = failure
        self.created = None
        self.calls = []

    async def create_server(self, protocol, **kwargs):
        self.calls.append((protocol, kwargs))
        if kwargs["start_serving"] is not False:
            raise AssertionError("ownership gap")
        if self.failure == "create":
            raise ValueError("inert create failure")
        self.created = Server(kwargs["sock"], self.failure == "pause")
        if self.failure == "readback":
            self.created.sockets = (SimpleNamespace(getsockname=lambda: ("127.0.0.1", 1)),)
        return self.created

    def create_task(self, coroutine):
        coroutine.close()
        if self.failure == "task":
            raise ValueError("inert task failure")
        return Watch()


class Runner:
    def __init__(self, failure=None):
        self.failure = failure
        self.sites = []
        self.server = object()
        self.cleanups = 0

    async def setup(self):
        if self.failure == "pause_setup":
            await Pause()
        if self.failure == "setup":
            raise ValueError("inert setup failure")

    async def cleanup(self):
        self.cleanups += 1
        for site in list(self.sites):
            await site.stop()
        if self.failure == "cleanup":
            raise ValueError("inert cleanup failure")


def finish(coroutine):
    try:
        value = coroutine.send(None)
    except StopIteration as done:
        return done.value
    coroutine.close()
    raise AssertionError(f"unexpected suspension: {value}")


def patch_ports(test_case, failure=None):
    """Patch this module's dependency references; unittest restores each scope.

    The real HmpServer and _FixtureSockSite bodies and inheritance are used.
    No event loop, socket or scheduled task is created by these inert ports.
    """
    loop = Loop(failure)
    runner = Runner(failure)

    def site_factory(*args, **kwargs):
        if failure == "site":
            raise ValueError("inert constructor failure")
        return ACTUAL_SITE(*args, **kwargs)

    replacements = {
        "socket": SimpleNamespace(socket=Socket, AF_INET=2, SOCK_STREAM=1,
                                  SOL_SOCKET=1, SO_ACCEPTCONN=30),
        "web": SimpleNamespace(BaseSite=BaseSite),
        "asyncio": SimpleNamespace(get_running_loop=lambda: loop,
                                  current_task=lambda: None, CancelledError=Cancelled,
                                  Event=Event),
        "contextlib": contextlib,
        "ListenerConfigError": ValueError,
        "server_ssl_context": lambda *_: "exact-tls-context",
        "build_app": lambda ctx: ctx,
        "_HmpAppRunner": lambda *_args, **_kwargs: runner,
        "_FixtureSockSite": site_factory,
        "AllowListedAccessLogger": object(),
        "logging": SimpleNamespace(getLogger=lambda _: object()),
        "ACCESS_LOGGER_NAME": "inert",
        "_ParserSafeLogger": lambda: object(),
        "SHUTDOWN_TIMEOUT_S": 2,
        "log_event": lambda *_args, **_kwargs: None,
    }
    scoped = patch.dict(hmp_server.__dict__, replacements)
    scoped.start()
    test_case.addCleanup(scoped.stop)
    return hmp_server.__dict__, runner, loop


class Event:
    def __init__(self):
        self.value = False

    def is_set(self):
        return self.value

    def set(self):
        self.value = True


def subject(namespace):
    ctx = SimpleNamespace(identity=object(), direct_send_deps=None)
    settings = SimpleNamespace(bind="127.0.0.1", port=8443)
    return namespace["HmpServer"](ctx, settings)


class FixtureListenerTests(unittest.TestCase):
    def load_ports(self, failure=None):
        return patch_ports(self, failure)

    def test_validation_refusals_retain_caller_ownership(self):
        cases = [("family", 10), ("type", 2), ("fd", -1), ("blocking", True),
                 ("listening", 0), ("endpoint", ("127.0.0.2", 8443)),
                 ("endpoint", ("127.0.0.1", 8444))]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                namespace, runner, _ = self.load_ports()
                owner, sock = subject(namespace), Socket()
                setattr(sock, field, value)
                with self.assertRaises(ValueError):
                    finish(owner._start_fixture_listener(sock))
                self.assertEqual(sock.closes, 0)
                self.assertFalse(owner._fixture_used)
                self.assertEqual(runner.cleanups, 0)

    def test_settings_and_wrong_object_refuse_without_transfer(self):
        for bind, port in [("localhost", 8443), ("127.0.0.1", 0),
                           ("127.0.0.1", True), ("127.0.0.1", 65536)]:
            namespace, _, _ = self.load_ports()
            owner, sock = subject(namespace), Socket()
            owner.settings = SimpleNamespace(bind=bind, port=port)
            with self.assertRaises(ValueError):
                finish(owner._start_fixture_listener(sock))
            self.assertEqual(sock.closes, 0)
        namespace, _, _ = self.load_ports()
        with self.assertRaises(ValueError):
            finish(subject(namespace)._start_fixture_listener(object()))

    def test_success_uses_exact_socket_tls_and_no_bind_arguments(self):
        namespace, runner, loop = self.load_ports()
        owner, sock = subject(namespace), Socket()
        finish(owner._start_fixture_listener(sock))
        self.assertIs(owner._runner, runner)
        self.assertIs(loop.calls[0][1]["sock"], sock)
        self.assertEqual(loop.calls[0][1], {
            "sock": sock, "ssl": "exact-tls-context", "backlog": 128,
            "start_serving": False,
        })
        self.assertEqual(owner.bound, sock.endpoint)
        self.assertEqual(sock.closes, 0)
        finish(runner.cleanup())
        self.assertEqual(sock.closes, 1)
        self.assertEqual(runner.sites, [])

    def test_startup_failures_close_once_and_cannot_replay(self):
        for stage in ["setup", "site", "create", "task"]:
            with self.subTest(stage=stage):
                namespace, runner, _ = self.load_ports(stage)
                owner, sock = subject(namespace), Socket()
                with self.assertRaises(ValueError):
                    finish(owner._start_fixture_listener(sock))
                self.assertEqual(sock.closes, 1)
                self.assertEqual(runner.cleanups, 1)
                self.assertFalse(owner._starting)
                with self.assertRaises(RuntimeError):
                    finish(owner._start_fixture_listener(Socket()))
                with self.assertRaises(RuntimeError):
                    finish(owner.start())

    def test_cancel_at_serving_has_retained_server_before_cleanup(self):
        namespace, runner, loop = self.load_ports("pause")
        owner, sock = subject(namespace), Socket()
        operation = owner._start_fixture_listener(sock)
        self.assertEqual(operation.send(None), "serving")
        self.assertIs(runner.sites[0]._server, loop.created)
        with self.assertRaises(RuntimeError):
            finish(owner.stop())
        with self.assertRaises(Cancelled):
            operation.throw(Cancelled())
        self.assertEqual(sock.closes, 1)
        self.assertEqual(runner.cleanups, 1)
        self.assertEqual(runner.sites, [])

    def test_ambiguous_close_is_fatal_and_never_replayed(self):
        namespace, runner, loop = self.load_ports("pause")
        owner, sock = subject(namespace), Socket()
        operation = owner._start_fixture_listener(sock)
        self.assertEqual(operation.send(None), "serving")
        sock.close_error = True
        with self.assertRaises(RuntimeError):
            operation.throw(Cancelled())
        self.assertEqual(sock.closes, 1)
        self.assertFalse(runner.sites[0]._fixture_closed)
        self.assertFalse(loop.created.sock.fd == -1)

    def test_freshness_refusal_leaves_socket_with_caller(self):
        for attribute, value in [("_fixture_used", True), ("_runner", object())]:
            namespace, _, _ = self.load_ports()
            owner, sock = subject(namespace), Socket()
            setattr(owner, attribute, value)
            with self.assertRaises(RuntimeError):
                finish(owner._start_fixture_listener(sock))
            self.assertEqual(sock.closes, 0)


    def test_successful_owner_stop_closes_transferred_socket_once(self):
        namespace, runner, _ = self.load_ports()
        owner, sock = subject(namespace), Socket()
        finish(owner._start_fixture_listener(sock))
        finish(owner.stop(notify=False))
        self.assertEqual(sock.closes, 1)
        self.assertEqual(sock.fd, -1)
        self.assertTrue(owner.closed.is_set())
        self.assertIsNone(owner._runner)
        finish(owner.stop(notify=False))
        self.assertEqual(sock.closes, 1)
        self.assertEqual(runner.cleanups, 1)

    def test_setup_cancellation_closes_raw_owned_socket(self):
        namespace, runner, loop = self.load_ports("pause_setup")
        owner, sock = subject(namespace), Socket()
        operation = owner._start_fixture_listener(sock)
        self.assertEqual(operation.send(None), "serving")
        with self.assertRaises(Cancelled):
            operation.throw(Cancelled())
        self.assertEqual(sock.closes, 1)
        self.assertEqual(runner.cleanups, 1)
        self.assertIsNone(loop.created)

    def test_wrong_bound_socket_readback_refuses(self):
        namespace, runner, _ = self.load_ports("readback")
        owner, sock = subject(namespace), Socket()
        with self.assertRaises(RuntimeError):
            finish(owner._start_fixture_listener(sock))
        self.assertEqual(sock.closes, 1)
        self.assertIsNone(owner.bound)
        self.assertIsNone(owner._runner)
        self.assertEqual(runner.sites, [])

    def test_before_runner_failure_consumes_accepted_socket(self):
        namespace, runner, _ = self.load_ports()
        owner, sock = subject(namespace), Socket()

        def fail_tls(*_args):
            raise ValueError("inert TLS failure")

        namespace["server_ssl_context"] = fail_tls
        with self.assertRaises(ValueError):
            finish(owner._start_fixture_listener(sock))
        self.assertEqual(sock.closes, 1)
        self.assertEqual(runner.cleanups, 0)
        self.assertIsNone(owner.bound)

    def test_cleanup_failure_stays_fatal_with_socket_closed(self):
        namespace, runner, _ = self.load_ports("cleanup")
        owner, sock = subject(namespace), Socket()

        def fail_site(*_args, **_kwargs):
            raise ValueError("inert site failure")

        namespace["_FixtureSockSite"] = fail_site
        with self.assertRaises(ValueError):
            finish(owner._start_fixture_listener(sock))
        self.assertEqual(sock.closes, 1)
        self.assertEqual(runner.cleanups, 1)
        self.assertFalse(owner.closed.is_set())
        self.assertIsNone(owner._runner)

    def test_default_start_retains_tcp_site_route(self):
        namespace, runner, _ = self.load_ports()
        owner = subject(namespace)
        calls = []

        class TCP:
            def __init__(self, selected_runner, bind, port, **kwargs):
                calls.append((selected_runner, bind, port, kwargs))
                self._server = SimpleNamespace(sockets=())

            async def start(self):
                return None

        namespace["web"].TCPSite = TCP
        namespace["address_allowed"] = lambda _bind: True
        finish(owner.start())
        self.assertEqual(calls, [(runner, "127.0.0.1", 8443, {
            "ssl_context": "exact-tls-context", "reuse_address": True,
        })])
        self.assertFalse(owner._fixture_used)


    def test_production_reservation_refuses_fixture_and_second_production(self):
        namespace, runner, _ = self.load_ports("pause_setup")
        namespace["address_allowed"] = lambda _: True
        owner, sock = subject(namespace), Socket()
        production = owner.start()
        self.assertEqual(production.send(None), "serving")
        self.assertTrue(owner._starting)
        with self.assertRaises(RuntimeError):
            finish(owner._start_fixture_listener(sock))
        with self.assertRaises(RuntimeError):
            finish(owner.start())
        with self.assertRaises(RuntimeError):
            finish(owner.stop())
        self.assertEqual(sock.closes, 0)
        self.assertFalse(owner._fixture_used)
        with self.assertRaises(Cancelled):
            production.throw(Cancelled())
        self.assertFalse(owner._starting)
        self.assertFalse(owner._startup_uncertain)
        self.assertEqual(runner.cleanups, 1)

    def test_fixture_reservation_refuses_production_before_setup_returns(self):
        namespace, _, _ = self.load_ports("pause_setup")
        owner, sock = subject(namespace), Socket()
        fixture = owner._start_fixture_listener(sock)
        self.assertEqual(fixture.send(None), "serving")
        with self.assertRaises(RuntimeError):
            finish(owner.start())
        with self.assertRaises(Cancelled):
            fixture.throw(Cancelled())
        self.assertEqual(sock.closes, 1)

    def test_production_setup_failure_can_retry_after_normal_cleanup(self):
        namespace, failed, _ = self.load_ports("setup")
        namespace["address_allowed"] = lambda _: True
        owner = subject(namespace)
        with self.assertRaises(ValueError):
            finish(owner.start())
        self.assertFalse(owner._starting)
        self.assertFalse(owner._startup_uncertain)
        self.assertEqual(failed.cleanups, 1)
        replacement = Runner()
        namespace["_HmpAppRunner"] = lambda *_args, **_kwargs: replacement

        class TCP:
            def __init__(self, *_args, **_kwargs):
                self._server = SimpleNamespace(sockets=())

            async def start(self):
                return None

        namespace["web"].TCPSite = TCP
        finish(owner.start())
        self.assertIs(owner._runner, replacement)

    def test_production_cancellation_can_retry_after_pre_listener_cleanup(self):
        namespace, failed, _ = self.load_ports("pause_setup")
        namespace["address_allowed"] = lambda _: True
        owner = subject(namespace)
        operation = owner.start()
        self.assertEqual(operation.send(None), "serving")
        with self.assertRaises(Cancelled):
            operation.throw(Cancelled())
        replacement = Runner()
        namespace["_HmpAppRunner"] = lambda *_args, **_kwargs: replacement
        sock = Socket()
        finish(owner._start_fixture_listener(sock))
        self.assertIs(owner._runner, replacement)
        self.assertEqual(failed.cleanups, 1)
        finish(replacement.cleanup())
        self.assertEqual(sock.closes, 1)

    def test_production_listener_failure_or_cancel_disables_retry(self):
        for cancel in (False, True):
            namespace, runner, _ = self.load_ports()
            namespace["address_allowed"] = lambda _: True
            owner, sock = subject(namespace), Socket()

            class TCP:
                def __init__(self, *_args, **_kwargs):
                    self._server = None

                async def start(self, cancel=cancel):
                    if cancel:
                        await Pause()
                    raise ValueError("inert listener start failure")

            namespace["web"].TCPSite = TCP
            operation = owner.start()
            if cancel:
                self.assertEqual(operation.send(None), "serving")
                with self.assertRaises(Cancelled):
                    operation.throw(Cancelled())
            else:
                with self.assertRaises(ValueError):
                    finish(operation)
            self.assertTrue(owner._startup_uncertain)
            self.assertFalse(owner._starting)
            self.assertEqual(runner.cleanups, 1)
            with self.assertRaises(RuntimeError):
                finish(owner.start())
            with self.assertRaises(RuntimeError):
                finish(owner._start_fixture_listener(sock))
            self.assertEqual(sock.closes, 0)

    def test_production_cleanup_failure_disables_retry(self):
        namespace, runner, _ = self.load_ports("cleanup")
        namespace["address_allowed"] = lambda _: True
        owner = subject(namespace)

        async def fail_setup():
            raise ValueError("inert setup failure")

        runner.setup = fail_setup
        with self.assertRaises(ValueError):
            finish(owner.start())
        self.assertTrue(owner._startup_uncertain)
        with self.assertRaises(RuntimeError):
            finish(owner.start())
        self.assertEqual(runner.cleanups, 1)


    def test_scoped_dependencies_restore_after_failure_or_cancellation(self):
        for raised in (ValueError, Cancelled):
            nested_case = unittest.TestCase()
            before = {name: hmp_server.__dict__[name] for name in (
                "asyncio", "socket", "web", "_HmpAppRunner", "_FixtureSockSite",
            )}
            try:
                patch_ports(nested_case)
                raise raised("inert test interruption")
            except raised:
                pass
            finally:
                nested_case.doCleanups()
            for name, expected in before.items():
                self.assertIs(hmp_server.__dict__[name], expected)


if __name__ == "__main__":
    unittest.main()
