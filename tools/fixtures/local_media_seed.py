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

_NATIVE_FACTORY_SHA256 = "3876c8027bb9d5b50bf35af7133477b19d774a44a864d15c07a456050aa30936"

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
    require(profile_home.name in {"media-alpha", "media-beta"}, "profile")
    require(factory_sha256 == _NATIVE_FACTORY_SHA256, "reviewed_factory_source")
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
        source_pin(factory, factory_path, factory_sha256)  # actual post-dispatch source readback
        require(
            type(raw) is str and len(raw) <= 65536 and len(raw.encode("utf-8")) <= 65536,
            "producer_result_cap",
        )
        result = json.loads(raw)
        require(
            result.get("success") is True
            and "error" not in result
            and result.get("provider") == "openai",
            "producer_result",
        )
        require(type(result.get("image")) is str, "producer_image")
        return raw, {
            "schema": "native-media-producer-v1",
            "profile": profile_home.name,
            "toolCallId": f"media-fixture-{invocation}",
            "factorySourceSHA256": factory_sha256,
            "toolResultBytes": len(raw.encode("utf-8")),
            "invocation": invocation,
            **observations[0],
            "toolResultSHA256": hashlib.sha256(raw.encode()).hexdigest(),
        }


def _receipt_hash(value: dict) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")
    require(len(encoded) <= 8192, "receipt_cap")
    return hashlib.sha256(encoded).hexdigest()


def _producer_receipt(receipt: dict, raw_result: str, invocation: str, profile: str) -> dict:
    """Validate captured producer data; dict possession is not native/source authority."""
    require(type(raw_result) is str and len(raw_result) <= 65536, "seed_result_cap")
    raw = raw_result.encode("utf-8")
    require(len(raw) <= 65536, "seed_result_cap")
    require(
        type(receipt) is dict
        and set(receipt)
        == {
            "schema",
            "profile",
            "toolCallId",
            "factorySourceSHA256",
            "toolResultBytes",
            "invocation",
            "actualFactoryReturns",
            "customHttpx",
            "redirects",
            "sdkMaxRetries",
            "effectiveURL",
            "dummyAuth",
            "toolResultSHA256",
        },
        "producer_receipt_shape",
    )
    require(
        invocation in {"P01", "P02", "P03", "P04"} and profile in {"media-alpha", "media-beta"},
        "producer_scope",
    )
    require(
        receipt["schema"] == "native-media-producer-v1"
        and receipt["profile"] == profile
        and receipt["invocation"] == invocation
        and receipt["toolCallId"] == f"media-fixture-{invocation}"
        and receipt["factorySourceSHA256"] == _NATIVE_FACTORY_SHA256,
        "producer_binding",
    )
    require(
        type(receipt["toolResultBytes"]) is int
        and receipt["toolResultBytes"] == len(raw)
        and receipt["toolResultSHA256"] == hashlib.sha256(raw).hexdigest(),
        "producer_body",
    )
    require(
        type(receipt["actualFactoryReturns"]) is int
        and receipt["actualFactoryReturns"] == 1
        and receipt["customHttpx"] is True
        and receipt["redirects"] is False
        and type(receipt["sdkMaxRetries"]) is int
        and receipt["sdkMaxRetries"] == 2
        and receipt["dummyAuth"] is True,
        "producer_factory",
    )
    # The exact numeric provider port is joined to its actual EOF receipt later.
    url = receipt["effectiveURL"]
    require(
        type(url) is str
        and len(url) <= 40
        and url.startswith("http://127.0.0.1:")
        and url.endswith("/v1/"),
        "producer_endpoint",
    )
    port = url[len("http://127.0.0.1:") : -len("/v1/")]
    require(
        port.isascii()
        and port.isdecimal()
        and str(int(port)) == port
        and 1024 <= int(port) <= 65535,
        "producer_endpoint",
    )
    return dict(receipt)


def _seed_messages(raw_result: str, invocation: str) -> list[dict]:
    call_id = f"media-fixture-{invocation}"
    return [
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
    ]


def _native_rows(db, session_id: str, messages: list[dict]) -> tuple[dict, ...]:
    """Bounded public API readback; only observed IDs, never guessed insert counters.

    This is a disposable, stopped-gateway synthetic database. Native decoding remains in
    the admitted process; the API's SQL row limit is not a hostile-database byte bound.
    """
    require(type(session_id) is str and 0 < len(session_id) <= 256, "native_session")
    require(type(messages) is list and 1 <= len(messages) <= 4, "native_message_count")
    rows = db.get_messages(session_id, include_inactive=True, limit=len(messages) + 1)
    require(type(rows) is list and len(rows) == len(messages), "native_rows_count")
    result = []
    previous = 0
    for row, expected in zip(rows, messages, strict=True):
        require(type(row) is dict, "native_row_shape")
        row_id = row.get("id")
        require(type(row_id) is int and previous < row_id <= (1 << 63) - 1, "native_row_id")
        require(
            row.get("session_id") == session_id
            and type(row.get("active")) is int
            and row["active"] == 1,
            "native_row_scope",
        )
        require(
            row.get("role") == expected["role"]
            and type(row.get("content")) is str
            and len(row["content"]) <= 65536
            and row["content"] == expected["content"]
            and row.get("tool_name") == expected.get("tool_name")
            and row.get("tool_call_id") == expected.get("tool_call_id")
            and row.get("tool_calls") == expected.get("tool_calls"),
            "native_row_body",
        )
        result.append(
            {
                "id": row_id,
                "session": session_id,
                "role": row["role"],
                "toolName": row.get("tool_name"),
                "toolCallId": row.get("tool_call_id"),
                "contentSHA256": hashlib.sha256(row["content"].encode("utf-8")).hexdigest(),
                "toolCallsSHA256": hashlib.sha256(
                    json.dumps(
                        row.get("tool_calls"),
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=True,
                        allow_nan=False,
                    ).encode("ascii")
                ).hexdigest(),
            }
        )
        previous = row_id
    return tuple(result)


def seed_tool_row(db, session_id: str, raw_result: str, invocation: str) -> tuple[dict, ...]:
    """Preserve native atomic batch. Only an empty private session may be seeded once."""
    require(invocation in {"P01", "P02", "P03", "P04"}, "invocation")
    require(
        type(raw_result) is str
        and len(raw_result) <= 65536
        and len(raw_result.encode("utf-8")) <= 65536,
        "seed_result_cap",
    )
    require(type(session_id) is str and 0 < len(session_id) <= 256, "native_session")
    before = db.get_messages(session_id, include_inactive=True, limit=1)
    require(type(before) is list and not before, "native_session_not_empty")
    messages = _seed_messages(raw_result, invocation)
    inserted = db.append_messages_batch(session_id, messages)
    require(type(inserted) is int and inserted == 2, "native_insert_count")
    return _native_rows(db, session_id, messages)


def join_provider_seed(producer: dict, provider: dict, seed: dict, *, raw_result: str) -> dict:
    """Pure join of actual private captures, never a substitute for root seal/custody.

    Native row IDs come from seed readbacks; HMP refs MUST come from the later authenticated
    descriptor response joined to those IDs. No registry mint or expected ref is produced.
    """
    from local_media_provider_response import BODY_CAP, HEADER_CAP, PNG_SHA256, RESPONSE_SHA256

    require(type(producer) is dict and type(seed) is dict and type(provider) is dict, "join_shape")
    require(
        set(seed)
        == {
            "botSession",
            "phoneSession",
            "nativeSeed",
            "schema",
            "invocation",
            "profile",
            "toolCallId",
            "toolResultSHA256",
            "producerReceiptSHA256",
            "botRows",
            "phoneRows",
            "botToolRow",
            "phoneToolRow",
            "nativeReadbackSHA256",
        },
        "seed_receipt_shape",
    )
    producer = _producer_receipt(producer, raw_result, seed["invocation"], seed["profile"])
    require(
        seed["schema"] == "native-media-seed-v1"
        and seed["nativeSeed"] == "SessionDB/SessionStore/PairingStore"
        and seed["toolCallId"] == producer["toolCallId"],
        "seed_receipt_scope",
    )
    for key in ("botSession", "phoneSession"):
        require(type(seed[key]) is str and 0 < len(seed[key]) <= 256, "seed_session")
    require(seed["botSession"] != seed["phoneSession"], "seed_sessions_distinct")
    ids = []
    for key, count, tool_key in (("botRows", 4, "botToolRow"), ("phoneRows", 2, "phoneToolRow")):
        require(type(seed[key]) is list and len(seed[key]) == count, "seed_row_count")
        require(
            all(type(value) is int and 1 <= value <= (1 << 63) - 1 for value in seed[key])
            and seed[key] == sorted(seed[key]),
            "seed_row_ids",
        )
        require(type(seed[tool_key]) is int and seed[tool_key] == seed[key][1], "seed_tool_row")
        ids.extend(seed[key])
    require(len(set(ids)) == 6, "seed_ids_distinct")
    for key in ("toolResultSHA256", "producerReceiptSHA256", "nativeReadbackSHA256"):
        value = seed[key]
        require(
            type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value),
            "seed_hash",
        )
    require(
        set(provider)
        == {
            "invocation",
            "requestSHA256",
            "retryCount",
            "posts",
            "responseSHA256",
            "peerEOF",
            "completionReadRequested",
            "receivedBytes",
            "readCalls",
            "providerPort",
            "responseBytes",
            "pngSHA256",
        },
        "provider_receipt_shape",
    )
    require(
        provider["invocation"] == producer.get("invocation") == seed.get("invocation")
        and producer.get("profile") == seed.get("profile")
        and seed.get("producerReceiptSHA256") == _receipt_hash(producer)
        and producer.get("toolResultSHA256") == seed.get("toolResultSHA256"),
        "join_producer_seed",
    )
    for field in (
        "retryCount",
        "posts",
        "completionReadRequested",
        "receivedBytes",
        "readCalls",
        "providerPort",
        "responseBytes",
    ):
        require(type(provider[field]) is int, "provider_integer")
    require(
        provider["peerEOF"] is True
        and provider["completionReadRequested"] == 1
        and provider["retryCount"] == 0
        and provider["posts"] == 1
        and provider["responseBytes"] == 135
        and provider["responseSHA256"] == RESPONSE_SHA256
        and provider["pngSHA256"] == PNG_SHA256,
        "provider_completion",
    )
    require(
        0 < provider["receivedBytes"] <= HEADER_CAP + BODY_CAP
        and 1 <= provider["readCalls"] <= HEADER_CAP + BODY_CAP + 1,
        "provider_credit",
    )
    port = provider["providerPort"]
    require(
        1024 <= port <= 65535 and producer.get("effectiveURL") == f"http://127.0.0.1:{port}/v1/",
        "provider_endpoint",
    )
    request_hash = provider["requestSHA256"]
    require(
        type(request_hash) is str
        and len(request_hash) == 64
        and all(c in "0123456789abcdef" for c in request_hash),
        "provider_request_hash",
    )
    return {
        "schema": "native-media-provenance-join-v1",
        "invocation": seed["invocation"],
        "profile": seed["profile"],
        "producerReceiptSHA256": _receipt_hash(producer),
        "providerReceiptSHA256": _receipt_hash(provider),
        "seedReceiptSHA256": _receipt_hash(seed),
    }


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
    producer_receipt: dict,
) -> dict:
    """Public SessionStore routing and SessionDB APIs; gateways must be stopped for seeding.

    Initial native grant uses PairingStore approve_request; no SQL or copied grant decision.
    The future root controller owns actual P1-P4 approval-owner setup separately.
    """
    producer = _producer_receipt(producer_receipt, raw_result, invocation, profile)
    producer_hash = _receipt_hash(producer)
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
            require(phone.session_id != bot_session_id, "distinct_native_sessions")
            bot_rows = seed_tool_row(db, bot_session_id, raw_result, invocation)
            phone_rows = seed_tool_row(db, phone.session_id, raw_result, invocation)
            # Native decoys are persisted too; text never establishes image authority.
            text_id = db.append_message(bot_session_id, "assistant", content="MEDIA: fixture text")
            decoy_id = db.append_message(
                bot_session_id,
                "tool",
                content=raw_result,
                tool_name="other_tool",
                tool_call_id="media-fixture-decoy",
            )
            require(db.get_session(bot_session_id) is not None, "native_bot_readback")
            messages = _seed_messages(raw_result, invocation)
            bot_final = _native_rows(
                db,
                bot_session_id,
                [
                    *messages,
                    {"role": "assistant", "content": "MEDIA: fixture text"},
                    {
                        "role": "tool",
                        "content": raw_result,
                        "tool_name": "other_tool",
                        "tool_call_id": "media-fixture-decoy",
                    },
                ],
            )
            phone_final = _native_rows(db, phone.session_id, messages)
            require(bot_final[:2] == bot_rows and phone_final == phone_rows, "native_final_drift")
            require(
                type(text_id) is int
                and type(decoy_id) is int
                and [row["id"] for row in bot_final[2:]] == [text_id, decoy_id],
                "native_decoy_ids",
            )
            all_ids = [row["id"] for row in bot_final + phone_final]
            require(len(set(all_ids)) == 6, "native_row_identity_collision")
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
            "schema": "native-media-seed-v1",
            "invocation": invocation,
            "profile": profile,
            "toolCallId": f"media-fixture-{invocation}",
            "toolResultSHA256": hashlib.sha256(raw_result.encode("utf-8")).hexdigest(),
            "producerReceiptSHA256": producer_hash,
            "botRows": [row["id"] for row in bot_final],
            "phoneRows": [row["id"] for row in phone_final],
            "botToolRow": bot_rows[1]["id"],
            "phoneToolRow": phone_rows[1]["id"],
            "nativeReadbackSHA256": _receipt_hash({"bot": bot_final, "phone": phone_final}),
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
