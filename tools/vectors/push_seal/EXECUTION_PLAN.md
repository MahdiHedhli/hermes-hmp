# Isolated execution preparation plan — NOT ADMITTED

No command below has run. Source/preparation review is the next gate. Installing
any package, importing its code or running crypto requires a new explicit root
admission after review. Separate installation and execution receipts are needed.

## Exact existing runtimes and files

The preparation receipt records Node22.22.3 at the existing local Node executable,
CPython3.14.6 on macOS arm64 at the existing Homebrew interpreter, and executable
SHA256s. Paths are private receipt metadata. No download/update of runtimes.
canonicalize5.1.0 requiresNode>=22; core/common require>=16. PyCryptodome3.23.0's
selected cp37-abi3-macosx_10_9_universal2 wheel is metadata-compatible with
ordinary CPython3.14 arm64; that is not a proved native import/CPU/ABI outcome.
rfc87850.1.4 is py3-none-any,Python>=3.8. No free-threaded Python.

Use a NEW mode0700 private runtime directory, represented as `$VECTOR_RUN` only
in this plan, with `src/`, `node_modules/`, `venv/`, `home/`, `tmp/`. Copy only the
exact independently accepted tools/vectors/push_seal source/data to `src/`; verify
the external freeze, source-pins.json, and artifact hashes before/after preparation.
Do not aim any operation at the current Desktop fixture, a server/app checkout,
owner HOME, account config, native/bootstrap/provider or live key directory.

Node installation after admission: safely extract ONLY the three predownloaded
pinned npm archives into node_modules/@hpke/core,@hpke/common,canonicalize,
stripping the single `package/` prefix. Reject absolute/parent paths, symlinks,
hardlinks/devices/other member types, collisions and size/count beyond the frozen
entry table; create regular0600 files/directories0700; verify the entire exact
file set and per-file digests against dependencies.lock.json. No npm/npx, npm
scripts, network, dev/optional/peer deps or range resolution. Entry package data
has no install lifecycle hooks; canonicalize's published developer scripts are
retained but never invoked. Root must independently review the extraction
method before installation; extraction itself is outside this source slice.

Python installation after admission: create venv with the exact existing Python
(no system-site-packages) in venv/, avoiding owner startup/environment. Use only
selected predownloaded wheels, offline/no build/no compile/no dependencies:
`venv/bin/python -I -m pip --isolated install --no-index --no-deps --no-compile
--only-binary=:all: --require-hashes --find-links <private admitted artifact dir>
-r src/requirements.txt`. This future operation executes trusted pip/venv code
and installs native binaries: separately admitted, never run here. Verify all
Crypto/rfc8785 file hashes before importing; no .pyc or extra package files.
Wheel installation RECORD may change; executable/package source and native
binary entries must match, and installed distribution version metadata must
be independently checked. Do not install extras/dev packages. Avoid build-from-
source fallback. PYCRYPTODOME_DISABLE_GMP=1 prevents optional systemGMP use; other
native/dynamic-loader/runtime libraries still need the admission review.

## Execution environment, containment and lifetime

Root must freeze and independently review a fresh OS containment profile/wrapper
before crypto execution, and validate it on harmless noncrypto canaries under a
new admission. It must deny all network (including loopback/DNS), owner files,
keychains/accounts, devices and process spawning/signalling outside the run;
allow only required exact runtime/shared libraries/system read metadata plus
read-only src/node_modules/venv and writes to isolated out/tmp. No borrowing the
Desktop allow-default signal profile. In-language source checks are not an OS
sandbox. Current slice has no installed profile/canary or containment claim.
A preparation gate must enumerate exact native shared-library/runtime reads and
pin the resulting files/profile/wrapper, avoiding an unbounded HOME/opt read.
No fetch, automatic version resolution, npm cache, pip cache or advisory refresh
is permitted during execution.

Launch with a cleared environment, exactly PATH=<minimal admitted runtime paths>,
HOME=$VECTOR_RUN/home,TMPDIR=$VECTOR_RUN/tmp,LANG=C.UTF-8,LC_ALL=C.UTF-8,TZ=UTC,
PYCRYPTODOME_DISABLE_GMP=1. No NODE_OPTIONS,NODE_PATH,PYTHONPATH,PYTHONHOME,proxy,
provider/Hermes or credential variables. cwd must be `$VECTOR_RUN/src` for both.
Closed preflight rejects other keys. Root records exact executable/library,
source/data/dependency/profile hashes before and after. Package directories must
be immutable for the entire process lifetime; startup hashes alone do not stop
later mutation, replacement/TOCTOU or native loader behavior.

Future generator invocation (under the reviewed OS wrapper): exact Node
`--no-addons src/generate.mjs` (invoke absolute path while cwd src). Its source
must retain the preflight checks and absolute package resolution. No CLI inputs,
key/config hooks, URL input or stdout payload. Future checker invocation:
`venv/bin/python -I -S -B src/check.py` (absolute path,cwd src). Python3.14 sets
venv prefix during path initialization even with-S; see official Python3.14
sys.prefix and command-line docs pinned in the private prep receipt. -I ignores
owner path/environment, -S avoids .pth/sitecustomize before validation, -B avoids
.pyc writes. The checker inserts ONLY verified isolated site-packages after
preflight. This flag combination has not been run or runtime-qualified here.

Bound each future child to60s wall time,256MiB desired address-space/512MiB RSS
observation budget, one child at a time, fixed bounded output logs<=64KiB. macOS
address-space limits are not assumed effective until observed: root must reject
unbounded fallback and document actual enforceable limit. A dedicated parent
owns ONLY its exact child's Popen handle/process group; TERM then bounded KILL/
wait5s on expiry, full reaping; no arbitrary ownerPID/process metadata scans.
Retain error runs privately, never replace with PASS, never extend thresholds
silently. Source emits only fixed failure/success codes; native fatal diagnostics
may bypass those, so log capture is private0600 and raw data is not published.

Generator writes new out/generated.json0600 exclusively (out0700), refuses
existing output; error/partial output is not a vector PASS. Checker writes new
out/checked.json0600 exclusively only after257 official opens and151 exact
reference cases; exports are explicitly unavailable in Python. Root validates
closed bounded receipt input hashes/counts and actual exit status. No native
execution/provider/action follows eligibility.

## Independent evidence and later gates

After the first admitted run, freeze source+packages+profile+runtime+official
input+corpus+both terminal logs/receipts for independent results review. Run
regeneration in two NEW identical isolated runtime directories, independently
check every output first, copy only accepted outputs/receipts into a separate
review folder and compare all nonsignature fields. The comparison source only
reports pending-both-signature-receipts; root must join exact checker receipts.
Do not overwrite the first output or exclude enc/ct/metadata/transcripts.

Then a separate T025 test-source slice can consume immutable corpus through the
actual HMP opaque request signer, and a separate T030 consumer/relay slice can
prove real opener/provider counters, malformed inputs, nonce retention/replay,
atomic clocks/rate limits and fixed errors. Static reference counts here do not
prove those causal production properties. T043 native app sealer/minimum-OS/
production randomness/custody/artifact tests remain unresolved. Existing replay
restart and seal unrevocability residuals remain. No provider/device/deployment,
DesktopT029,A5 or Play conclusion follows from this preparation.
