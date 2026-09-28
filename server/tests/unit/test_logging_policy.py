"""Logging allow-list (SEC-4, SR-007; T033)."""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from hmp_plugin.logging_policy import (
    ID_PREFIX_LEN,
    LOGGER_NAME,
    AllowListedAccessLogger,
    id_prefix,
    log_bridge_exception,
    log_event,
)


def test_id_prefix_len_constant() -> None:
    assert ID_PREFIX_LEN == 8


def test_id_prefix_truncates() -> None:
    assert id_prefix("dev_abcdefghijklmnop") == "dev_abcd"


def test_id_prefix_rejects_short_value() -> None:
    with pytest.raises(ValueError):
        id_prefix("short")


def test_id_prefix_rejects_non_string() -> None:
    with pytest.raises(TypeError):
        id_prefix(12345678)  # type: ignore[arg-type]


def test_id_prefix_never_returns_more_than_the_limit() -> None:
    huge = "s" * 500
    assert len(id_prefix(huge)) == ID_PREFIX_LEN


def test_log_event_emits_only_allowlisted_fields(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        log_event("token_refresh", outcome="revoked", device_id="dev_abcdefghijklmnop")
    assert len(caplog.records) == 1
    message = caplog.records[0].getMessage()
    assert "event=token_refresh" in message
    assert "outcome=revoked" in message
    assert "device_id=dev_abcd" in message  # first 8 chars only
    assert "ijklmnop" not in message  # the rest of the raw id never appears


def test_log_event_with_no_ids() -> None:
    # Must not raise when no id kwargs are supplied.
    assert logging.getLogger(LOGGER_NAME).name == LOGGER_NAME  # sanity: logger exists
    log_event("ready", outcome="ok")


@pytest.mark.parametrize(
    "bad_event", ["", "Has Spaces", "UPPER", "has-dash", "1starts_digit", "x" * 65]
)
def test_log_event_rejects_malformed_event_code(bad_event: str) -> None:
    with pytest.raises(ValueError):
        log_event(bad_event, outcome="ok")


@pytest.mark.parametrize("bad_outcome", ["", "Revoked", "revoked!", "has space"])
def test_log_event_rejects_malformed_outcome_code(bad_outcome: str) -> None:
    with pytest.raises(ValueError):
        log_event("ready", outcome=bad_outcome)


def test_log_event_multiple_ids_sorted_deterministically(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        log_event(
            "pair_complete", outcome="ok", pairing_id="pid_abcdefgh", device_id="dev_abcdefgh"
        )
    message = caplog.records[0].getMessage()
    assert message.index("device_id=") < message.index("pairing_id=")


def test_log_bridge_exception_logs_type_only(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        try:
            raise KeyError("some sensitive detail that must never be logged")
        except KeyError as exc:
            log_bridge_exception(exc)
    message = caplog.records[0].getMessage()
    assert "exception_type=KeyError" in message
    assert "sensitive detail" not in message


# --------------------------------------------------------------------------------------------
# AllowListedAccessLogger
# --------------------------------------------------------------------------------------------


def _fake_request() -> SimpleNamespace:
    return SimpleNamespace(
        method="POST",
        match_info=SimpleNamespace(
            route=SimpleNamespace(
                resource=SimpleNamespace(canonical="/hmp/v1/bots/{p}/authorize")
            )
        ),
        # Deliberately present, to prove the access logger never reads them.
        query_string="token=super-secret-value",
        headers={"Authorization": "Bearer super-secret-token"},
        path="/hmp/v1/bots/f1-alpha/authorize",
    )


def _fake_response() -> SimpleNamespace:
    return SimpleNamespace(status=200)


def test_access_logger_reduced_fields(caplog: pytest.LogCaptureFixture) -> None:
    access_logger_name = "test.access"
    logger = AllowListedAccessLogger(logger=logging.getLogger(access_logger_name))
    with caplog.at_level(logging.INFO, logger=access_logger_name):
        logger.log(_fake_request(), _fake_response(), 0.125)
    message = caplog.records[0].getMessage()
    assert "POST" in message
    assert "/hmp/v1/bots/{p}/authorize" in message
    assert "200" in message
    assert "super-secret" not in message
    assert "f1-alpha" not in message  # the concrete path never appears, only the route template


def test_access_logger_handles_missing_match_info() -> None:
    logger = AllowListedAccessLogger(logger=logging.getLogger("test.access.bare"))
    bare = SimpleNamespace(method="GET")
    logger.log(bare, _fake_response(), 0.01)  # must not raise


@pytest.mark.parametrize("method", ["GET", "POST", "HEAD"])
def test_access_logger_passes_through_allow_listed_methods(
    caplog: pytest.LogCaptureFixture, method: str
) -> None:
    access_logger_name = f"test.access.{method}"
    logger = AllowListedAccessLogger(logger=logging.getLogger(access_logger_name))
    req = _fake_request()
    req.method = method
    with caplog.at_level(logging.INFO, logger=access_logger_name):
        logger.log(req, _fake_response(), 0.01)
    message = caplog.records[0].getMessage()
    assert message.startswith(method + " ")


@pytest.mark.parametrize(
    "method", ["PUT", "DELETE", "PATCH", "OPTIONS", "TRACE", "PROPFIND", "FOOBAR", "-"]
)
def test_access_logger_maps_any_other_method_to_a_fixed_token(
    caplog: pytest.LogCaptureFixture, method: str
) -> None:
    # A raw request line's method is an open-ended token, not an enum, so it must never be
    # written to the log verbatim (SEC-4) -- only the fixed set F1 actually uses passes through.
    access_logger_name = f"test.access.other.{method}"
    logger = AllowListedAccessLogger(logger=logging.getLogger(access_logger_name))
    req = _fake_request()
    req.method = method
    with caplog.at_level(logging.INFO, logger=access_logger_name):
        logger.log(req, _fake_response(), 0.01)
    message = caplog.records[0].getMessage()
    assert message.startswith("OTHER ")
    assert method not in message
