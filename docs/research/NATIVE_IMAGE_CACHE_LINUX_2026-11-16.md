# Fresh native Linux image-cache qualification — November16

Status: all three complete synthetic native Linux scenarios passed in
[run43857621548](https://github.com/MahdiHedhli/hermes-hmp/actions/runs/43857621548),
exact harness583e39886c61aed471a8159934ff309502226cef. Artifact/report/source
readback and independent bounded runtime review are accepted. No host update,
physical device acceptance or release is claimed.
The older b86/run43827844022 result remains valid only for its old183a inputs.

## Exact inputs and scope

HMP a4a157a5d04a20f23dddc6d614d462b758a947f4 contributes1,021 regular Git files;
unchanged native ed1afb082eb3e46cf2edae9d8f68fb67b09ee4df contributes12,185 selected
source files. The complete13,206-file canonical source manifest has SHA256
28f13dcb4a90fce810bc0cf8aecb35b33584f5095e5e427a1887637135bcc702. The new HMP
hashes are derived from exact Git blobs with object readback, not an installed
package list. Its project metadata, all77 frozen dependencies, binary hashes,
container image and FD helper remain unchanged.

Both original matrix and mutation scenarios retain their assertions, complete
lifecycle and natural602-second reapproval wait. A third, separately attributable
historic scenario runs the same full two-profile/two-device/TLS/authorization/
isolation/regrant/mutation/cleanup journey. It seeds only each fresh scratch
profile's image_cache, then uses the actual pinned native cache_image_from_bytes
under the original profile scope. It checks helper source origin, rejects a cache
constant override, and requires the returned exact profile path and PNG bytes.
Its committed image_generate tool rows are synthetic fixture data, not provider
image generation. The original two scenarios still use save_b64_image.

The75-minute outer job limit accommodates the additional full scenario, not a
shortened wait or cleanup proof. Overdue actors retain the same identity and are
observed without kill, replay or replacement. Existing network-none/non-root/
read-only mounts/resource limits, ownership/settlement checks and source/runtime
readback remain. Only four extra fixed historic report paths join the encrypted
evidence allowlist; no new key, recipient, raw upload or host data is involved.

## Pre-dispatch evidence and open gates

124 component/source/DATA tests pass across six selected files. They test the
three report shapes and historic-only requirements, reject provider-generation
claims and duplicate profile evidence, bind actual actor bytes, and check both
preparation source counts against the pinned inventory. An earlier pytest-root
collection failure was corrected in the invocation, not by disabling tests. The
source audit also caught two stale13,201 count checks before any actor ran; the
new count regression covers both. Independent review accepts one fresh synthetic
experiment, with a separate additive correction recording the exact canonical
manifest serialization. Neither source tests nor data-only report fixtures are
runtime/Linux observations.

## Terminal runtime evidence

All three independent actors (matrix, mutation, historic) completed, exited0 with
PID0 and no OOM. Reports match their recorded SHA256 values. Artifact14224206279
has4,712,760 bytes and SHA256
7f70226bb46e48bbe0fe978766ba20c296f6f1cad7d01c32b1890570e4ec8f01.
The source manifest matches the exact golden bytes above; the CPython3.14.9
runtime manifest binds10,664 entries. Reviewed controller checks verify source
and runtime before and after each actor; archived software trees were not
independently re-executed during readback.

Both original scenarios and the historic scenario observed authenticated TLS
image bytes, two profiles/two synthetic devices, isolation, revocation/regrant,
metadata/avatar revision checks, and natural waits of602.001997,602.002007 and
602.002356seconds respectively. Historic evidence confirms both exact native
image_cache profile roots and PNG bytes via the original helper. Canonical tool
rows remain synthetic; this does not qualify live provider generation.

Independent review verifies908 network-isolated container observations. All917
captured Docker command stdout/stderr hashes match their receipts. Adapter,
loader and event-loop cleanup checks pass. The status writer was idle but its
daemon still alive before whole-process exit; do not claim all threads joined
before exit. This result does not resolve old canceled-run cleanup or the Mac
scanner's unknown worker lifetime. Private-union/Mac runtime, live host/phone
rendering, physical startup and release acceptance remain unqualified.
