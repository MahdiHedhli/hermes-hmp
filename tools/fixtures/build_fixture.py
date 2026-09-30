#!/usr/bin/env python3
"""T060: the F1 fixture builder.

Builds the two isolated Hermes instances (`A`, `B`) `fixtures/f1/instances.yaml` describes, on one
extracted Hermes build (T004; `tools/hermes_builds/extract.py`), per
`specs/001-connect-and-browse/contracts/fixture-format.md`:

  - one isolated `HERMES_HOME` per instance, under `--out`, never inside the real user home
    (rule 1; `_fixture_common.assert_instance_paths_safe`);
  - profiles created with the build's own `hermes profile create` CLI (rule 2);
  - HMP users and chat bindings written through the HMP plugin's own `store.py`, offline
    (rule 2/3), and per-bot (P6) authorization approved through the real Hermes
    `hermes -p <profile> pairing approve hmp <request_id>` CLI (rule 2);
  - messages written through the target build's own `SessionDB`/`SessionStore` APIs, offline
    (rule 3);
  - every seeded message text labelled with the manifest's `label_prefix`, `continuity_evidence`
    stays `false` (enforced by `tools/fixtures/manifest.py`, run first, always).

`--serve` additionally starts every instance's real HMP listener (aiohttp + TLS, `server/
hmp_plugin/server.py`, T024), pairs one throwaway reference device per instance through the real
`hermes hmp pair confirm` (T032, run under a pty so its TTY gate passes -- see
`fixture_pairing_cli.py`), and prints one JSON line per instance to stdout as each comes up:
`{"key", "port", "iid", "device": {"device_id", "user_ref", "access_token", "refresh_token",
"access_expires_at"}}` -- the reference-client state `server/tests/integration/
test_reads_fixture.py` reads immediately, and then blocks (serving) until it is asked to stop
(SIGTERM/SIGINT). It also writes the run descriptor `mobile/packages/hmp_client/test/fixture/
fixture_server_test.dart` documents (`<out>/run_descriptor.json`), so the Dart real-server tests
can drive their OWN P1-P4 pairing through `offer`/`confirm`/`deny`.

`--serve` on an `--out` that was already built reuses it (profiles, users, seeded history and any
`mutate.py` changes survive); pass `--force` to wipe and rebuild an instance from scratch.

Usage:
    python3 tools/fixtures/build_fixture.py --build stock-base --out /path/to/scratch/f1_fixtures
    python3 tools/fixtures/build_fixture.py --build stock-base --out ... --serve

`--builds-dir` defaults to `$HMP_HERMES_BUILDS_DIR` (same default `tools/ci/check_all.sh` uses:
`${TMPDIR:-/tmp}/hermes_bot_mobile_hermes_builds`), a T004 `extract.py --out` directory.

UNSAFE DEVELOPER TOOL for the ad-hoc `--build candidate`: this (like `mutate.py` and
`selfcheck.py`) executes the candidate's Python and verifies nothing about its extracted tree.
It refuses `--build candidate` unless `HMP_ENABLE_CANDIDATE_BUILD=1` is set, which
`tools/compat/run_matrix.py --candidate-sha` does only after proving the tree is exactly the
requested commit; setting it by hand is your statement that you checked the tree yourself,
inside an isolated VM, container or user account. Scrubbing the environment is not a sandbox:
the candidate's code can still read the real home (a live `~/.hermes` included) by absolute path.
The candidate is recognised by what `--builds-dir/<label>` leads to, not by spelling: a malformed
label (`candidate/`, `./candidate`, `Candidate`) or any other label whose tree is the candidate's
(a symlink or renamed copy) is refused, so the gate and scrubbed environment always apply.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import _fixture_common as fc

THIS_DIR = Path(__file__).resolve().parent
FIXTURE_SEED = THIS_DIR / "fixture_seed.py"
FIXTURE_PAIRING_CLI = THIS_DIR / "fixture_pairing_cli.py"
HERMES_BUILDS_DIR_TOOL = fc.REPO_ROOT / "tools" / "hermes_builds"
DEFAULT_CONVERSATION_ID = "default"
DEFAULT_BUILDS_DIR_ENV = "HMP_HERMES_BUILDS_DIR"
_MAX_CANDIDATE_METADATA_BYTES = 1 << 20


def fixture_plugin_dir(out_dir: Path) -> Path:
    """A scratch COPY of `server/hmp_plugin`, under `--out`, that fixture instances symlink into
    instead of the tracked package directly. `bootstrap_compat_entry` patches only this copy's
    `read_compat_builds.json` -- the committed one (`server/hmp_plugin/read_compat_builds.json`)
    is never touched. `server/tests/unit/test_compat.py::
    test_load_the_committed_read_compat_builds_json` asserts that file's `builds` list is empty
    (T013's untouched skeleton, pending T063/T064); mutating it would be a global, persistent side
    effect on a tracked file every other worker and CI run also reads, breaking that assertion for
    everyone, not just this fixture run."""
    return Path(out_dir).resolve() / "_hmp_plugin"


def refresh_fixture_plugin_copy(out_dir: Path) -> Path:
    """(Re)copy `server/hmp_plugin` into `fixture_plugin_dir(out_dir)`, always fresh (so a local
    code change is picked up), preserving nothing from a previous copy except what
    `bootstrap_compat_entry` re-derives afterwards."""
    dest = fixture_plugin_dir(out_dir)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(fc.SERVER_DIR / "hmp_plugin", dest)
    return dest


def _resolve_source_sha(build_label: str, build_dir: Path | None = None) -> str | None:
    """The extraction's commit (fixture-format.md rule 8: "provenance only"), read the same
    read-only way `tools/hermes_builds/extract.py` (T004) does: no fetch, no working-tree touch.
    Returns `None` if it cannot be determined -- `source_sha` is optional.

    The ad-hoc `candidate` build is not in builds.yaml; its commit is what its own extraction
    recorded in `<build_dir>/build-metadata.json` (only trusted if it names the `candidate`
    label and a full 40-hex commit). A metadata file that is a symlink, FIFO or other non-regular
    file, or is oversized, is refused with `FixtureSafetyError` (never followed or waited on); a
    missing or malformed one just yields `None`. Provenance only: same-user code can rewrite it."""
    if str(HERMES_BUILDS_DIR_TOOL) not in sys.path:
        sys.path.insert(0, str(HERMES_BUILDS_DIR_TOOL))
    import extract as extract_mod

    if build_label == extract_mod.CANDIDATE_LABEL:
        if build_dir is None:
            return None
        try:
            raw = fc.safety.read_regular_file(
                build_dir / extract_mod.METADATA_NAME, _MAX_CANDIDATE_METADATA_BYTES
            )
        except fc.safety.SafetyError as exc:
            raise fc.FixtureSafetyError(f"candidate metadata: {exc}") from exc
        if raw is None:
            return None
        try:
            meta = json.loads(raw.decode("utf-8"))
            commit = meta["commit"]
        except (UnicodeDecodeError, ValueError, KeyError, TypeError):
            return None
        if meta.get("label") != build_label or not isinstance(commit, str):
            return None
        return commit if extract_mod.FULL_SHA_RE.fullmatch(commit) else None

    try:
        builds = extract_mod.load_builds()
        refs_dir = extract_mod.find_refs_dir(HERMES_BUILDS_DIR_TOOL)
    except SystemExit:
        return None
    for b in builds:
        if b.label == build_label:
            return extract_mod.ref_resolves(refs_dir / b.clone, b.ref)
    return None


def bootstrap_compat_entry(build: fc.BuildInfo, plugin_copy_dir: Path) -> None:
    """T023's compat gate (`server/hmp_plugin/compat.py`) refuses Hermes-dependent routes until a
    build is listed in `read_compat_builds.json` -- by design (GU-2c): an unlisted build must
    never serve reads. The bridge-independent pairing amendment permits P1-P5 and self-revoke
    without that entry, but `selfcheck.py` (T061) and the read fixture suite (T030) still need
    qualified Bot Chat reads. A fingerprint-only entry is therefore bootstrapped for THIS
    extracted build in a scratch copy only; it does not qualify any production build.

    Patches ONLY `plugin_copy_dir`'s `read_compat_builds.json` (`refresh_fixture_plugin_copy`'s
    scratch copy fixture instances actually import -- never the tracked
    `server/hmp_plugin/read_compat_builds.json`; see `fixture_plugin_dir`'s docstring for why).
    The fingerprint itself is a property of the HERMES install (`bridge_files` under
    `hermes_root`), not of wherever `hmp_plugin` is imported from, so computing it via
    `fixture_seed.py compat-identity` (which still runs against the TRACKED `hmp_plugin` -- byte-
    identical code, just not the file this function writes to) yields the exact same value
    `compat.default_gate()` will see when it runs against the copy.

    Only if that exact fingerprint is not already listed in the copy's file, ADDS one fingerprint-
    only entry (`git_sha: null` -- git-archive extractions have no `.git`, matching rule 8's
    "fingerprint-only entries"). It never removes or edits an existing entry, and never marks a
    build "supported" without checking its real, current fingerprint first. This is a bootstrap
    for test tooling, clearly labelled as such in `qualified_by`; a real T063 run against the
    tracked package is unaffected by anything this function does.
    """
    identity = json.loads(fc.run_seed_script(build, FIXTURE_SEED, "compat-identity").stdout)
    fingerprint = identity["fingerprint"]
    if fingerprint is None:
        raise fc.FixtureSafetyError(
            f"build {build.label!r}: could not compute a read-bridge fingerprint at all "
            "(a listed bridge file is missing from this extraction) -- cannot bootstrap"
        )
    compat_path = plugin_copy_dir / "read_compat_builds.json"
    data = json.loads(compat_path.read_text(encoding="utf-8"))
    for entry in data.get("builds", []):
        if entry.get("fingerprint") == fingerprint and entry.get("git_sha") is None:
            return  # already listed (a prior bootstrap run against this same copy)
    data.setdefault("builds", []).append(
        {
            "fingerprint": fingerprint,
            "git_sha": None,
            "label": f"fixture-bootstrap-{build.label}",
            "qualified_by": "tools/fixtures/build_fixture.py (T060 bootstrap pending T063/T064)",
            "qualified_at": datetime.now(UTC).isoformat(),
            "source_sha": _resolve_source_sha(build.label, build.src_dir.parent),
        }
    )
    compat_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _deterministic_user_id(instance_key: str, user_key: str) -> str:
    """Stable across rebuilds: `mutate.py`/`selfcheck.py` recompute the same id without needing a
    separate persisted mapping file. `server/hmp_plugin/cli.py`'s `USER_ID_RE` requires exactly
    32 lowercase hex chars after `hmpu_` (the same shape `_cmd_confirm` mints with
    `crypto.random_bytes(16).hex()`), so a short digest prefix is rejected by the real CLI."""
    digest = hashlib.sha256(f"{instance_key}:{user_key}".encode()).hexdigest()
    return f"hmpu_{digest[:32]}"


def chat_id_for(instance_key: str, profile_name: str) -> str:
    return f"fixture-chat-{instance_key}-{profile_name}"


def _generate_conversation_messages(
    label_prefix: str, spec: dict[str, Any]
) -> list[dict[str, str]]:
    """Manifest `conversations.<key>`: either literal `messages` (used verbatim -- the manifest
    already label-prefixes every text) or `generate: {count, roles}` (synthesized here, every
    text label-prefixed per the builder's own obligation, contracts/fixture-format.md)."""
    if "messages" in spec:
        return [{"role": m["role"], "text": m["text"]} for m in spec["messages"]]
    gen = spec["generate"]
    roles: list[str] = gen["roles"]
    count: int = gen["count"]
    return [
        {
            "role": roles[i % len(roles)],
            "text": f"{label_prefix} generated message {i} ({roles[i % len(roles)]})",
        }
        for i in range(count)
    ]


def _write_messages_file(messages: list[dict[str, str]], tmp_dir: Path, name: str) -> Path:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    path = tmp_dir / f"{name}.json"
    path.write_text(json.dumps(messages), encoding="utf-8")
    return path


def _write_config_yaml(
    paths: fc.InstancePaths, profile_names: tuple[str, ...] = (), *, port: int | None = None
) -> None:
    """`plugins.enabled: [hmp]` alone makes `Platform("hmp")` resolve once plugin discovery has
    run (needed even for offline seeding: `fixture_seed.py`'s `seed-messages`/`new-session`/
    `append` construct a `SessionSource(platform=Platform("hmp"), ...)`). The
    `gateway.platforms.hmp` block additionally starts the real listener, so it is only written
    once a `port` is known (`--serve`).

    `gateway.profile_routes`: HMP's read bridge (`bridge.py`'s `_source`) builds each source with
    `scope_id=guild_id=<profile>`, exactly like an inbound platform message from that "location",
    and asks Hermes's OWN route matcher (`gateway/profile_routing.py`) whether that resolves back
    to the same profile -- if it does not (`gateway.config.Platform.build_source`'s
    `.profile != <profile>`), `authz_state` reports `NOT_ROUTED` before it ever checks
    authorization (`bridge.py`'s `authz_state`), even for a correctly P6-authorized user. Without
    an explicit route, a Hermes install has none by default. One `platform: hmp, guild_id:
    <profile>, profile: <profile>` route per profile (`bot_profile` left unset: HMP is a root-
    level adapter, so routes apply against the default profile's "bot", which is exactly right)
    is what makes every fixture profile routable at all -- this is a Hermes gateway-config
    requirement the fixture builder itself must satisfy, not something `server/hmp_plugin` could
    default on its own (see this task's final report).

    Hand-written, not through `yaml.safe_dump`: profile names are `^f1-[a-z0-9-]+$` (SCHEMA.json)
    and `port`/`bind` are ours, so this is a small, fixed, safely-interpolated shape, avoiding a
    PyYAML dependency this script otherwise has no need for.
    """
    lines = ['plugins:\n', '  enabled: ["hmp"]\n', "gateway:\n", "  multiplex_profiles: true\n"]
    if profile_names:
        lines.append("  profile_routes:\n")
        for name in profile_names:
            lines += [
                f'    - name: "{name}-route"\n',
                '      platform: "hmp"\n',
                f'      profile: "{name}"\n',
                f'      guild_id: "{name}"\n',
            ]
    if port is not None:
        lines += [
            "  platforms:\n",
            "    hmp:\n",
            "      enabled: true\n",
            "      extra:\n",
            '        bind: "127.0.0.1"\n',
            f"        port: {port}\n",
        ]
    (paths.home / "config.yaml").write_text("".join(lines), encoding="utf-8")


def _install_plugin_symlink(paths: fc.InstancePaths, plugin_dir: Path) -> None:
    """Symlinks to `plugin_dir` (`fixture_plugin_dir(out_dir)`, a scratch copy -- never
    `server/hmp_plugin` directly; see that function's docstring)."""
    plugins_dir = paths.home / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)
    link = plugins_dir / "hmp"
    target = plugin_dir.resolve()
    if link.is_symlink() or link.exists():
        if link.resolve() == target:
            return
        link.unlink()
    link.symlink_to(target)


def build_instance(
    build: fc.BuildInfo,
    paths: fc.InstancePaths,
    manifest: dict[str, Any],
    instance: dict[str, Any],
    plugin_dir: Path,
    *,
    force: bool,
) -> dict[str, Any]:
    fc.assert_instance_paths_safe(paths)
    if paths.home.exists() or paths.xdg_state.exists():
        if not force:
            raise fc.FixtureSafetyError(
                f"{paths.home} already exists; pass --force to rebuild it from scratch"
            )
        shutil.rmtree(paths.home, ignore_errors=True)
        shutil.rmtree(paths.xdg_state, ignore_errors=True)
    paths.home.mkdir(parents=True, exist_ok=True)
    paths.xdg_state.mkdir(parents=True, exist_ok=True)

    label_prefix = manifest["label_prefix"]
    instance_key = instance["key"]
    conversations = manifest.get("conversations") or {}

    # 0. Enable the plugin (needed even offline: `Platform("hmp")` only resolves once plugin
    # discovery has seen it enabled), route every profile (see `_write_config_yaml`'s docstring)
    # and install the plugin into this isolated home.
    profile_names = tuple(p["name"] for p in instance["profiles"])
    _write_config_yaml(paths, profile_names, port=None)
    _install_plugin_symlink(paths, plugin_dir)

    # 1. Profiles, via the build's own `hermes profile create` CLI (rule 2). Each named profile
    # ALSO needs its own `gateway.multiplex_profiles: true`: `gateway/session_recovery.py`'s
    # `_resolve_profile_for_key` (which decides a session key's `agent:<profile>` namespace) reads
    # `self.config.multiplex_profiles` off whatever `load_gateway_config()` sees for the CURRENT
    # `HERMES_HOME` scope -- and `fixture_seed.py`'s message seeding runs scoped to the PROFILE's
    # own home (`set_hermes_home_override`), which has its own, separate config.yaml. Without
    # this, seeded sessions land under the `agent:main` namespace while `bridge.py`'s read path
    # (which calls `gateway.session.build_session_key(source, profile=profile)` directly, with no
    # config dependency at all) looks them up under `agent:<profile>` -- a namespace mismatch that
    # makes every snapshot/history read come back empty despite real, correctly-authorized rows.
    for profile in instance["profiles"]:
        fc.run_hermes_cli(
            build, paths, "profile", "create", profile["name"], "--no-alias", "--no-skills"
        )
        (paths.home / "profiles" / profile["name"] / "config.yaml").write_text(
            "gateway:\n  multiplex_profiles: true\n", encoding="utf-8"
        )

    # 2. HMP users, through the plugin's own store (rule 2), offline.
    fc.ensure_plugin_data_dir(paths)
    user_ids: dict[str, str] = {}
    for user in instance["users"]:
        user_key = user["key"]
        user_id = _deterministic_user_id(instance_key, user_key)
        user_ids[user_key] = user_id
        fc.run_seed_script(
            build,
            FIXTURE_SEED,
            "insert-user",
            "--home", str(paths.home),
            "--xdg-state", str(paths.xdg_state),
            "--user-id", user_id,
            "--label", f"{instance_key}:{user_key}",
        )

    # 3. Per profile: chat binding + P6 authorization (rule 2) + seeded history (rule 3).
    tmp_dir = paths.out_dir / "tmp" / instance_key
    profiles_meta: list[dict[str, Any]] = []
    for profile in instance["profiles"]:
        name = profile["name"]
        authorize_for: list[str] = profile.get("authorize_for") or []
        conv_key = profile.get("conversation")
        entry: dict[str, Any] = {
            "name": name,
            "authorized": bool(authorize_for),
            "has_history": conv_key is not None,
        }
        if authorize_for:
            # F1 fixtures authorize exactly one user per profile (contracts/fixture-format.md's
            # own example manifest never lists more than one); the first key is that user.
            user_key = authorize_for[0]
            user_id = user_ids[user_key]
            chat_id = chat_id_for(instance_key, name)
            entry["user_id"] = user_id
            entry["chat_id"] = chat_id
            fc.run_seed_script(
                build,
                FIXTURE_SEED,
                "set-chat",
                "--home", str(paths.home),
                "--xdg-state", str(paths.xdg_state),
                "--user-id", user_id,
                "--profile", name,
                "--chat-id", chat_id,
            )
            gen = fc.run_seed_script(
                build,
                FIXTURE_SEED,
                "p6-generate",
                "--home", str(paths.home),
                "--profile", name,
                "--user-id", user_id,
                "--label", f"{fc.manifest_mod.CS22_OPERATOR_LABEL_PREFIX}{instance_key}-{name}",
            )
            request_id = json.loads(gen.stdout)["request_id"]
            fc.run_hermes_cli(
                build, paths, "-p", name, "pairing", "approve", "hmp", request_id
            )
            if conv_key is not None:
                messages = _generate_conversation_messages(label_prefix, conversations[conv_key])
                messages_file = _write_messages_file(messages, tmp_dir, f"{name}-{conv_key}")
                seeded = fc.run_seed_script(
                    build,
                    FIXTURE_SEED,
                    "seed-messages",
                    "--home", str(paths.home),
                    "--profile", name,
                    "--user-id", user_id,
                    "--chat-id", chat_id,
                    "--messages-file", str(messages_file),
                )
                entry["session_id"] = json.loads(seeded.stdout)["session_id"]

        # Amendment A1 (session browsing, OD-F9/OD-F10): non-HMP sessions of this SAME bot, from
        # other sources (Desktop, CLI, cron, ...), so `list_sessions_rich` has more than one
        # source to list. These are independent of the HMP chat/authorize steps above -- OD-F10's
        # whole point is that bot-level authorization is what gates them, not a per-session grant.
        other_sessions = profile.get("other_sessions") or []
        seeded_other_ids: list[str] = []
        for other in other_sessions:
            other_id = f"{instance_key}-{name}-{other['session_id']}"
            other_messages_file = None
            conv = other.get("conversation")
            if conv is not None:
                other_messages = _generate_conversation_messages(label_prefix, conversations[conv])
                other_messages_file = _write_messages_file(
                    other_messages, tmp_dir, f"{name}-{other['session_id']}"
                )
            parent = other.get("parent_session_id")
            fc.run_seed_script(
                build,
                FIXTURE_SEED,
                "seed-session",
                "--home", str(paths.home),
                "--profile", name,
                "--session-id", other_id,
                "--source", other["source"],
                *(["--title", other["title"]] if other.get("title") is not None else []),
                *(["--messages-file", str(other_messages_file)] if other_messages_file else []),
                *(["--archived"] if other.get("archived") else []),
                *(["--hidden"] if other.get("hidden") else []),
                *(
                    ["--parent-session-id", f"{instance_key}-{name}-{parent}"]
                    if parent is not None
                    else []
                ),
                *(["--end-reason", other["end_reason"]] if other.get("end_reason") else []),
            )
            seeded_other_ids.append(other_id)
        if seeded_other_ids:
            entry["other_session_ids"] = seeded_other_ids
        profiles_meta.append(entry)

    return {
        "key": instance_key,
        "home": str(paths.home),
        "xdg_state": str(paths.xdg_state),
        "profiles": profiles_meta,
    }


def build_instance_if_needed(
    build: fc.BuildInfo,
    paths: fc.InstancePaths,
    manifest: dict[str, Any],
    instance: dict[str, Any],
    plugin_dir: Path,
    *,
    force: bool,
) -> dict[str, Any]:
    """`--serve` on an existing `--out` reuses it (profiles, seeded history and any `mutate.py`
    change survive a restart) instead of rebuilding -- `server/tests/integration/
    test_reads_fixture.py`'s `test_new_session_is_session_replaced_across_restart` depends on
    exactly this. A prior build's `fixture_meta.json` entry, if any, is reused so callers that
    never rebuilt still get a `profiles_meta` back."""
    if paths.home.exists() and not force:
        existing = read_fixture_meta(paths.out_dir)
        for inst in existing.get("instances", []):
            if inst["key"] == instance["key"]:
                return inst
        # Home exists (e.g. from a differently-scoped prior run) but no meta recorded -- rebuild
        # is the only way to know what is really there.
    return build_instance(build, paths, manifest, instance, plugin_dir, force=force)


class _GatewayHandle:
    def __init__(self, key: str, process: subprocess.Popen[bytes], log_path: Path) -> None:
        self.key = key
        self.process = process
        self.log_path = log_path


def _wait_for_port(port: int, *, timeout: float) -> bool:
    import socket

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            try:
                s.connect(("127.0.0.1", port))
            except OSError:
                time.sleep(0.5)
                continue
            return True
    return False


def _pick(profiles_meta: list[dict[str, Any]], *, authorized: bool) -> str | None:
    for p in profiles_meta:
        if p["authorized"] == authorized and (not authorized or p.get("has_history")):
            return p["name"]
    if authorized:
        for p in profiles_meta:
            if p["authorized"]:
                return p["name"]
    return None


def serve_instances(
    build: fc.BuildInfo,
    out_dir: Path,
    manifest: dict[str, Any],
    built: list[dict[str, Any]],
    plugin_dir: Path,
) -> None:
    fc.ensure_runtime_deps(build)
    handles: list[_GatewayHandle] = []
    instances_desc: list[dict[str, Any]] = []
    out_dir = Path(out_dir).resolve()
    log_dir = out_dir / "gateway_logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    def cleanup(*_: object) -> None:
        for h in handles:
            if h.process.poll() is None:
                h.process.terminate()
        deadline = time.monotonic() + 10
        for h in handles:
            remaining = max(0.0, deadline - time.monotonic())
            try:
                h.process.wait(timeout=remaining)
            except Exception:
                h.process.kill()

    signal.signal(signal.SIGINT, lambda signum, frame: (cleanup(), sys.exit(130)))
    signal.signal(signal.SIGTERM, lambda signum, frame: (cleanup(), sys.exit(143)))

    try:
        for inst in built:
            key = inst["key"]
            paths = fc.instance_paths(out_dir, key)
            fc.assert_instance_paths_safe(paths)
            port = fc.find_free_port()
            profile_names = tuple(p["name"] for p in inst["profiles"])
            _write_config_yaml(paths, profile_names, port=port)
            _install_plugin_symlink(paths, plugin_dir)
            fc.ensure_plugin_data_dir(paths)

            hermes_bin = build.venv_python.parent / "hermes"
            env = fc.clean_hermes_env(
                extra={"HERMES_HOME": str(paths.home), "XDG_STATE_HOME": str(paths.xdg_state)}
            )
            log_path = log_dir / f"{key}.log"
            log_file = log_path.open("w", encoding="utf-8")
            proc = subprocess.Popen(
                [str(hermes_bin), "gateway", "run", "--force"],
                env=env,
                stdout=log_file,
                stderr=subprocess.STDOUT,
            )
            handles.append(_GatewayHandle(key, proc, log_path))

            if not _wait_for_port(port, timeout=45.0):
                tail = log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
                raise RuntimeError(
                    f"instance {key!r}: HMP listener on port {port} did not come up within 45s.\n"
                    f"Log tail:\n{tail}"
                )

            profiles_meta = inst["profiles"]
            authorized_profile = _pick(profiles_meta, authorized=True)
            pending_profile = _pick(profiles_meta, authorized=False)
            authorized_user_id = next(
                (p["user_id"] for p in profiles_meta if p.get("user_id")), None
            )
            endpoint = f"https://127.0.0.1:{port}"
            common = ["--home", str(paths.home), "--xdg-state", str(paths.xdg_state)]
            instances_desc.append(
                {
                    "key": key,
                    "endpoint": endpoint,
                    "offer_cmd": [
                        str(build.venv_python), str(FIXTURE_PAIRING_CLI), "offer",
                        *common, "--endpoint", endpoint,
                        "--user", authorized_user_id or "",
                        "--label", "fixture-offer",
                    ],
                    "confirm_cmd": [
                        str(build.venv_python), str(FIXTURE_PAIRING_CLI), "confirm",
                        *common, "--sas", "{sas}", "--sas-group", "{sas_group}",
                        "--label", "{label}", "--user", authorized_user_id or "",
                    ],
                    "deny_cmd": [
                        str(build.venv_python), str(FIXTURE_PAIRING_CLI), "deny",
                        *common, "--sas", "{sas}", "--sas-group", "{sas_group}",
                    ],
                    "authorized_profile": authorized_profile,
                    "pending_profile": pending_profile,
                }
            )

            # A ready-to-use reference-client bearer token per instance
            # (server/tests/integration/test_reads_fixture.py's interface), paired through the
            # REAL operator CLI now that the gateway has created the instance identity.
            if authorized_user_id is not None:
                ref = subprocess.run(
                    [
                        str(build.venv_python), str(FIXTURE_PAIRING_CLI), "pair-reference-client",
                        *common, "--endpoint", endpoint,
                        "--user", authorized_user_id, "--label", "fixture-reference-client",
                    ],
                    env=fc.clean_hermes_env(),
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )
                if ref.returncode != 0:
                    raise RuntimeError(
                        f"instance {key!r}: pair-reference-client failed:\n"
                        f"stdout: {ref.stdout}\nstderr: {ref.stderr}"
                    )
                ref_info = json.loads(ref.stdout)
                print(
                    json.dumps(
                        {
                            "key": key,
                            "port": port,
                            "iid": ref_info["iid"],
                            "device": ref_info["device"],
                        }
                    ),
                    flush=True,
                )

        descriptor = {"format": 1, "build": build.label, "instances": instances_desc}
        descriptor_path = out_dir / "run_descriptor.json"
        descriptor_path.write_text(json.dumps(descriptor, indent=2), encoding="utf-8")
        print(f"HMP_F1_FIXTURE_RUN={descriptor_path}", file=sys.stderr, flush=True)
        print(
            "Fixture gateways are running. Press Ctrl-C to stop them.",
            file=sys.stderr, flush=True,
        )
        signal.pause()
    finally:
        cleanup()


def fixture_meta_path(out_dir: Path) -> Path:
    return Path(out_dir).resolve() / "fixture_meta.json"


def read_fixture_meta(out_dir: Path) -> dict[str, Any]:
    path = fixture_meta_path(out_dir)
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def write_fixture_meta(out_dir: Path, build: fc.BuildInfo, built: list[dict[str, Any]]) -> None:
    """Persist what `mutate.py` (T062) needs to find a profile's session and re-invoke tooling
    under the SAME build without repeating `--build`/`--builds-dir` (`server/tests/integration/
    test_reads_fixture.py`'s `mutate.py --out <dir> --instance <key> --mutation <name>` interface
    takes neither). Merges over any existing file so a partial rebuild (`--instances A`) does not
    lose a sibling instance's entry."""
    path = fixture_meta_path(out_dir)
    existing: dict[str, Any] = {}
    if path.exists():
        with path.open(encoding="utf-8") as fh:
            existing = json.load(fh)
    instances = {i["key"]: i for i in existing.get("instances", [])}
    for inst in built:
        instances[inst["key"]] = inst
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "build": {
                    "label": build.label,
                    "src_dir": str(build.src_dir),
                    "venv_python": str(build.venv_python),
                },
                "instances": list(instances.values()),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def build_info_from_meta(meta: dict[str, Any]) -> fc.BuildInfo:
    """The build a fixture was made from, re-resolved (`fc.resolve_build`) from the recorded
    `<builds_dir>/<label>/src`, so a re-entering tool (`mutate.py`) applies the same label and
    candidate-identity rules as the builder: the record must be exactly that shape for its label,
    and a listed label whose tree is the candidate's is refused. For the candidate, the caller
    must have enabled isolation first (`resolve_build` refuses otherwise)."""
    b = meta["build"]
    label = fc.check_build_label(b.get("label"))
    src_dir = Path(str(b.get("src_dir", "")))
    if (
        not src_dir.is_absolute()
        or src_dir.name != "src"
        or src_dir.parent.name != label
        or Path(str(b.get("venv_python", ""))) != src_dir / ".venv" / "bin" / "python3"
    ):
        raise fc.FixtureSafetyError(
            f"refusing: fixture_meta.json's build record is not <builds-dir>/{label}/src with its "
            "own .venv/bin/python3; rebuild the fixture with build_fixture.py"
        )
    return fc.resolve_build(src_dir.parent.parent, label)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--build", required=True, help="build label from tools/hermes_builds/builds.yaml"
    )
    parser.add_argument(
        "--builds-dir", type=Path, default=None,
        help=f"T004 extract.py --out directory (default: ${DEFAULT_BUILDS_DIR_ENV})",
    )
    parser.add_argument(
        "--out", required=True, type=Path, help="scratch output directory for this fixture build"
    )
    parser.add_argument("--manifest", type=Path, default=fc.DEFAULT_MANIFEST_PATH)
    parser.add_argument("--schema", type=Path, default=fc.DEFAULT_SCHEMA_PATH)
    parser.add_argument(
        "--instances", default=None, help="comma-separated instance keys (default: all)"
    )
    parser.add_argument(
        "--serve", action="store_true",
        help="also start every listener, pair a reference client and write the run descriptor",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="wipe and rebuild an instance home that already exists",
    )
    args = parser.parse_args(argv)

    builds_dir = args.builds_dir or os.environ.get(DEFAULT_BUILDS_DIR_ENV)
    if not builds_dir:
        parser.error(f"--builds-dir is required (or set ${DEFAULT_BUILDS_DIR_ENV})")

    fc.assert_outside_real_home(args.out, "--out")
    # By identity, not spelling: a malformed label, or any other name that leads to the
    # candidate's tree (a symlink, `candidate/`, a case variant), is refused here.
    if fc.classify_build(builds_dir, args.build):
        # The ad-hoc candidate's code runs in everything below (`hermes`, the seed scripts, the
        # gateway, `uv pip`): scrub the environment and make every file private, whoever
        # launched this process and with whatever environment. Refused unless the explicit
        # opt-in is set; this is the entry point that builds, so it starts from a fresh scratch
        # environment (no stale bytecode, caches or HOME).
        fc.enable_candidate_isolation(args.out, fresh=True)

    manifest = fc.load_and_validate_manifest(args.manifest, args.schema)
    build = fc.resolve_build(builds_dir, args.build)
    # Even the offline build touches `hmp_plugin.server` (for `store_path`), which imports
    # `aiohttp` at module scope; `--serve` additionally needs it to actually listen.
    fc.ensure_runtime_deps(build)
    plugin_dir = refresh_fixture_plugin_copy(args.out)
    bootstrap_compat_entry(build, plugin_dir)

    wanted = set(args.instances.split(",")) if args.instances else None
    built: list[dict[str, Any]] = []
    for instance in manifest["instances"]:
        if wanted and instance["key"] not in wanted:
            continue
        paths = fc.instance_paths(args.out, instance["key"])
        print(f"==> instance {instance['key']!r} ({build.label}) at {paths.home}", file=sys.stderr)
        built.append(
            build_instance_if_needed(build, paths, manifest, instance, plugin_dir, force=args.force)
        )

    write_fixture_meta(args.out, build, built)

    if not args.serve:
        print(json.dumps({"ok": True, "build": build.label, "instances": built}, indent=2))
        return 0

    serve_instances(build, args.out, manifest, built, plugin_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
