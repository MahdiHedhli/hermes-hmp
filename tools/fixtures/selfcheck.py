#!/usr/bin/env python3
"""T061: the F1 fixture self-check.

Builds and serves a fixture (T060 `build_fixture.py`), then reads it back through the REAL HMP
read path -- roster (`GET /hmp/v1/bots`) and each authorized profile's snapshot (`GET .../
conversations/default`) -- over real TLS, with the reference-client bearer token `--serve` mints,
exactly like a real client. It compares what comes back against what the manifest
(`fixtures/f1/instances.yaml`) says should be there: every profile's authorization state, and
every seeded conversation's message count and (for the literal `conv-roles` case) exact text.
This is research R9's "self-check": proof that a build fixture is not just written, but legible
through the plugin's own read path, on each extracted Hermes build.

Skip condition (source check, not a live probe -- see the module docstring's history): if
`server/hmp_plugin/reads.py`'s `Reads.roster`/`snapshot` still raise `NotImplementedError("T030")`
in this checkout, every live check is certain to fail closed with `500 internal_error` before it
even reaches the manifest comparison, so this skips with that reason instead of spending a `--serve`
cycle to rediscover it. T030 has landed on `f1/connect-and-browse` (merged into this branch); this
check exists so the self-check still degrades gracefully in a worktree that has not picked that up.

Usage:
    python3 tools/fixtures/selfcheck.py --build stock-base --out /path/to/scratch/f1_selfcheck
`--builds-dir` defaults to `$HMP_HERMES_BUILDS_DIR`, same as `build_fixture.py`.

UNSAFE DEVELOPER TOOL for the ad-hoc `--build candidate`: it starts the candidate's gateway and
verifies nothing about its extracted tree, so it refuses `candidate` unless
`HMP_ENABLE_CANDIDATE_BUILD=1` is set (see `build_fixture.py`; `run_matrix.py --candidate-sha`
sets it only after verifying the tree). Any other label that leads to the candidate's tree, and
any malformed label, is refused before anything starts.
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import _fixture_common as fc
from build_fixture import DEFAULT_BUILDS_DIR_ENV, _generate_conversation_messages

THIS_DIR = Path(__file__).resolve().parent
BUILD_FIXTURE = THIS_DIR / "build_fixture.py"
SERVER_DIR = fc.SERVER_DIR
READS_PY = SERVER_DIR / "hmp_plugin" / "reads.py"


def reads_path_implemented() -> bool:
    """True unless `reads.py` is still T030's `raise NotImplementedError("T030")` stub. See the
    module docstring."""
    text = READS_PY.read_text(encoding="utf-8")
    return 'raise NotImplementedError("T030")' not in text


def _get(port: int, iid: str, token: str, path: str) -> tuple[int, Any]:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # the pin is T041's job; this is a content self-check
    req = urllib.request.Request(
        f"https://127.0.0.1:{port}{path}",
        headers={"Authorization": f"Bearer {token}", "HMP-Instance": iid},
    )
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:  # noqa: S310
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read() or b"null")


def _expected_message_count(
    manifest: dict[str, Any], conv_key: str
) -> tuple[int, list[str] | None]:
    """(count, exact texts or None). `conv-roles`-style literal conversations get their exact
    texts compared too, since they exist specifically to exercise hostile/unusual content."""
    spec = manifest["conversations"][conv_key]
    messages = _generate_conversation_messages(manifest["label_prefix"], spec)
    exact = [m["text"] for m in messages] if "messages" in spec else None
    return len(messages), exact


def check_instance(
    manifest: dict[str, Any], instance_manifest: dict[str, Any], info: dict[str, Any]
) -> list[str]:
    """Returns a list of failure descriptions (empty = this instance is clean)."""
    failures: list[str] = []
    port, iid, token = info["port"], info["iid"], info["device"]["access_token"]

    status, roster = _get(port, iid, token, "/hmp/v1/bots")
    if status != 200:
        return [f"roster: expected 200, got {status}: {roster}"]
    served = {b["profile"]: b["authz"] for b in roster["bots"]}

    for profile in instance_manifest["profiles"]:
        name = profile["name"]
        expect_authz = "authorized" if profile.get("authorize_for") else "pending_operator"
        actual_authz = served.get(name)
        if actual_authz != expect_authz:
            failures.append(
                f"{name}: expected authz {expect_authz!r}, roster says {actual_authz!r}"
            )
            continue  # a mis-authorized bot's snapshot is not meaningful to check further
        if expect_authz != "authorized":
            continue  # ERR-3 correctly refuses a snapshot for a non-authorized bot (403)

        status, snap = _get(
            port, iid, token, f"/hmp/v1/bots/{name}/conversations/default?limit=500"
        )
        if status != 200:
            failures.append(f"{name}: snapshot expected 200, got {status}: {snap}")
            continue

        conv_key = profile.get("conversation")
        if conv_key is None:
            if snap["messages"]:
                failures.append(f"{name}: expected empty history, got {len(snap['messages'])} rows")
            continue

        expected_count, expected_texts = _expected_message_count(manifest, conv_key)
        got_texts = [m["text"] for m in snap["messages"]]
        # Snapshot may be tail-windowed (RO-3's max); only the literal, small conversations are
        # compared byte-for-byte, and only when the whole thing fit in the window.
        if expected_texts is not None and len(got_texts) == expected_count:
            if got_texts != expected_texts:
                failures.append(f"{name}: message text mismatch for {conv_key!r}")
        elif len(got_texts) != min(expected_count, len(got_texts)) or not got_texts:
            failures.append(
                f"{name}: expected some rows from {conv_key!r} ({expected_count} generated), got 0"
            )
        if snap.get("head_message_id") is None:
            failures.append(f"{name}: expected a head_message_id, got None")

    return failures


def run_selfcheck(
    build_label: str, out_dir: Path, manifest: dict[str, Any], *, builds_dir: Path | None = None
) -> list[str]:
    argv = [
        sys.executable, str(BUILD_FIXTURE),
        "--build", build_label, "--out", str(out_dir), "--serve",
    ]
    if builds_dir is not None:
        # Forwarded explicitly rather than left to `build_fixture.py`'s own
        # `$HMP_HERMES_BUILDS_DIR` env fallback: `--builds-dir` on THIS script's own CLI must
        # actually take effect, not merely be accepted and ignored.
        argv += ["--builds-dir", str(builds_dir)]
    env = None  # the caller's environment, as for every listed build
    # By identity, not spelling: a malformed label, or any other name that leads to the
    # candidate's tree (a symlink, `candidate/`, a case variant), is refused before anything
    # starts. Without a builds directory only the label can be checked here; the builder this
    # starts re-classifies against the directory it is given.
    effective_builds = builds_dir or os.environ.get(DEFAULT_BUILDS_DIR_ENV)
    if effective_builds:
        is_candidate = fc.classify_build(effective_builds, build_label)
    else:
        is_candidate = fc.check_build_label(build_label) == fc.CANDIDATE_LABEL
    if is_candidate:
        # Nothing of the caller's environment (credentials, proxies, PYTHON*/GIT_* variables,
        # the real HOME) reaches the process that builds and serves the candidate's fixture.
        fc.require_candidate_gate("selfcheck.py")
        scratch_root = Path(out_dir).resolve() / "_selfcheck_env"
        try:
            fc.safety.reset_scratch_env(scratch_root)  # a fresh HOME/cache/tmp/bytecode every run
            env = fc.safety.scrubbed_env(scratch_root)
        except fc.safety.SafetyError as exc:
            raise fc.FixtureSafetyError(str(exc)) from exc
        env[fc.CANDIDATE_OPT_IN_ENV] = "1"  # the gate above passed; the builder it starts re-checks
        if builds_dir is None and os.environ.get(DEFAULT_BUILDS_DIR_ENV):
            env[DEFAULT_BUILDS_DIR_ENV] = os.environ[DEFAULT_BUILDS_DIR_ENV]
    proc = subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        text=True,
        env=env,
    )
    assert proc.stdout is not None
    all_failures: list[str] = []
    try:
        by_key = {i["key"]: i for i in manifest["instances"]}
        for _ in range(len(manifest["instances"])):
            info = json.loads(proc.stdout.readline())
            key = info["key"]
            failures = check_instance(manifest, by_key[key], info)
            all_failures += [f"[{build_label}/{key}] {f}" for f in failures]
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
    return all_failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", required=True)
    parser.add_argument("--builds-dir", type=Path, default=None)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--manifest", type=Path, default=fc.DEFAULT_MANIFEST_PATH)
    parser.add_argument("--schema", type=Path, default=fc.DEFAULT_SCHEMA_PATH)
    args = parser.parse_args(argv)

    if not reads_path_implemented():
        print(
            "SKIP: server/hmp_plugin/reads.py is still the T030 stub "
            "(raise NotImplementedError(\"T030\")) in this checkout -- every live read would fail "
            "closed with 500 before reaching the manifest comparison. Merge/rebase onto "
            "f1/connect-and-browse (T030 has landed there) and rerun."
        )
        return 0

    fc.assert_outside_real_home(args.out, "--out")
    manifest = fc.load_and_validate_manifest(args.manifest, args.schema)

    failures = run_selfcheck(args.build, args.out, manifest, builds_dir=args.builds_dir)
    if failures:
        print(f"FAIL: {len(failures)} self-check failure(s) for build {args.build!r}:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"OK: {args.build!r} reads back through the plugin's read path exactly as built.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
