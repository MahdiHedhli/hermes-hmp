# Install and pair

## Requirements

- A current Hermes Agent installation on the host.
- A private network path between the phone and host, such as Tailscale.
- Hermes gateway profile routing configured as described in [Deployment](../server/DEPLOYMENT.md).

On a multi-profile host, read Deployment's topology warning before setting
`gateway.multiplex_profiles: true`. That setting can bypass Hermes's migration
preflight and change API ingress and secret scoping on qualified builds.

Install the plugin from its public repository. For reproducible deployments, add `--ref <full-commit-sha>`.

```sh
hermes plugins install MahdiHedhli/hermes-hmp
hermes hmp compat
```

On the Bot Mode baseline `v2026.8.31`, Hermes validates and warns about the
plugin's `python_dependencies` but does **not** install them. A base Hermes
environment may have `cryptography` but omit `aiohttp` and `qrcode`; HMP then
cannot start its listener or render a pairing offer. Install the requirements
declared in `server/hmp_plugin/plugin.yaml` into the **same Python environment
that runs Hermes**. For a source checkout with a `.venv`, for example:

```sh
HERMES_PYTHON=/absolute/path/to/hermes-agent/.venv/bin/python
uv pip install --python "$HERMES_PYTHON" 'aiohttp>=3.14.3,<4' 'cryptography>=50' 'qrcode>=7.4.2,<9'
```

Do not run that command against an unrelated system Python or the HMP
development venv. Keep your Hermes lockfile and update workflow in mind when
recreating the environment. After installation, restart the gateway and run
`hermes hmp setup check`; it reports missing or out-of-range runtime package
names before checking listener readiness. On other Hermes installations, use their own
environment's package manager to satisfy the same manifest requirements.

Configure profile routing using [Deployment](../server/DEPLOYMENT.md), then
start or restart the Hermes gateway. On a build with the setup check command,
run it before creating a pairing offer:

```sh
hermes hmp setup check
hermes hmp pair offer
```

`setup check` reads HMP's build compatibility, current instance identity, and
TLS-pinned listener readiness without changing files or running another
Hermes command. It reports a served-bot count but cannot prove that every bot
is routed, has a usable profile-scoped API key, or grants this device access.
A nonzero result means Bot Chat is not ready; inspect the gateway and the
deployment checklist. A running listener can still pair a device when only
Hermes read compatibility is missing, but the phone cannot use bots and the
pairing command does not grant bot access or owner controls in that state.
Use `hermes hmp compat` to see the reason, then update to a qualified HMP/Hermes
combination and grant bot access separately. Older HMP releases without this command can still use
`hermes hmp compat` and the checklist.

For Bot Chat sends and the scheduled-job and default-model previews, each
named profile needs its own `API_SERVER_KEY` in that profile's private `.env`.
Use a distinct value of at least 16 characters for each profile; the default
profile's key does not authorize a named profile. Keep each API server bound to
loopback, keep keys out of source control and support logs, and use the
profile's Hermes configuration workflow to set and rotate them. A missing or
unusable key leaves that bot's write controls unavailable; pairing and reads
can still work.

After the gateway starts, run `hermes hmp health check` to inspect every served
bot's enabled send, jobs, and model prerequisites. The command uses a fresh
gateway snapshot and the same pinned listener check as `setup check`. A missing
profile-scoped key or loopback route makes that bot's enabled channels
unavailable and returns a nonzero exit code; intentionally disabled channels
are reported as disabled. The private snapshot contains only status codes, no
keys or endpoints. Recheck after changing profile configuration and restarting
the gateway. This is a prerequisite diagnostic: device authorization and the
outcome of a later request are checked separately by HMP's routes.

Scan the offer in the mobile app, compare the short security code on both screens, and confirm on the host. Then approve only the profiles this device should access. Pairing asks separately whether this phone may manage scheduled jobs and bot default models. Type `GRANT` on the host to allow those controls; any other answer leaves them off. This decision applies to that device only, even when two phones share an HMP user. Keep the offer and approval codes out of logs, screenshots, and support requests.

To change that decision later, use `hermes hmp devices list` on the host to find the active device, then run `hermes hmp devices grant-controls <device-id>` or `hermes hmp devices deny-controls <device-id>`. These commands require an interactive host terminal. Revoking the device also stops its privileged access. Do not put device IDs in support reports.

The plugin belongs to the Hermes instance where it is installed. Do not copy its instance keys or device store between hosts. See [Host hardening](../server/HOST_HARDENING.md) before exposing any Hermes host service.

## Scheduled jobs preview

Scheduled jobs are disabled by default. The host must run an exact Hermes build listed in
`server/hmp_plugin/mobile_cron_supported_builds.json`, with a working profile-scoped
loopback API server and key. Grant the specific phone at pairing or with
`hermes hmp devices grant-controls <device-id>`, then set the HMP gateway platform's
`extra.cron.enabled: true` in private host configuration. Do not commit device IDs or API
server keys to this repository. A new job is always created paused;
review it in the app and choose Resume when ready. A timed-out create may have succeeded,
so refresh the list before creating another job.

For new jobs, the phone defaults to this bot's Bot Chat. Choose “Run history only”
when no chat reply is wanted. Continuity lets each run see this job's previous
output. An existing job's result destination does not change until edited. On
the qualified builds, HMP writes create/edit through Hermes's profile-scoped
cron writer because the profile API does not persist `context_from`. This is
bound to the exact build fingerprint and fails closed after an unqualified
Hermes update.

This preview is qualified only for the listed build bytes. Other builds fail closed.
Installing the plugin does not enable the preview; the operator must grant the device and
enable the cron flag. Existing `extra.owner_device_ids` entries remain a legacy fallback;
an explicit host denial for that device takes precedence.

## Bot default model preview

Model management is disabled by default. The host must run an exact Hermes build listed in
`server/hmp_plugin/mobile_model_supported_builds.json`, with its profile-scoped API server
available locally. Grant the phone at pairing or with
`hermes hmp devices grant-controls <device-id>`, then set
`extra.model_management.enabled: true` in private host configuration. The phone
then offers only models from Hermes's authenticated provider catalog for that bot. A model
change affects new sessions and is never retried automatically; refresh the setting after
an uncertain response. Do not commit device IDs, provider credentials, or API server keys.

The preview fails closed on other Hermes builds. Installing the plugin does not
enable it; the operator must grant the device and enable the model flag. Existing
`extra.owner_device_ids` entries remain a legacy fallback, subject to explicit per-device denial.

## Updating a pinned HMP install

`hermes update` updates Hermes core but does not advance a custom HMP Git-SHA
pin. A pinned plugin's `hermes plugins check-updates` result also does not
compare it with newer HMP revisions. Check the public repository and its
release notes explicitly, keep the current installed SHA for rollback, and
review a candidate commit before reinstalling HMP with `--ref <full-sha>`.
`hermes hmp update check` is a read-only advisory check against the latest
published stable HMP release. It reports the installed and candidate full SHAs,
Git ancestry, and exact Hermes build matches from the release's read, send,
cron, and model compatibility lists. `listed` means the release manifest names
this build; it is not a runtime health result. `unknown` must not be treated as
supported. As of 2026-09-29, no HMP release has been published, so the check
reports that state instead of suggesting `main` as a release.

After reviewing a published release and its commit, save your current SHA and
use `hermes plugins install MahdiHedhli/hermes-hmp --ref <full-sha> --force`
in an isolated Hermes home first. Run `hermes hmp compat`,
`hermes hmp health check`, and a real client send. To roll back, reinstall the
saved full SHA with the same command and recheck those gates. Only then follow
your normal live gateway change process. Requalify after the gateway restarts;
a read-only setup check cannot prove send readiness. This feature is tracked in
[issue #18](https://github.com/MahdiHedhli/hermes-hmp/issues/18).

## Local compatibility tests

Keep source clones of the public Hermes builds in a sibling `_refs/` directory, or pass an explicit path:

```sh
refs_dir="$PWD/../_refs"
builds_dir="/tmp/hmp-builds"
uv run --project server --extra dev python tools/hermes_builds/extract.py --refs-dir "$refs_dir" --out "$builds_dir" --builds stock-base
uv run --project server --extra dev python tools/compat/run_matrix.py --refs-dir "$refs_dir" --builds-dir "$builds_dir" --out /tmp/hmp-matrix --builds stock-base
```

Fixture gateway data belongs in scratch storage outside this repository. Never point tests at your live Hermes home.

### Checking one exact Hermes commit ad hoc

To check a Hermes commit that is not in `tools/hermes_builds/builds.yaml` (for
example a candidate you are about to update to), use `--candidate-sha`. The
tools themselves never edit `builds.yaml` or `read_compat_builds.json`, never
fetch, and never read or update the installed Hermes or `~/.hermes`; the
candidate's own code, once it runs, is not bound by that (see the warning
below). Everything runs from a commit that already exists in your local clone.

> **Run an unreviewed candidate only in an isolated VM, container or user
> account.** Checking a candidate *executes its code*: `uv sync` builds and
> installs the candidate's project and its locked dependencies (build backends
> and `.pth` files run), the extraction imports the candidate, and the self-check
> gateway and the read suite run the candidate's Python. All of it runs as the
> user who started the tools. The safeguards below (a scrubbed environment,
> private scratch directories, refusing paths in your home or `~/.hermes`,
> verifying the source tree against the commit) narrow what an honest mistake
> can touch and catch accidental drift. They are **not a sandbox and not an
> attestation**: candidate code can still read anything that user can read
> (including your real `~/.hermes` and credentials, which it can find through the
> OS account database), use the network, write anywhere that user can write,
> and forge any result these tools record or check after it has run. Use a
> disposable VM or container, or a separate unprivileged user with no access to
> your home, and give it no credentials. That protects **the host**; it does not
> protect these tools from code running as the same user inside it. If you
> cannot isolate the run, do not run the candidate: review its source and
> lockfile first.
>
> **A pass (`candidate_passed: true`) is non-adversarial compatibility evidence
> only.** It means an honest candidate at that commit behaved as expected. It is
> not proof that a hostile candidate was contained or that the result was not
> forged.

```sh
refs_dir="$PWD/../_refs"                 # must contain a hermes-agent/ clone (not a partial clone)
candidate_sha="<full 40-character lowercase hex SHA already present in that clone>"
candidate_interpreter="/usr/bin/python3.14"  # required: absolute path of a base Python outside your home
candidate_python="3.14"                  # optional, "3.MINOR" or "3.MINOR.PATCH"; default "3.11"
builds_dir="$(mktemp -d /tmp/hmp-candidate-builds.XXXXXX)"
scratch="$(mktemp -d /tmp/hmp-candidate-scratch.XXXXXX)"

uv run --project server --extra dev python tools/hermes_builds/extract.py \
  --refs-dir "$refs_dir" --out "$builds_dir" \
  --candidate-sha "$candidate_sha" --candidate-interpreter "$candidate_interpreter" \
  --candidate-python "$candidate_python"

uv run --project server --extra dev python tools/compat/run_matrix.py \
  --refs-dir "$refs_dir" --builds-dir "$builds_dir" --out "$scratch" \
  --candidate-sha "$candidate_sha" --candidate-interpreter "$candidate_interpreter" \
  --candidate-python "$candidate_python" \
  --json-out "$scratch/candidate-report.json"
```

Pass the same `--candidate-sha`, `--candidate-interpreter` and
`--candidate-python` to both tools. The label (`candidate`) and the clone
directory (`$refs_dir/hermes-agent`) are fixed, and `--refs-dir` and
`--candidate-interpreter` are required (`extract.py --skip-venv` needs no
interpreter). Both tools reject an abbreviated, uppercase or named ref, a Python
version other than `3.MINOR` or `3.MINOR.PATCH`, and a combination with
`--builds`. Before anything is created they also refuse a placement that could
reach your real files: an `--out` or `--builds-dir` inside your home (or
containing it), a `--refs-dir` inside `~/.hermes`, a clone whose git directory,
`.git` pointer, `alternates` or `core.worktree` leads into `~/.hermes`, a
partial (blobless/treeless, promisor) clone, an `--out`, `--builds-dir` or
`candidate/`, `candidate/src/` directory that is a symlink, any overlap between
`--out`, `--builds-dir`, `--refs-dir` and this repository, and an unsuitable
`--candidate-interpreter` (see **Interpreter** below). "Your home" is the
account's home directory from the operating system's account database, not
`$HOME`, which candidate processes are given a scratch value for. Use throwaway
directories outside your home, as above; the tools create `--out` and everything
in it as `0700` directories and `0600` files.

Every process the tools start for the candidate (`git`, `uv`, the interpreter
probe, the self-check and its fixture gateway, pytest, SC-007) gets a scrubbed
environment: `HOME`, `HERMES_HOME`, every `XDG_*` directory, `TMPDIR`, the
bytecode prefix and the caches (including uv's) point at private scratch
directories, and nothing is inherited except `PATH`, locale and certificate
settings. Provider keys, proxies, `GIT_*` and `PYTHON*` variables are dropped.
This only changes where well-behaved code looks for its files. It contains
nothing: the candidate's code can still open your real home, including a live
`~/.hermes`, by absolute path, and write outside the scratch directories.
git runs with replace refs, optional locks, fsmonitor, hooks, signature
verification (`log.showSignature=false`, so a `gpg.program` in the clone's config
is never run), every transport (`protocol.allow=never`, and `GIT_ALLOW_PROTOCOL`
set to a name no protocol has, so a `protocol.<name>.allow=always` in the clone's
config cannot re-enable one) and lazy fetching (`GIT_NO_LAZY_FETCH=1`) disabled,
and reads the clone only through object-database commands, so a missing object
is an error, never a fetch.

Each extraction and each matrix run **starts from fresh scratch directories**:
the previous run's `HOME`, caches, `XDG_*` directories, `TMPDIR`, bytecode
prefix and uv cache (under `$builds_dir/candidate` for the extraction and
`$scratch/candidate/env` for the matrix run) are deleted first, so no stale
bytecode or cache is ever consumed. Only those named directories are removed
(symlinks are refused); the extracted source, `--refs-dir`, this repository and
the listed builds are never touched.

The candidate's `PATH` is stricter than a listed build's: besides relative
entries and anything under `~/.hermes`, it drops every directory that holds a
symlink resolving (through any chain) into `~/.hermes`, such as a
`~/.local/bin` containing a `hermes` link, so a bare `hermes` can never reach
your live install. Because that directory may also hold `uv`, the tools find
`uv` first and run it by absolute path; if `uv` cannot be found outside
`~/.hermes`, they stop with instructions to install it. A wrapper script or copy
named `hermes` that is not a symlink is not detected: `PATH` filtering is
hygiene, not a sandbox.

**Interpreter.** The tools never execute a Python from your home, not even to
ask it its version, and they do not search for one: you name it with
`--candidate-interpreter`. Before `uv` or any Python runs, that path is checked
using only `lstat`, `readlink` and `realpath`. It must be absolute; it, every
symlink it passes through and its real path must be outside your home; the real
path must be a regular executable owned by you or root that nobody else can
write, outside `--out`, `--builds-dir`, `--refs-dir` and this repository (a link
planted in one of them is refused however its path is spelled, e.g. through
`/tmp` for `/private/tmp` or a symlinked parent); its directory and that
directory's parent, where Python looks for a `pyvenv.cfg`, must not be writable
by group or others (a sticky bit does not make one acceptable, such as `/tmp`);
and it must be a base interpreter, not a venv's (no `pyvenv.cfg` beside it or
one level up). Only then is it run once (`-I -S`) to confirm its version and that its base
is outside your home, and `uv sync` receives its real path, so uv discovers
nothing. After `uv sync`, and before the venv's interpreter runs, every
`.venv/bin/python*` must resolve to that interpreter (or the base it reported,
checked the same way) and `pyvenv.cfg` must name a `home` (and any other base
path) outside your home. The matrix run re-checks the interpreter and the venv
the same way before it runs the venv's Python. The fixture tools
(`build_fixture.py`, `mutate.py`) also refuse a candidate venv whose
`bin/python*` links or `pyvenv.cfg` lead into your home (they do not know which
interpreter was intended, so they cannot check more). A uv- or pyenv-managed Python
in your home is refused: install a system Python in the VM (for example
`/usr/bin/python3.14`, or one under `/opt`). uv never downloads one.

The extraction writes the candidate's tree from the commit's raw git blobs (not
`git archive`, which applies `.gitattributes` filters) into a `0700` directory
and proves it matches the commit.

The matrix run:

1. verifies the extraction: the metadata names label `candidate`, your exact
   commit, and a passing import check; the clone's git directories are safe;
   **before any candidate Python runs**, the entire extracted tracked source
   matches the commit's file contents, exec bits and symlinks, contains nothing
   else (only a top-level `.venv` and `*.egg-info` metadata are tolerated; any
   other untracked file, including a `.py`, `.pth` or `__pycache__`, fails), and
   has no symlinked directories, hard links or group/other-writable entries;
   only then does it check `--candidate-interpreter` and the venv's
   `bin/python*` and `pyvenv.cfg` (see **Interpreter**, nothing executed), then
   that the interpreter matches the requested version and the one recorded at
   extraction (probed with `python -I -S`, so no `.pth` or `sitecustomize`
   runs), and that the bridge-file fingerprint and `uv.lock` match the commit;
2. runs the fixture self-check and the full read suite for exactly that label
   (read-suite tests are chosen by exact pytest node id, never by `-k`, and are
   parametrized for `candidate` only when `HMP_ENABLE_CANDIDATE_BUILD=1`, which
   only this tool sets; pytest's temporary files go to a private `--basetemp`
   under `$scratch`; zero collected, skipped, errored or failed tests, or any
   collected test the tool cannot parse, fail the run, and so does a self-check
   that only printed `SKIP`);
3. runs SC-007 on copies of just the bridge files (no symlink or `.venv` is
   followed, and a FIFO, device or symlink in place of a bridge file is refused).
   It writes a scratch compatibility list holding one provisional row for the
   candidate's verified fingerprint, and proves that the pristine copy is listed
   and supported and that a copy with one byte changed is refused
   (`hermes_build_unsupported`) before any bridge import. The check imports HMP
   from this repository's `server/` directory under `python -I`, asserts where
   the module came from, and never puts the candidate tree on `sys.path`. The
   committed `read_compat_builds.json` is only read, never edited;
4. **re-verifies after SC-007** (`source_unchanged_after_run`) that the whole
   tracked tree, the bridge-file fingerprint and the lockfile are still exactly
   the commit, by the same checks as step 1. This catches accidental drift: a
   stage that wrote into the tree, a stray edit or process. It cannot catch
   code running as your user that restores what it changed, rewrites the
   metadata, or alters `.venv` (only its `bin/python*` links and `pyvenv.cfg`
   are checked, and only before its interpreter first runs; the installed
   packages are never verified).

Stages stop at the first failure. Exit status is `0` only if `candidate_passed`
is `true`. `--json-out` must be a regular file inside `--out`, in a directory
that is not itself a symlink, not overlapping this repository, the clone, the
builds directory or your home. It is written `0600`: an existing regular file of
yours at that path is replaced, while a symlink, hard link or other file type is
refused. The path is validated before the run and again right before the report
is written (the candidate has been running as your user in between). The JSON
report holds only public-safe fields:

- `generated_at` (UTC), `matrix_runtime` (`os` and `python` as `3.MINOR`),
  and `hmp_source` (`commit`, plugin `version`, and `worktree_dirty`, which is
  `true` when the HMP checkout had uncommitted changes or its state could not
  be read);
- `candidate` (`label`, `commit`, `python_requested`, and the read-bridge
  `fingerprint` once verified);
- `checks`, all booleans: `clone_commit_matches`, `extraction_metadata_valid`,
  `extraction_metadata_commit_matches`, `interpreter_matches`,
  `source_fingerprint_matches`, `selfcheck_passed`, `read_suite_passed`,
  `sc007_passed`, `sc007_bound_to_candidate`, `source_unchanged_after_run`;
- `runtime_dependencies` (installed versions of `aiohttp`, `cryptography` and
  `qrcode`, or `null`; see the limits below);
- `read_suite_tests_run`, `sc007` (`label`, `ran`, `ok`, `status`, `why`,
  `bridge_imported`), `failed_stage`, `candidate_passed`, and `assurance` (the
  fixed statement that a pass is non-adversarial compatibility evidence, not an
  attestation or sandbox).

The report has no paths, environment values, transcripts or log text. Verification,
self-check, read-suite and SC-007 logs stay under `$scratch/candidate/` for you to
read; review them before sharing, since they can contain local paths.

Limits: the checks establish that, when they ran, the extracted tracked tree was
the commit and the tools' own file operations were aimed at the scratch
directories. They do not show that the candidate's processes stayed there: the
scratch `HOME` and `XDG_*` values redirect well-behaved code, they do not stop
code from reading your real home (a live `~/.hermes` included) or writing
elsewhere by absolute path. They do not make running the candidate safe (see
the warning above), they are not an attestation, and they cannot vouch for what
`uv sync` installed into `.venv` (only that the lockfile is the commit's).
Same-user candidate code can defeat them: it can edit or restore files, rewrite
`build-metadata.json` and the scratch logs, or forge the test results the
report is built from. Build backends already run during `uv sync`, before any
check of the installed environment is possible. The isolated VM, container or
user protects your host, not the harness's results from code running as the
same user inside that VM. A candidate whose tracked symlinks
resolve outside its own tree, or whose commit contains a path named `.git` or
`.venv`, is refused rather than extracted. The git alternates chain of the clone
is followed and refused if any entry leads into `~/.hermes`.

The lockfile does not make the fixture step reproducible. It installs
`aiohttp`, `cryptography` and `qrcode` into the candidate's venv from the default
package index, **unpinned and outside `uv.lock`** (with an empty, scratch package
cache), so the isolated environment needs that network access and two runs can
resolve different versions. The report's `runtime_dependencies` records what was
installed (read from the venv's `*.dist-info` names, nothing is executed); the
versions are reported, not pinned.

The tools that build and serve the fixture directly (`build_fixture.py`,
`mutate.py`, `selfcheck.py` with `--build candidate`) are unsafe developer tools:
they execute the candidate and verify nothing about its tree, so they refuse it
unless `HMP_ENABLE_CANDIDATE_BUILD=1` is set. `run_matrix.py --candidate-sha`
sets that only after verifying the tree; setting it by hand is your statement that
you checked the tree yourself, inside an isolated environment. They recognise the
candidate by what `--builds-dir/<label>` leads to, not by how the label is
spelled: a malformed label (`candidate/`, `./candidate`, `Candidate`, anything
that is not one lowercase path component) is refused, and so is any other label
whose directory, `src` or `.venv` is, links to, or was extracted as the
candidate's tree. The candidate is therefore only ever run as exactly
`candidate`, through the opt-in and with the scrubbed environment, never with
your `HOME` or full environment.

This is compatibility evidence for the read path only. It does not run
the send, cron or model suites, does not add the commit to any allowlist, and
does not replace the isolated-home and real-client checks in the update
procedure above. The candidate's `uv.lock` must resolve without private-index
credentials or a proxy, and a base interpreter outside your home must already be
installed and named with `--candidate-interpreter` (uv never downloads one).
Re-extract after any change to the candidate or the interpreter; the matrix
refuses stale metadata (including a different recorded interpreter) rather than
reusing it. Delete `$builds_dir` and `$scratch` when you are done.
