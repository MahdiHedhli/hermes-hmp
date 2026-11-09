## November 9 — shared cache-probe lifecycle implemented; image delivery not yet complete

The experimental HMP cache-probe engine now shares the existing admission, native stat/fstat producer, consumption, acknowledgement, caller-held custody and producer-unwound retirement machinery. Directory-consumer ownership stays closed; the probe uses a distinct fixed typed policy. Known missing-file reports contain no exception, errno or filename and are classified only around the literal native stat call. Current lifecycle checks run immediately before each native branch. These are local HMP implementation changes, not a demonstrated upstream Hermes blocker.

At source `d117656`, all 12 selected producer/lifetime/diagnostic checks pass on Python 3.14.9 with unchanged source. At `6755ffe`, all 15 selected shared-ACK interruption, origin-refusal and real missing/directory/declared traversal checks pass with zero failures/errors/skips and unchanged source. The ten interruption cases exercise actual shared ACK stores, preserve the acknowledged original and partial history/cursor without rollback or metered replay, retire raw payloads and close known reserved descriptors. The case formerly called lost-return interrupted immediately before return; it is not evidence of a return-event fault. Test-only successor `eb16eef` adds that separate return-event case. All 16 cases pass on Python 3.14.9 with unchanged source and zero failures/errors/skips. The return-event case does not claim native-call observation from the profiler disabled by its injected exception; independent original ledger/history/count assertions establish no metered replay.

The earlier 22-case directory/resource/cache suite passed on both Python 3.14.9 and 3.11.15 at parent `c981bc2`. Those results do not qualify the later shared producer/consume/ACK changes; the same compatibility selection still needs execution on the latest source. Source successor `9a247bb` adds an exact operation-type fence before resource inspection and a causal foreign-property regression case. Its 23-case existing directory/resource/cache plus shape-check selection is running; no result is claimed yet. Complete diagnostic/type/descriptor/final-seal qualification and actual observe-caller adoption remain open. The prototype is unwired and uninstalled. Full bot-character and host-local image delivery, service/resource bounds and physical/release qualification are not complete. Earlier initial green observer runs that swallowed assertions remain withdrawn; their corrected evidence is described in the historical checkpoints.

Deployment is separate: the recorded LLY520 update runs Hermes 0.23.0 (`0f0e96f`) and HMP `5ecd2ba`, with a graceful restart, verified installed files/listener/TLS, preserved configuration and device controls, and Hermes/Belac/School Bot ready. Lucas/Serenity retain their prior unavailable baseline. ColPanicM2 also has the separately verified HMP safety backport. These host receipts do not prove phone UI or this experimental image candidate. R3 local-media code was installed separately; that does not enable media access or qualify the unfinished character pipeline. No new host/device/grant/provider/model/job/release action occurred during this source/test work. The full roadmap goal remains active.

The following design notes are historical where superseded above; remaining acceptance requirements still apply.

# Original metadata ACK history

This is an isolated engine extension, not an installed character feature or a
completed metadata walker. Source `c82a97a` follows the fixed-source timestamp
policy. Exact execution results belong in FEATURES; finite source review does
not qualify runtime or devices.

The metadata plan retains an original raw-free ACK list. Each fixed consumer
holds that exact list and one actual predecessor commit, not a copied prefix.
The predecessor chain rejoins each original indexed ledger attempt, its actual
acknowledged result and consumer commit, original site and ordinal, registration
and held walk. A matching cursor or reconstructed commit is insufficient.
Exact primitive type/range checks precede equality and indexing. Callback-bearing
material/native closure is followed by another history join.

The current directory ACK path appends its actual commit after clearing native
payload cells and before advancing the original cursor. A failure between those
writes retains a partial ACK/history record and the original failed operation.
It must not restore a healthy cursor, erase history, refund or repeat native IO.
The fixed caller's independent memory custody still handles payload retirement.

One predecessor reference per consumer gives linear retained links. Repeated
full-chain audits can still take quadratic CPU across a file's sites; this is
not a performance qualification or a resolution of the separate floor timeout.

Before enabling leaf-before, leaf-opened, post-EOF and ancestor roles, bind their
actual original predecessors and resources in this shared engine. Source-only
timestamp policy remains conditional on the original source-digest effect.
Keep the walker completion guard closed: zero cursor, no pending consumer and
empty ACK history until the entire real sequence and exact finish proof replace
it together. No generic stat dispatcher or caller-selected policy is introduced.

The bounded tests exercise actual synthetic native returns, retained original
ACKs, copied/missing history, foreign ordinal hooks and interruption after history
append but before cursor advancement. They also preserve the normal caller,
before/after-detach interruption, existing plan and resource checks. Constructed
fixtures prove only their stated scope. Full multi-site history, concurrency,
revocation, remaining operations, runtime/service and physical acceptance remain
required.

## November 9 — literal predecessor return correction

Historical consistency alone did not prove the prior returned receipt: the old
preparation selected its predecessor from the current history list. A coherent
copy in history, prior consumer commit and prior result ACK passed that check;
the isolated causal control reached one leaf stat/ACK while the incomplete
walker still refused completion. Do not treat earlier isolated-mirror tests as
proof against this case.

The fixed caller now carries its literal previous observation return into the
next preparation. Ordinal zero requires None; every later ordinal requires the
exact supplied commit in the original history slot. The same held object is
rejoined after callbacks, consumer construction/publication and latch. Current
mirrors confirm this anchor; they cannot nominate its replacement. No matching
copied tuple or reconstructed chain substitutes for the actual caller return.

Runtime source db91522 and test successor a09eeda pass the four causal cases on
both supported interpreters, unchanged source. Broader regression is pending.
The shared engine now supports only the original directory and leaf-before
roles, with literal no-follow stat for the latter. Same-result timestamp DATA
does not activate source-effect conversion or complete the walker. Actual
leaf-opened/post-EOF/ancestor predecessor and baseline joins remain required.

## Opened-leaf baseline extension

Source72c5e4b retains the repaired literal predecessor handoff for the actual
opened leaf. Before admission, its predecessor must be the original
leaf-before commit for the same held walk and expected declaration. Pending
policy compares the actual new full identity against that immutable earlier
identity, then carries the same actual fstat timestamp separately. Changed
mtime, copied/missing predecessor and lost producer return have focused current
execution coverage; minimum-floor combined regression is pending. This adds no
fullwalker completion, source-timestamp conversion or media authority.

## EOF receipt and post-read accounting

The post-read consumer carries the caller's actual EOF return separately from
its metadata predecessor and original leaf-before baseline. It revalidates the
read's original ACK/consumer/raw-clear/step/count/eof and cache journal where
applicable. Actual EOF is required even for an empty file. Each fixed post-read
row then checks exact attempt index/length and debit distance from that EOF;
the second row also joins the first actual metadata return's same EOF/baseline.
Historical count monotonicity alone is not native work authority. Existing
current-read wrappers retain exact latest-debit and IDLE requirements.

The typed-baseline nested-access control found and source-repaired a zero-hook
refusal gap before any new metadataC. The repaired12 current selection and one actual-empty-EOF control pass across
two runs with byte-identical production source. Combined13 floor qualification
is running. Cache post-read integration, final ancestors and full completion
remain unqualified.
