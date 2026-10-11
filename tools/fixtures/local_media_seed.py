"""Public native APIs and unchanged registered producer, for an admitted disposable fixture.

No CLI, listener/process launch, dependency installation, direct SQLite or native replacement.
All native imports are delayed until the future root executor has admitted the complete graph.
The return observer only captures the actual returned object; validation follows the call.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import stat
import sys
import threading
from contextlib import contextmanager
from pathlib import Path

from local_media_provider_response import DUMMY_KEY, EXPECTED_REQUEST, require

_FORBIDDEN_ENV = {
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_ORG_ID",
    "OPENAI_ORGANIZATION",
    "OPENAI_PROJECT_ID",
    "OPENAI_IMAGE_MODEL",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "FAL_KEY",
    "FAL_API_KEY",
    "KREA_API_KEY",
}


def check_environment(home: Path, runtime: Path) -> None:
    require(os.environ.get("HOME") == "/Users/mhedhli", "literal_home")
    require(not (_FORBIDDEN_ENV & os.environ.keys()), "ambient_provider")
    require(os.environ.get("HERMES_HOME") == str(home), "native_home")
    require(os.environ.get("HERMES_RUNTIME_DIR") == str(runtime), "native_runtime")
    require(os.environ.get("HMP_MEDIA_FIXTURE_IMAGE_KEY") == DUMMY_KEY, "dummy_key")
    for path in (home, runtime):
        require(path.is_absolute() and str(path).startswith("/private/tmp/"), "owned_path")
        require(".." not in path.parts, "owned_path")
        fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for component in path.parts[1:]:
                child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                previous = fd
                fd = None
                try:
                    os.close(previous)
                except BaseException as parent_error:
                    try:
                        os.close(child)
                    except BaseException as child_error:
                        raise child_error from parent_error
                    raise
                fd = child
            s = os.fstat(fd)
            require(s.st_uid == os.getuid() and stat.S_IMODE(s.st_mode) == 0o700, "owned_mode")
        finally:
            if fd is not None:
                os.close(fd)


def _leaf_identity(s) -> tuple[int, ...]:
    """Stable leaf metadata; read-induced access time is deliberately excluded."""
    values = (
        s.st_dev,
        s.st_ino,
        s.st_mode,
        s.st_uid,
        s.st_gid,
        s.st_nlink,
        s.st_size,
        s.st_mtime_ns,
        s.st_ctime_ns,
    )
    require(all(type(value) is int for value in values), "leaf_metadata")
    return values


def source_pin(function, expected_path: Path, expected_sha256: str) -> None:
    require(Path(inspect.getsourcefile(function)) == expected_path, "factory_source")
    parent = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in expected_path.parts[1:-1]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            previous = parent
            parent = None
            try:
                os.close(previous)
            except BaseException as parent_error:
                try:
                    os.close(child)
                except BaseException as child_error:
                    raise child_error from parent_error
                raise
            parent = child
        fd = os.open(expected_path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            before = os.fstat(fd)
            require(
                stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= 65536,
                "factory_leaf",
            )
            before_identity = _leaf_identity(before)
            digest = hashlib.sha256()
            remaining = before.st_size
            while remaining:
                chunk = os.read(fd, min(remaining, 8192))
                require(bool(chunk), "factory_short")
                remaining -= len(chunk)
                digest.update(chunk)
            require(not os.read(fd, 1) and digest.hexdigest() == expected_sha256, "factory_body")
            require(
                _leaf_identity(os.fstat(fd)) == before_identity
                and _leaf_identity(
                    os.stat(expected_path.name, dir_fd=parent, follow_symlinks=False)
                )
                == before_identity,
                "factory_drift",
            )
        finally:
            os.close(fd)
    finally:
        if parent is not None:
            os.close(parent)


def client_observation(client, *, sdk_type, httpx_type, base_url: str) -> dict:
    """Read-only inspection of the object the exact native _build_client returns."""
    require(type(client) is sdk_type, "client_type")
    native_http = client._client
    require(type(native_http) is httpx_type, "fallback_client")
    require(str(client.base_url) == base_url + "/", "effective_url")
    require(
        client.api_key == DUMMY_KEY
        and client.auth_headers == {"Authorization": f"Bearer {DUMMY_KEY}"},
        "effective_auth",
    )
    require(type(client.max_retries) is int and client.max_retries == 2, "max_retries")
    require(native_http.follow_redirects is False, "redirects")
    require(client.organization is None and client.project is None, "sdk_scope")
    require(client.default_headers.get("OpenAI-Project") == "", "project_header")
    timeout = native_http.timeout
    require(
        (timeout.connect, timeout.read, timeout.write, timeout.pool) == (15.0, None, 15.0, 10.0),
        "native_timeout",
    )
    return {
        "actualFactoryReturns": 1,
        "customHttpx": True,
        "redirects": False,
        "sdkMaxRetries": 2,
        "effectiveURL": base_url + "/",
        "dummyAuth": True,
    }


@contextmanager
def observe_factory(factory, *, sdk_type, httpx_type, base_url: str):
    """Capture-only current-thread observer around synchronous full producer dispatch.

    The callback does not validate, throw, retain frames/locals, or change native results.
    Qualification is checked after dispatch. Default SDK fallback can therefore execute,
    but the separately admitted network profile must deny every nonfixture endpoint.
    A callback failure/missing/wrong-thread/multiple return refuses after the native call.
    """
    prior = sys.getprofile()
    require(prior is None, "ambient_profiler")
    owner_thread = threading.get_ident()
    captured, rows = [], []
    state = {"count": 0, "failed": False}

    def observer(frame, event, value):
        # Never raise into the native factory; no source/factory/object substitution.
        try:
            if event == "return" and frame.f_code is factory.__code__:
                state["count"] = min(2, state["count"] + 1)
                if state["count"] == 1:
                    captured.append((value, threading.get_ident()))
                else:
                    state["failed"] = True
        except Exception:
            state["failed"] = True

    sys.setprofile(observer)
    try:
        yield rows
    finally:
        current = sys.getprofile()
        sys.setprofile(prior)
    require(current is observer, "factory_observer_stale")
    require(
        not state["failed"] and state["count"] == 1 and len(captured) == 1,
        "factory_observation_missing_duplicate",
    )
    client, observed_thread = captured[0]
    require(threading.get_ident() == owner_thread == observed_thread, "factory_thread")
    rows.append(
        client_observation(client, sdk_type=sdk_type, httpx_type=httpx_type, base_url=base_url)
    )


def produce_once(
    *,
    home: Path,
    runtime: Path,
    profile_home: Path,
    port: int,
    invocation: str,
    factory_path: Path,
    factory_sha256: str,
) -> tuple[str, dict]:
    """The real registered full producer. Future response ledger must join this invocation.

    Root supplies sealed profile/config/source pins. No source edits, skip flags, alternate
    registry/provider, fallback endpoint or terminal process is constructed here.
    """
    from local_media_provider_response import exact_port

    check_environment(home, runtime)
    exact_port(port)
    require(invocation in {"P01", "P02", "P03", "P04"}, "invocation")
    require(profile_home.parent == home / "profiles", "profile_home")
    from gateway.run import _profile_runtime_scope

    # isort: split
    import httpx

    # isort: split
    import openai

    # isort: split
    import model_tools

    # isort: split
    from tools import image_generation_tool as image_tool

    base_url = f"http://127.0.0.1:{port}/v1"
    with _profile_runtime_scope(profile_home, hydrate_secrets=True):
        require(image_tool._plugin_provider_name() == "openai", "configured_provider")
        provider = image_tool._get_plugin_provider("openai")
        module = inspect.getmodule(type(provider))
        require(
            module is not None and type(provider).__name__ == "OpenAIImageGenProvider",
            "builtin_provider",
        )
        require(module._resolve_endpoint() == (base_url, DUMMY_KEY), "configured_endpoint")
        factory = module._build_client
        source_pin(factory, factory_path, factory_sha256)
        with observe_factory(
            factory, sdk_type=openai.OpenAI, httpx_type=httpx.Client, base_url=base_url
        ) as observations:
            raw = model_tools.handle_function_call(
                "image_generate",
                {"prompt": EXPECTED_REQUEST["prompt"]},
                task_id=f"media-fixture-{invocation}",
                tool_call_id=f"media-fixture-{invocation}",
            )
        require(type(raw) is str and len(raw.encode("utf-8")) <= 65536, "producer_result_cap")
        result = json.loads(raw)
        require(
            result.get("success") is True
            and "error" not in result
            and result.get("provider") == "openai",
            "producer_result",
        )
        require(type(result.get("image")) is str, "producer_image")
        return raw, {
            "invocation": invocation,
            **observations[0],
            "toolResultSHA256": hashlib.sha256(raw.encode()).hexdigest(),
        }


def seed_tool_row(db, session_id: str, raw_result: str, invocation: str) -> None:
    """Called only with a real native SessionDB under a private profile scope."""
    require(invocation in {"P01", "P02", "P03", "P04"}, "invocation")
    require(type(raw_result) is str and len(raw_result.encode()) <= 65536, "seed_result_cap")
    call_id = f"media-fixture-{invocation}"
    db.append_messages_batch(
        session_id,
        [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": "image_generate",
                            "arguments": json.dumps({"prompt": EXPECTED_REQUEST["prompt"]}),
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": raw_result,
                "tool_name": "image_generate",
                "tool_call_id": call_id,
            },
        ],
    )


def seed_profile(
    *,
    home: Path,
    runtime: Path,
    profile: str,
    user_id: str,
    chat_id: str,
    raw_result: str,
    invocation: str,
    bot_session_id: str,
) -> dict:
    """Public SessionStore routing and SessionDB APIs; gateways must be stopped for seeding.

    Initial native grant uses PairingStore approve_request; no SQL or copied grant decision.
    The future root controller owns actual P1-P4 approval-owner setup separately.
    """
    check_environment(home, runtime)
    require(profile in {"media-alpha", "media-beta"}, "profile")
    from gateway.config import Platform, load_gateway_config

    # isort: split
    from gateway.session import SessionSource, SessionStore

    # isort: split
    from gateway.pairing import PairingStore

    # isort: split
    from hermes_constants import reset_hermes_home_override, set_hermes_home_override

    # isort: split
    from hermes_state import SessionDB

    # isort: split
    from hermes_cli.plugins import discover_plugins

    discover_plugins(force=True)
    platform = Platform("hmp")
    sessions = SessionStore(home / "sessions", load_gateway_config())  # ROOT before scope.
    token = set_hermes_home_override(str(home / "profiles" / profile))
    try:
        phone = sessions.get_or_create_session(
            SessionSource(
                platform=platform,
                chat_id=chat_id,
                user_id=user_id,
                chat_type="dm",
                profile=profile,
            ),
            force_new=False,
            touch_activity=True,
        )
        db = SessionDB(home / "profiles" / profile / "state.db")
        try:
            db.create_session(bot_session_id, "cli")
            db.set_session_title(bot_session_id, "Bot Chat")
            db.set_session_hidden(bot_session_id, True)
            seed_tool_row(db, bot_session_id, raw_result, invocation)
            seed_tool_row(db, phone.session_id, raw_result, invocation)
            # Native decoys are persisted too; text never establishes image authority.
            db.append_message(bot_session_id, "assistant", content="MEDIA: fixture text")
            db.append_message(
                bot_session_id,
                "tool",
                content=raw_result,
                tool_name="other_tool",
                tool_call_id="media-fixture-decoy",
            )
            require(db.get_session(bot_session_id) is not None, "native_bot_readback")
            require(len(db.get_messages(bot_session_id, limit=64)) == 4, "native_rows_readback")
        finally:
            db.close()
        pairing = PairingStore(profile=profile)
        code = pairing.generate_code("hmp", user_id, "media-fixture")
        require(code is not None, "native_pending")
        pending = [row for row in pairing.list_pending("hmp") if row["user_id"] == user_id]
        require(len(pending) == 1, "native_pending_count")
        approved = pairing.approve_request("hmp", pending[0]["request_id"])
        require(type(approved) is dict and approved.get("user_id") == user_id, "native_grant")
        return {
            "botSession": bot_session_id,
            "phoneSession": phone.session_id,
            "nativeSeed": "SessionDB/SessionStore/PairingStore",
        }
    finally:
        reset_hermes_home_override(token)


def prepare_profiles(*, home: Path, runtime: Path) -> None:
    """No clone, alias, imported user skills or channel synchronization."""
    check_environment(home, runtime)
    from hermes_cli.profiles import create_profile, get_profile_dir

    for profile in ("media-alpha", "media-beta"):
        create_profile(
            profile,
            clone_from=None,
            clone_all=False,
            clone_config=False,
            no_alias=True,
            no_skills=True,
            clone_channels=False,
            sync_imports=False,
        )
        require(get_profile_dir(profile) == home / "profiles" / profile, "profile_readback")


def revoke_grant(*, home: Path, runtime: Path, profile: str, user_id: str) -> None:
    check_environment(home, runtime)
    require(profile in {"media-alpha", "media-beta"}, "profile")
    from gateway.pairing import PairingStore

    PairingStore(profile=profile).revoke("hmp", user_id)
    # The actual next HTTP ERR3 result, not revoke's return alone, proves the negative.


def advance_phone(*, home: Path, runtime: Path, profile: str, user_id: str, chat_id: str) -> str:
    check_environment(home, runtime)
    require(profile in {"media-alpha", "media-beta"}, "profile")
    from gateway.config import Platform, load_gateway_config

    # isort: split
    from gateway.session import SessionSource, SessionStore

    # isort: split
    from hermes_constants import reset_hermes_home_override, set_hermes_home_override

    store = SessionStore(home / "sessions", load_gateway_config())
    token = set_hermes_home_override(str(home / "profiles" / profile))
    try:
        return store.get_or_create_session(
            SessionSource(
                platform=Platform("hmp"),
                chat_id=chat_id,
                user_id=user_id,
                chat_type="dm",
                profile=profile,
            ),
            force_new=True,
            touch_activity=True,
        ).session_id
    finally:
        reset_hermes_home_override(token)
