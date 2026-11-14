"""PN-AV: availability precedence, exact configuration grammars and live snapshots."""

from dataclasses import FrozenInstanceError
from urllib.parse import urlsplit

import pytest

from hmp_plugin import push_config, wire

from .hmp_kit import Env


def block(**changes):
    return {
        "enabled": True,
        "relay_url": "https://relay.example.invalid/base",
        "relay_audience": "Hermes.Beta-1",
        "relay_kids": ["Key.A-1"],
        **changes,
    }


def verdict(config, **changes):
    return push_config.evaluate(
        config, **{"direct_send": True, "approvals": True, "phone_chat": False, **changes}
    )


@pytest.mark.parametrize("enabled", [None, False, 1, "true", [], {}])
def test_only_literal_host_opt_in_enabled(enabled):
    value = verdict(block(enabled=enabled, relay_kids=[]), approvals=False)
    assert (value.available, value.why, value.relay) == (False, "push_disabled", None)


@pytest.mark.parametrize("config", [None, False, [], "enabled", {}])
def test_missing_or_malformed_block_is_disabled(config):
    assert verdict(config).why == "push_disabled"


@pytest.mark.parametrize("url", [
    "http://relay.example.invalid", "", "https://", "https://relay.example.invalid:0",
    "https://relay.example.invalid:65536", "https://user:pass@relay.example.invalid",
    "https://relay.example.invalid?token=private", "https://relay.example.invalid#fragment",
    "https://relay.example.invalid?", "https://relay.example.invalid#",
    "https://relay.example.invalid/base?", "https://relay.example.invalid/base#",
    " https://relay.example.invalid", "https://relay.example.invalid\n",
    "https://relay.example.invalid\\host", "https://[invalid]", None, 1,
])
def test_relay_requires_https_base_without_ambiguous_credentials_or_suffix(url):
    assert verdict(block(relay_url=url), direct_send=False).why == "relay_unconfigured"


@pytest.mark.parametrize("url", [
    "https://relay.example.invalid", "https://relay.example.invalid/base/",
    "https://relay.example.invalid:443/base", "https://[::1]:8443/base", "HTTPS://relay.example.invalid",
])
def test_valid_host_https_base_accepted_without_network_resolution(url):
    assert verdict(block(relay_url=url)).available
    endpoint = urlsplit(url.rstrip("/") + "/v1/push")
    assert endpoint.path.endswith("/v1/push")
    assert not endpoint.query and not endpoint.fragment


@pytest.mark.parametrize("kids", [None, [], (), "Key.A-1", ["good", " bad"], ["good", 1],
                                  [".first"], ["-first"], ["x" * 65], ["\u00e9"], ["key\n"]])
def test_one_malformed_kid_closes_whole_config(kids):
    value = verdict(block(relay_kids=kids))
    assert value.why == "relay_unconfigured" and value.relay is None
    assert value.live_kids == frozenset()


@pytest.mark.parametrize(
    "audience", [None, "", ".first", "-first", "x" * 129, "\u00e9", "a b", "a\n"]
)
def test_audience_grammar(audience):
    assert verdict(block(relay_audience=audience)).why == "relay_unconfigured"


def test_grammar_bounds_exact_case_and_no_normalization():
    value = verdict(block(relay_audience="A" * 128, relay_kids=["K" * 64, "key", "KEY"]))
    assert value.available
    assert value.live_kids == frozenset({"K" * 64, "key", "KEY"})
    assert value.relay.audience == "A" * 128


@pytest.mark.parametrize("pins", [None, [], (), "x", [None], [1], ["A" * 42], ["A" * 44],
                                  ["A" * 42 + "="], ["!" * 43], ["A" * 42 + "B"],
                                  [wire.b64u_encode(b"x" * 32)] * 2,
                                  [wire.b64u_encode(bytes([n]) * 32) for n in range(9)]])
def test_configured_pins_are_exact_canonical_distinct_nonempty_bounded_list(pins):
    assert verdict(block(relay_spki_pins=pins)).why == "relay_unconfigured"


@pytest.mark.parametrize("count", [1, 8])
def test_pin_boundaries_and_omission(count):
    assert verdict(block()).relay.spki_pins is None
    values = [bytes([n]) * 32 for n in range(count)]
    value = verdict(block(relay_spki_pins=[wire.b64u_encode(p) for p in values]))
    assert value.available and value.relay.spki_pins == tuple(values)


@pytest.mark.parametrize("direct,bot,phone", [
    (False, True, True), (True, False, False), (1, True, True), (True, 1, False),
])
def test_approval_prerequisites_are_literal_and_closed(direct, bot, phone):
    value = verdict(block(), direct_send=direct, approvals=bot, phone_chat=phone)
    assert value.why == "approvals_unavailable"
    assert value.relay is not None and value.live_kids == frozenset()


@pytest.mark.parametrize("bot,phone", [(True, False), (False, True), (True, True)])
def test_either_approval_member_opens_availability(bot, phone):
    assert verdict(block(), approvals=bot, phone_chat=phone).available


def test_snapshot_is_immutable_and_has_no_logging_repr():
    source = block(relay_spki_pins=[wire.b64u_encode(b"x" * 32)])
    value = verdict(source)
    source["relay_kids"][0] = "changed"
    source["relay_spki_pins"].clear()
    source["relay_url"] = "https://changed.invalid"
    assert value.live_kids == frozenset({"Key.A-1"})
    assert value.relay.spki_pins == (b"x" * 32,)
    assert value.relay.url == "https://relay.example.invalid/base"
    with pytest.raises(FrozenInstanceError):
        value.available = False
    assert "relay.example" not in repr(value) + repr(value.relay)


def test_environment_never_enables_or_repairs_host_settings(monkeypatch):
    monkeypatch.setenv("PUSH_ENABLED", "true")
    monkeypatch.setenv("PUSH_RELAY_URL", "https://relay.example.invalid")
    monkeypatch.setenv("PUSH_RELAY_SPKI_PINS", wire.b64u_encode(b"x" * 32))
    assert verdict({}).why == "push_disabled"
    assert verdict(block(relay_spki_pins=None)).why == "relay_unconfigured"


def test_context_reads_live_host_values_without_changing_approval_members(tmp_path):
    env = Env(tmp_path)
    current = block()
    calls = []
    ctx = env.ctx
    ctx.push_settings = lambda: (calls.append(1), current)[1]
    ctx.direct_send_flag = lambda: True
    ctx.approvals_available = lambda: True
    ctx.phone_chat_available = lambda: False
    assert ctx.push_availability().available and len(calls) == 1
    current["relay_kids"] = ["bad!"]
    assert ctx.push_availability().why == "relay_unconfigured" and len(calls) == 2
    assert ctx.is_approvals_available() and not ctx.is_phone_chat_available()
    current["enabled"] = False
    assert ctx.push_availability().why == "push_disabled"
    current.update(block())
    ctx.direct_send_flag = lambda: False
    assert ctx.push_availability().why == "approvals_unavailable"
    ctx.direct_send_flag = lambda: True
    ctx.approvals_available = lambda: False
    ctx.phone_chat_available = lambda: True
    assert ctx.push_availability().available
    env.store.close()
