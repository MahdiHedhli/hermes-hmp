"""Spec 034: the `approvals` and `phone_chat` eligibility members.

Covers R1-R5 and N13, N14, N23-N25, N30, N33.

Everything here uses synthetic Hermes trees under tmp_path and injected version readers. No real
Hermes module is imported, nothing is fetched, and no installed Hermes home is touched.
"""

from __future__ import annotations

import dataclasses
import sys
import textwrap
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path

import pytest

from hmp_plugin import compat, hermes_version
from hmp_plugin.compat import (
    PHONE_CHAT_DEPENDENCIES,
    DependencySpec,
    Feature,
    FeatureStatus,
    Unavailable,
    evaluate_eligibility,
    probe_dependencies,
)
from hmp_plugin.hermes_version import HermesVersion, Scheme, VersionSource
from hmp_plugin.request_ctx import ServerContext

FLOOR = HermesVersion(Scheme.SEMVER, (0, 21, 5), VersionSource.LITERAL)
BELOW = HermesVersion(Scheme.SEMVER, (0, 21, 4), VersionSource.LITERAL)
NEWER = HermesVersion(Scheme.SEMVER, (7, 3, 1), VersionSource.LITERAL)
PLACEHOLDER = HermesVersion(Scheme.UNKNOWN, (), VersionSource.UNKNOWN)

TOP_LEVEL = ("tools", "gateway")


# --------------------------------------------------------------------------------------------
# A synthetic Hermes tree with exactly the phone_chat surface, with one switch per defect
# --------------------------------------------------------------------------------------------

_FILES = {
    "tools/__init__.py": "",
    "gateway/__init__.py": "",
    "gateway/platforms/__init__.py": "",
    "tools/approval.py": """
        def resolve_gateway_approval(session_key, choice, resolve_all=False, reason=None,
                                     request_id=None):
            return 0

        def list_gateway_approvals(session_key):
            return []
    """,
    "tools/approval_context.py": """
        def _get_approval_timeout():
            return 300
    """,
    "tools/clarify_gateway.py": """
        def resolve_gateway_clarify(clarify_id, response):
            return True

        def mark_awaiting_text(clarify_id):
            return True

        def get_clarify_timeout():
            return 3600
    """,
    "gateway/platforms/base.py": """
        class BasePlatformAdapter:
            async def _send_exec_approval_prompt(self, prompt):
                return None

            async def send_clarify(self, chat_id, question, choices, clarify_id, session_key,
                                   metadata=None):
                return None
    """,
    "gateway/platforms/event.py": """
        from dataclasses import dataclass

        @dataclass
        class MessageEvent:
            text: str = ""
            allow_gateway_control: bool = True
    """,
}


def _write_tree(root: Path, overrides: dict[str, str] | None = None) -> None:
    files = {**_FILES, **(overrides or {})}
    for rel, body in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(body).lstrip("\n"), encoding="utf-8")


def _purge() -> None:
    for name in list(sys.modules):
        if name.split(".")[0] in TOP_LEVEL:
            del sys.modules[name]


@pytest.fixture()
def tree(tmp_path: Path) -> Iterator[Callable[[dict[str, str] | None], Path]]:
    root = tmp_path / "hermes-src"
    root.mkdir()
    sys.path.insert(0, str(root))
    _purge()

    def build(overrides: dict[str, str] | None = None) -> Path:
        _write_tree(root, overrides)
        _purge()
        return root

    try:
        yield build
    finally:
        sys.path.remove(str(root))
        _purge()


def _missing(root: Path) -> tuple[str, ...]:
    return tuple(probe_dependencies(hermes_root=root, specs=PHONE_CHAT_DEPENDENCIES))


# --------------------------------------------------------------------------------------------
# The phone_chat table against real module shapes (N13, N14)
# --------------------------------------------------------------------------------------------


def test_the_complete_phone_surface_is_available(tree: Callable[..., Path]) -> None:
    assert _missing(tree()) == ()


def test_n13_event_without_allow_gateway_control_is_missing(tree: Callable[..., Path]) -> None:
    root = tree(
        {
            "gateway/platforms/event.py": """
                from dataclasses import dataclass

                @dataclass
                class MessageEvent:
                    text: str = ""
            """
        }
    )
    assert _missing(root) == ("gateway.platforms.event.MessageEvent.allow_gateway_control",)


def test_n13_a_plain_attribute_or_property_is_not_a_declared_field(
    tree: Callable[..., Path],
) -> None:
    for body in (
        """
        from dataclasses import dataclass

        @dataclass
        class MessageEvent:
            text: str = ""
            allow_gateway_control = True  # no annotation: a class variable, not a field
        """,
        """
        from dataclasses import dataclass

        @dataclass
        class MessageEvent:
            text: str = ""

            @property
            def allow_gateway_control(self):
                return True
        """,
        """
        class MessageEvent:  # not a dataclass at all
            allow_gateway_control = True
        """,
    ):
        root = tree({"gateway/platforms/event.py": body})
        assert _missing(root) == ("gateway.platforms.event.MessageEvent.allow_gateway_control",)


def test_n14_a_resolver_without_a_named_request_id_is_missing(tree: Callable[..., Path]) -> None:
    for signature in (
        "session_key, choice, resolve_all=False, reason=None",
        "session_key, choice, **kwargs",
        "session_key, choice, resolve_all=False, **kwargs",
        "*args, **kwargs",
    ):
        root = tree(
            {
                "tools/approval.py": f"""
                    def resolve_gateway_approval({signature}):
                        return 0

                    def list_gateway_approvals(session_key):
                        return []
                """
            }
        )
        assert _missing(root) == ("tools.approval.resolve_gateway_approval",), signature


def test_n14_a_resolver_without_a_named_resolve_all_is_missing(
    tree: Callable[..., Path],
) -> None:
    root = tree(
        {
            "tools/approval.py": """
                def resolve_gateway_approval(session_key, choice, request_id=None):
                    return 0

                def list_gateway_approvals(session_key):
                    return []
            """
        }
    )
    assert _missing(root) == ("tools.approval.resolve_gateway_approval",)


def test_each_missing_helper_names_only_itself(tree: Callable[..., Path]) -> None:
    removals = {
        "tools/approval.py": ("tools.approval.list_gateway_approvals",),
        "tools/approval_context.py": ("tools.approval_context._get_approval_timeout",),
    }
    for path, expected in removals.items():
        root = tree({path: "VALUE = 1\n"})
        assert set(expected) <= set(_missing(root)), path


def test_retire_clarify_card_is_not_a_probe_row(tree: Callable[..., Path]) -> None:
    """Hermes finds it on the adapter's own class; the base class has no such method (source of
    `f97608f1`, `8afaab37` and `ac0cfa7d`), so probing the base would close every build."""
    labels = {spec.label for spec in PHONE_CHAT_DEPENDENCIES}
    assert not any("retire_clarify_card" in label for label in labels)
    assert _missing(tree()) == ()  # the synthetic base has no such method


def test_a_shadow_module_outside_the_hermes_tree_is_missing(
    tree: Callable[..., Path], tmp_path: Path
) -> None:
    root = tree()
    shadow = tmp_path / "site-packages" / "tools"
    shadow.mkdir(parents=True)
    (shadow / "__init__.py").write_text("")
    (shadow / "approval.py").write_text(
        "def resolve_gateway_approval(session_key, choice, resolve_all=False, request_id=None):\n"
        "    return 1\n\ndef list_gateway_approvals(session_key):\n    return []\n"
    )
    for name in list(sys.modules):
        if name.split(".")[0] == "tools":
            del sys.modules[name]
    sys.path.insert(0, str(shadow.parent))
    try:
        missing = _missing(root)
    finally:
        sys.path.remove(str(shadow.parent))
    assert "tools.approval.resolve_gateway_approval" in missing


# --------------------------------------------------------------------------------------------
# Eligibility: floors, send, unknown and newer builds (R1, R2, R4, N23-N25)
# --------------------------------------------------------------------------------------------


class Recorder:
    """A probe double: records the tables asked about and the imports it would have made."""

    def __init__(self, missing: dict[str, Sequence[str]] | None = None) -> None:
        self.tables: list[str] = []
        self.missing = missing or {}

    def __call__(self, _root: Path, specs: Sequence[DependencySpec]) -> Sequence[str]:
        names = {
            id(compat.READ_CORE_DEPENDENCIES): "read",
            id(compat.SESSION_BROWSING_DEPENDENCIES): "session_browsing",
            id(compat.DIRECT_SEND_DEPENDENCIES): "send",
            id(compat.CRON_DEPENDENCIES): "jobs",
            id(compat.MODEL_DEPENDENCIES): "model",
            id(PHONE_CHAT_DEPENDENCIES): "phone_chat",
            id(compat.LOCAL_MEDIA_DEPENDENCIES): "local_media",
        }
        name = names[id(specs)]
        self.tables.append(name)
        return self.missing.get(name, ())


def _evaluate(
    version: HermesVersion,
    probe: Recorder | None = None,
    hook: Callable[[Path], bool | None] | None = None,
) -> compat.Eligibility:
    return evaluate_eligibility(
        root_locator=lambda: Path("/nonexistent-hermes-root"),
        version_reader=lambda _root: version,
        probe=probe or Recorder(),
        evidence=lambda _root: {},
        hook_probe=hook or (lambda _root: None),
    )


def test_both_members_use_the_send_floor() -> None:
    assert hermes_version.FEATURE_FLOORS["approvals"] == hermes_version.FEATURE_FLOORS["send"]
    assert hermes_version.FEATURE_FLOORS["phone_chat"] == hermes_version.FEATURE_FLOORS["send"]


@pytest.mark.parametrize("version", [FLOOR, NEWER, PLACEHOLDER])
def test_n24_floor_newer_and_unknown_versions_are_attempted(version: HermesVersion) -> None:
    probe = Recorder()
    eligibility = _evaluate(version, probe)
    assert eligibility.available(Feature.APPROVALS)
    assert eligibility.available(Feature.PHONE_CHAT)
    assert probe.tables.count("phone_chat") == 1
    assert "approvals" not in probe.tables  # no table of its own


def test_n25_below_the_floor_both_members_are_refused_and_nothing_is_probed() -> None:
    probe = Recorder()
    eligibility = _evaluate(BELOW, probe)
    for member in (Feature.APPROVALS, Feature.PHONE_CHAT):
        assert eligibility.features[member] == FeatureStatus(
            False, Unavailable.VERSION_BELOW_FLOOR
        )
    assert "phone_chat" not in probe.tables and "send" not in probe.tables


def test_without_send_both_members_close_and_phone_helpers_are_not_probed() -> None:
    probe = Recorder({"send": ["hermes_state.SessionDB.get_session"]})
    eligibility = _evaluate(FLOOR, probe)
    assert not eligibility.available(Feature.SEND)
    for member in (Feature.APPROVALS, Feature.PHONE_CHAT):
        assert eligibility.features[member] == FeatureStatus(False, Unavailable.REQUIRES_SEND)
    assert "phone_chat" not in probe.tables


def test_a_missing_phone_helper_closes_only_phone_chat() -> None:
    probe = Recorder({"phone_chat": ["tools.approval.list_gateway_approvals"]})
    eligibility = _evaluate(NEWER, probe)
    assert eligibility.available(Feature.SEND)
    assert eligibility.available(Feature.APPROVALS)  # Bot Chat answers never use the helpers
    phone = eligibility.features[Feature.PHONE_CHAT]
    assert (phone.available, phone.reason) == (False, Unavailable.DEPENDENCY_MISSING)
    assert phone.missing == ("tools.approval.list_gateway_approvals",)


def test_a_probe_that_raises_closes_phone_chat_with_a_fixed_reason() -> None:
    def broken(_root: Path, specs: Sequence[DependencySpec]) -> Sequence[str]:
        if specs is PHONE_CHAT_DEPENDENCIES:
            raise RuntimeError("secret detail that must not travel")
        return ()

    eligibility = evaluate_eligibility(
        root_locator=lambda: Path("/nonexistent-hermes-root"),
        version_reader=lambda _root: FLOOR,
        probe=broken,
        evidence=lambda _root: {},
        hook_probe=lambda _root: None,
    )
    phone = eligibility.features[Feature.PHONE_CHAT]
    assert (phone.available, phone.reason, phone.missing) == (False, Unavailable.PROBE_FAILED, ())
    assert eligibility.available(Feature.APPROVALS)


def test_a_core_read_failure_makes_both_members_requires_read() -> None:
    eligibility = _evaluate(FLOOR, Recorder({"read": ["gateway.run.GatewayRunner"]}))
    for member in (Feature.APPROVALS, Feature.PHONE_CHAT):
        assert eligibility.features[member] == FeatureStatus(False, Unavailable.REQUIRES_READ)


# --------------------------------------------------------------------------------------------
# The session-stream hook diagnostic never gates (R4, N23, N24)
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("hook", [True, False, None])
def test_n23_the_hook_fact_changes_no_availability(hook: bool | None) -> None:
    eligibility = _evaluate(FLOOR, hook=lambda _root: hook)
    assert eligibility.stream_approval_hook is hook
    assert {f for f in Feature if eligibility.available(f)} == set(Feature)


def test_n24_a_raising_or_non_boolean_hook_probe_is_unknown_and_harmless() -> None:
    def boom(_root: Path) -> bool:
        raise RuntimeError("renamed hook on a newer build")

    assert _evaluate(NEWER, hook=boom).stream_approval_hook is None
    assert _evaluate(NEWER, hook=lambda _root: "yes").stream_approval_hook is None  # type: ignore[arg-type,return-value]
    assert _evaluate(NEWER, hook=boom).available(Feature.APPROVALS)


def test_the_hook_is_not_probed_when_approvals_are_closed() -> None:
    calls: list[Path] = []
    eligibility = _evaluate(BELOW, hook=lambda root: calls.append(root))  # type: ignore[arg-type,return-value]
    assert calls == [] and eligibility.stream_approval_hook is None


def _api_server(tmp_path: Path, body: str) -> Path:
    root = tmp_path / "src"
    (root / "gateway" / "platforms").mkdir(parents=True)
    (root / "gateway" / "platforms" / "api_server.py").write_text(body, encoding="utf-8")
    return root


def test_stream_hook_probe_reads_one_file_and_imports_nothing(tmp_path: Path) -> None:
    before = set(sys.modules)
    present = _api_server(
        tmp_path / "a", "class A:\n    def _register_session_stream_approval(self, run_id):\n"
        "        pass\n"
    )
    absent = _api_server(tmp_path / "b", "class A:\n    pass\n")
    renamed = _api_server(
        tmp_path / "c", "class A:\n    def _register_stream_approval(self):\n        pass\n"
    )
    assert compat.stream_hook_present(present) is True
    assert compat.stream_hook_present(absent) is False
    assert compat.stream_hook_present(renamed) is False  # a newer build's rename: a fact, no gate
    assert compat.stream_hook_present(tmp_path / "missing") is None
    assert set(sys.modules) == before


def test_stream_hook_probe_refuses_an_oversized_file(tmp_path: Path) -> None:
    root = _api_server(tmp_path, "x" * (compat._STREAM_HOOK_READ_CAP + 10))
    assert compat.stream_hook_present(root) is None


# --------------------------------------------------------------------------------------------
# Manifests never decide availability (R5, N30)
# --------------------------------------------------------------------------------------------


def test_n30_no_manifest_reader_can_change_availability(monkeypatch: pytest.MonkeyPatch) -> None:
    baseline = _evaluate(FLOOR)
    expected = {f: baseline.available(f) for f in Feature}

    def explode(*_a: object, **_k: object) -> None:
        raise AssertionError("a manifest or fingerprint reader was reached")

    for name in ("load_read_compat_list", "match_build", "compute_read_bridge_fingerprint"):
        monkeypatch.setattr(compat, name, explode)
    # The production evidence matcher swallows reader failures: availability is unchanged.
    eligibility = evaluate_eligibility(
        root_locator=lambda: Path("/nonexistent-hermes-root"),
        version_reader=lambda _root: FLOOR,
        probe=Recorder(),
        hook_probe=lambda _root: None,
    )
    assert {f: eligibility.available(f) for f in Feature} == expected


def test_no_manifest_named_for_approvals_ships_or_is_read() -> None:
    package = Path(compat.__file__).parent
    assert not (package / "approval_supported_builds.json").exists()
    for source in package.glob("*.py"):
        text = source.read_text(encoding="utf-8")
        assert "approval_supported_builds" not in text, source.name
    assert not hasattr(compat, "APPROVAL_COMPAT_FILE")


# --------------------------------------------------------------------------------------------
# Defaults deny (N33)
# --------------------------------------------------------------------------------------------


def test_n33_the_constructor_defaults_for_both_members_are_closed() -> None:
    fields = {f.name: f for f in dataclasses.fields(ServerContext)}
    for name in ("approvals_available", "phone_chat_available"):
        assert fields[name].default() is False  # the stored default is a zero-argument reader
    # No stray qualification field survives the conversion.
    assert "approval_qualified" not in fields


def test_n33_an_unconfigured_context_never_reports_an_open_member() -> None:
    ctx = ServerContext(identity=object(), store=object(), compat=object())  # type: ignore[arg-type]
    assert ctx.is_approvals_available() is False
    assert ctx.is_phone_chat_available() is False
    assert ctx.approval_surface_available("bot_chat") is False
    assert ctx.approval_surface_available("phone_chat") is False


def test_a_member_that_raises_or_returns_a_non_bool_is_closed() -> None:
    def boom() -> bool:
        raise RuntimeError("x")

    ctx = ServerContext(identity=object(), store=object(), compat=object())  # type: ignore[arg-type]
    ctx.approvals_available = boom
    ctx.phone_chat_available = lambda: 1  # type: ignore[assignment,return-value]
    assert ctx.is_approvals_available() is False
    assert ctx.is_phone_chat_available() is False
