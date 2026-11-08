# Fresh cache metadata probe — work in progress

The isolated runtime-cache-probe branch implements an owned original-row metadata
probe using fresh descriptor-relative no-follow traversal. It accepts an actual
continuation and source-row index, not a caller path or expected artifact. Its
counter remains zero because no cache payload bytes are read; original startup
counters are preserved. Actor eligibility precedes attempt consumption, and late
refusal remains inside the sticky failure boundary.

Results are diagnostic missing-component, original-directory or declared-regular
metadata. Exact ENOENT is sampled twice under held ancestors. A directory must
match the original tree directory identity; a declared regular leaf must match
its original receipt identity. Unapproved regular/symlink leaves and structural/
permission errors refuse. None of these outcomes grants cache-read, source-fallback,
code-decode or execution authority. A later fallback consumer still needs persistent
typed syscall outcome/effect provenance and the accepted error categorization;
it cannot infer cache absence from generic CacheProbeError.

Actual result/resource/record allocations are held before final callbacks and
rejoined with the original root/count/selection/path/proof, closed descriptor
allocations, attempt state and vacant fact slots before publication. Native
partial-resource and unknown-cleanup behavior still requires causal qualification.

Bounded independent read-only review accepted the repaired diagnostic-only source.
Eleven causal cases passed on Python 3.14.9 and eleven actual Python 3.11.15
children passed with source hashes unchanged: missing component, appearance,
symlink, counter replacement, original directory, declared regular file, wrong
thread, replay, after-close counter replacement, copied completed fact and late
callback fact replacement. These are bounded diagnostic source checks; the unchanged-source shared
startup regression passed1220 cases in1453.48 seconds on source4f28ac0. No native/device qualification, cache fallback,
live host change or operational factory admission is claimed.

Five additional causal OS/cleanup cases passed on Python 3.14.9 and five actual
Python 3.11.15 children passed with unchanged source: stat permission refusal,
structural ENOTDIR refusal, failed-open uncertainty, fstat refusal after owned
open, and a lost close acknowledgement after the actual close. Failures remain
sticky; known descriptors close, unknown resources retain their state, and no
case authorizes source fallback. These focused checks supplement the 1,220-case
baseline; the later fault cases were not part of that baseline run.
