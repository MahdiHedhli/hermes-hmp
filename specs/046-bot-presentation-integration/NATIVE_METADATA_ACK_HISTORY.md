## November 9 — signed iOS test build ready; entry integration under combined verification

Mobile source `5107b29` / HMP pin `6796bfbb` now produces a **developer-signed iOS release-mode test build 2026110901** through the sanctioned wrapper. Its signature and the preserved private 74-file artifact were independently verified, with tracked source unchanged. It is not installed, physically qualified or released. The build contains device-local bot sections/static icons and readiness guidance; desktop character and host-local image delivery remain unfinished. Device installation and physical acceptance remain pending.

The original minimum-Python regression on repaired `f6f3348` finished **106 passes / two timeouts**, not qualification. Both are close-ACK-loss controls. Controlled test-only comparisons preserve the native C observer, exact loss, full cleanup/accounting assertions and 60-second deadline while omitting a parallel diagnostic stack-dump watchdog: first passes in 47.05 seconds, middle in 46.23 seconds; the latter's saved timing proves all assertions completed at 43.981 seconds. These comparisons support a harness correction, not a proven internal watchdog diagnosis or conversion of the original failed run into a pass. Current Python's earlier 109-case regression remains passing.

Early factory capture preparation `2830810` passes the same **86 controls on both runtimes**. Actual entry/lineage integration `24e1ba5` passes the same **19 controls on both**: retain the actual capture before owner construction, reject coherent copies before publication, preserve foreign slots and refuse lost/reentrant construction replay. This source adds no Scope/native link admission or service. Its broader current run had 21 passes / two failures; the same two older fault tests fail on predecessor `f6`. Test-only `890b0b1` reaches the original post-intent context return instead of replacing a native getter; both corrected controls pass both runtimes, with all prior state/no-I/O/replay assertions retained.

Composed test successor `d093664` keeps production bytes identical to `24e1ba5` and passes **all 131 current-Python checks**, including full unobserved native startup and monitored normal/first/middle cleanup. Its 130-case minimum run is active. Minimum uses full unobserved normal completion plus the same two loss controls; it intentionally excludes the known expensive globally traced normal observer. No minimum result is assumed. Scope blueprint binding, complete native link result/consume/ACK/cleanup, remaining enumeration and service/runtime/device/release gates remain open. No host, permission, configuration, provider/model, job or release change occurred.

## November 9 — repaired startup regression passes; link traversal policy verified

Exact repaired startup source `f6f3348` passes **all 109 current-Python regression cases**, with zero failures, errors or skips and unchanged source. Saved log/XML hashes and the exact case count were checked. This includes the normal cache-read control that failed on predecessor `61cb346`; the predecessor's 108-pass/one-failure result remains historical failed evidence. The broader 108-case minimum-Python run is now active; no result is assumed.

Executable-link traversal policy source `0d5d862` passes the **same 56 DATA controls on Python 3.14.9 and 3.11.15**, with independently checked case sets and artifact hashes. It encodes the full original hop/target before/after/recheck order, identity and byte bounds, foreign-input refusal, and constructor/helper replacement controls. Bounded independent source review accepted this preparation. It is not wired to native effects, admission, ACK or image service delivery. Follow-up `ae0c0ef` moves dependency capture before the first path helper and adds four causal controls; source review accepts that change, but its 60-case execution is pending and no predecessor pass is transferred to it.

The remaining link integration needs an original factory/type origin retained before callbacks. The reviewed concrete anchor is the actual module-load `_ENTRY_ORIGIN` in `gateway_entry.py`, carried as the same original object through native lineage and across outer Scope publication. The entry/lineage extension is not implemented. Early imports widen pre-bootstrap code execution and do not themselves admit native work; package/source/factory gates, full mutable-parent audits, complete link result/consume/ACK/cleanup, remaining enumeration, service/runtime and physical qualification all remain required. Desktop character and host-local image availability is still incomplete. No host, app install, flags, grants, provider/model, job or release changes occurred.

## November 9 — media candidate built; historical startup repair under broader regression

Media candidate `5107b29` pins composed HMP `6796bfbb`. The backend preserves the installed original-worker lifetime and caller-context fixes in both ordinary and media collectors. The same 41 focused and 1,071 combined cases pass on Python 3.14.9 and minimum 3.11.15; source stability, case sets and saved artifact hashes were checked. Paired mobile checks pass: 66 client cases, 73 app cases and both whole-package analyzers. Mobile runtime code remains identical to authoritative `f6795f1`; this pin also carries the reviewed privacy-scanner boundary tests.

The iOS release compile and artifact scan pass for build **2026110901** from exact candidate `5107b29`. A private preserved 67-file artifact matches the build manifest. This build is not developer-signed or installed, and no physical or release acceptance is claimed. Existing readiness guidance is implemented; actual desktop character images and host-local image delivery remain incomplete at runtime.

The earlier 109-case startup regression on `61cb346` remains **108 passes / one normal-read refusal**, not qualification. Targeted diagnosis found that old completed startup receipts incorrectly required the shared ledger to remain idle during a later healthy read. Repair `7d0e455` permits canonical healthy idle/active/pending shapes while preserving exact phase snapshots and failed/torn-state refusal. Exact test successor `ed44874` passes the same 18 controls on both supported Python versions, including the formerly failing normal-read case, type-first foreign-input checks, healthy/torn states and late phase/retirement-marker changes. Independent review accepted the bounded correction. Test-only `f6f3348` names the retirement-marker control accurately; it does not claim literal ACK/link replacement coverage. Its repaired 109-case current regression is running; minimum broader coverage remains pending.

Final synchronous HTTP authority/config latency, schema-4 process quiescence, legacy revision limits, full character byte/service integration, signing and physical Android/iOS qualification remain open. Necessary graceful restarts and relevant LLY520 updates are authorized, but no host, device, grant, flag, model/provider, job or release changes occurred in this checkpoint. The full roadmap goal remains active.

## November 9 — connected regression: 108 passes, one normal-read refusal

Exact native-startup candidate `61cb346` finished **108 passes / 1 failure / 0 errors / 0 skips** in its 109-case current-Python regression. The failure is `test_cache_actor_return_refuses_changed_originals[normal-read]`: the declared-cache reader refuses its normal control with `CacheReadError`. The exact source, log and XML hashes were independently checked. This is not qualification; the minimum broad suite is not started against the known failing candidate. Focused native completion/cleanup passes below remain scoped evidence, and the refusal needs a targeted diagnosis before promotion.

The existing media-readiness frontend `f6795f1` already implements the strict decoder, authenticated API, lifecycle isolation and independent image-gate guidance. It remains authoritative. Candidate `102ce20` adds reviewed privacy tests/status only, leaving mobile runtime code unchanged. Backend composition `6796bfbb` preserves media source `f7f5084` together with the installed actual-worker lifetime and caller-context fixes from `5ecd2ba`. Both media and ordinary collectors retain the original future, budget and drain. Independent source review found no concrete composition regression; the same 41 focused cases pass on Python 3.14.9 and 3.11.15 with unchanged source and checked log/XML hashes. Its 1,071-case combined current suite is running; minimum follows only on success. The mobile backend pin is not advanced yet.

Final synchronous HTTP authority/config latency, schema-4 old-process quiescence, legacy revision limits, packaging and physical acceptance remain open. This composition is not deployed character or host-local image delivery. No host, device, grant, flag, model/provider or release changes occurred.

## November 9 — native startup normal and close-loss checks pass; broad regression running

Exact source `61cb346` passes three focused current-Python cases: monitored full normal completion (42.558 seconds), first lost-close-ACK (13.654 seconds), and middle lost-close-ACK (13.723 seconds). Minimum Python 3.11.15 passes full uninstrumented normal completion (45.840 seconds), plus the same first/middle lost-ACK controls through its focused-trace fallback (45.814 and 45.373 seconds). These are deliberately different normal observer selections, not identical three-case sets. Source footprints match; source stability and log/XML hashes were independently verified. Full uninstrumented normal completion also passed both Python versions on production-equivalent `58d9c35`, as recorded below.

Local-code LINE monitoring on newer Python removes global tracing overhead while retaining real C-close observation, exact pre-ACK loss injection, every cleanup/accounting assertion and the original 60-second deadline. Earlier globally traced normal timeouts remain failures. Independent review found no fidelity regression. The connected-path current-Python regression now runs 109 cases, including the predecessor 100 plus native completion, cleanup, late-parent mutations and foreign-proof checks. Its result is pending; the 108-case minimum selection is prepared but has not started. This is focused source qualification, not a broad regression pass, installed host behavior, actual character/host-local image delivery, device or release qualification. No runtime or permission changes occurred.

## November 9 — full native startup completion passes on both Python versions

Exact source `58d9c35` passes the same uninstrumented full native Entry/cache-fact completion case on Python 3.14.9 (42.607 seconds) and minimum 3.11.15 (42.87 seconds), within the existing 60-second deadline. The test verifies both absence passes, completed literal native finishes, no unknown effects, published entry/cache facts and a cleared active execution slot, with trace/profile absent before and after. Exact source remained unchanged; matching XML case identity and log/XML hashes were independently checked. This is native startup completion, not complete desktop-image delivery, installed host behavior, device or release qualification.

The synthetic globally traced cleanup-normal case still times out and remains failed evidence; these uninstrumented passes do not convert that result into a pass. Test-only source `61cb346` uses local code LINE monitoring on supported Python versions while retaining the actual C-close observer, precise lost-ACK injection, full completion/accounting assertions and the same deadline. Minimum Python retains the focused-trace fallback. Independent source review found no fidelity regression; the three-case execution is in progress and no result is assumed. Two late-parent mutation controls already pass as recorded below.

No hosts, phones, grants, provider settings or releases changed. Device-local sections/static icons retain their separate source status; actual desktop character images and host-local images remain incomplete at runtime.

## November 9 — retained-token correction and guarded consumer validation

The normal-path refusal was traced to historical validation incorrectly requiring all three native preparation cells to be empty. Original open/metadata admission intentionally retains those inputs after IDLE. Source `951ce22` removes that incorrect requirement while preserving exact cell shape, healthy idle state, and identity/value rejoin across observations; independent review accepted the lifecycle correction. Subsequent full normal checks still timed out at the unchanged 60-second deadline and remain failures, not qualification.

Source `45d2948` fuses consumer validation: retain the original weak-reference observations, perform a full mutable-parent audit afterward, then retain the history/resource/consumer checks without publishing a reusable audit token. Standalone validators keep their full audits. Independent source review found no omitted checks. Two full-entry causal tests pass on Python 3.14.9: corrupting an old parent scan's unknown or close-attempt state after observations is refused with no subsequent stat/fstat call and no additional attempt debit. Exact source remained unchanged and log/XML hashes were verified. The normal-completion check is running separately; no normal, minimum-Python, device or release qualification is inferred.

The related explicit cache-pass fixture migration (`c324ff2`) passes all three foreign-input/no-hook checks. Immutable path-inventory validation was narrowed to original factory validation plus active-path/pin checks (`faeba3f`), independently reviewed without removing mutable-parent audits; its normal run still timed out. Desktop character images and host-local image delivery remain incomplete. No host/device/grant/provider or release changes occurred.

## November 9 — native startup caller connected; final validation still failing

The experimental startup driver now connects the actual native cache observer to the shared metadata pipeline and carries literal finishes into effect/pass publication. This is source implementation, not deployed image availability. Candidate `4f5818b` retains full parent-state validation before native effects. A proposed shallow parent witness in `70cbf24` was rejected because it missed mutable nested scan/descriptor state; `e028eb8` removes that optimization. No host deployment used the rejected change.

Focused cleanup verification on exact `4f5818b` finished **2 passes / 1 failure**. Both lost-close-ACK controls pass, including completed traversal before cleanup and no close retry. The normal path closes all seven held descriptors but final validation refuses the result. It remains unqualified; diagnostic work is ongoing without relaxing production checks or the 60-second test deadline. Earlier connected-driver timeouts and the rejected candidate's normal-path failure remain failed evidence.

The predecessor policy/shared-pipeline regression on exact `34f1966` finished **100 passes on Python 3.14.9 and 100 on Python 3.11.15**, with matching case sets and independently checked log/XML hashes. These results do not cover the newly connected native driver. Mobile device-local sections/static icons retain the separately recorded 51-case source result; desktop character images and host-local image delivery are still incomplete and are not claimed available on a phone. No host or device changes occurred in this checkpoint.

## November 9 — shared pipeline corrected; startup ordering implemented, native wiring pending

Source `1898b64` connects the actual fresh-cache observe caller to the shared metadata engine and literal typed finish, preserving the existing ten-field fact. The same twenty actual probe/completion cases pass on Python 3.14.9 and 3.11.15; XML case sets, identical source footprints and log/XML hashes were checked. Source `e66d56a` removes the unused alternative stat helper and passes thirty-six current-interpreter registration, scope, argument, actor and diagnostic cases. These are bounded source results, not complete image or runtime qualification.

Startup cleanup source `31ce4be` repairs a demonstrated close-acknowledgement loss defect: an invalid write to immutable descriptor status could stop remaining reserved closes. The corrected baseline has one normal pass and two intended failures (one or four of seven close calls). The original normal observer timed out and is not qualification; its corrected scope retains full entry/cache-fact completion and the same 60-second deadline. The repair uses the canonical original-allocation refusal marker, continues other known reservations, and never retries the uncertain close. Its three cases pass on current Python and as an explicitly checked subset of the minimum run. Corrupted-allocation marker failure remains outside this bounded correction. The affected files are absent from the last verified installed `5ecd2ba` tree; no host incident is claimed.

The overall thirty-nine-case minimum run finished **37 passes / 2 failures**, not qualification. Both failures were retained-container assertions for base OSError and diagnostic-construction interruption, with all known descriptors closed. An unchanged-production diagnostic reproduces both: the empty container is detached and retired but still referenced by a cached producer-locals dictionary. A test-only injector that targets the same literal statement through the canonical pending/in-flight operation avoids producer frame-local snapshots. Both former failures plus a control pass on Python 3.11.15 with cyclic GC disabled, unchanged hard retirement/cleanup/accounting assertions, no production change, no retry and no deadline increase. This bounded comparison supports correcting the instrumentation; it does not turn the original failed run green. The corrected combined forty-five-case selection now passes on Python 3.11.15 at unchanged source `81676cc`, with zero failures, errors or skips. Source footprints, all 45 XML cases and saved log/XML hashes were checked; the original failed run remains failed.

Source `81676cc` prepares a separate canonical startup-absence resource and a closed origin resolver on the existing shared claim/actor/native/consume/ACK/caller machinery. The default startup origin is None; no factory configures it and the actual startup traversal is not switched. DirectoryConsumer ownership is unchanged. Independent review found and corrected an operation/resource registration mismatch before nested access. Thirteen focused current checks pass at production-equivalent `7ef5679`: four unconfigured-startup gates, two foreign-registration refusals, actual fresh missing traversal, normal Scope construction and five directory-resource checks. At that checkpoint the final change was test-only. The combined forty-five-case minimum suite passes as described above; this does not implement or qualify the still-unconfigured startup policy. The complete next boundary is specified in STARTUP_CACHE_METADATA.md, including original root-open/fstat ordering, both ancestor passes around missing confirmation, literal finishes, effect/pass publication and reserved accounting.

Startup Scope publication source `f17590a` captures the constructor/code, original tuple fields/members/dispatch, constructor inputs, owner dictionary and activation publication cell before allocation, then seals the actual return before publishing/registering it. Independent review identified a missing global guard-identity check; the correction and a fifth zero-foreign-call regression control are committed. Static surface/diff checks pass. The same twelve focused checks, including full startup success and close-loss controls, pass on Python 3.14.9 and 3.11.15 with zero failures, errors or skips. Actual source footprints, XML case sets and log/XML hashes were independently checked on exact `f17590a`. These focused results do not qualify the complete still-unimplemented startup policy. This is one prerequisite, not the complete startup traversal or image feature.

Mobile candidate `56d517c` passes Flutter analysis with no issues and 51 organizer/static-icon model, controller, platform-slot and Home widget cases with no failures or skips (plus four successful test-loader entries). All tracked mobile bytes remained unchanged and were rehashed against the saved log/receipt. These synthetic checks cover local organization and instance isolation, not Desktop character images, physical persistence/accessibility or release acceptance. A separate documentation branch replaces the generated app README with actual development, feature and validation guidance. No app install or device interaction was performed.

The shared producer/consumer/ACK dispatch now lives in the canonical metadata module for the two fixed probe resource types. The initial `9960c9d` selection failed three normal traversals (eight other checks passed); the same three passed on preceding `f17590a`. Independent review identified a stale resource-bridge namespace requirement and late helper-dispatch ordering. Source `1ffea76` repairs both with exact retained helper/code checks and an inline exception only for the three canonical shared wrappers. The intervening `b0af3c4` five-case run also failed and remains failed. The corrected eight-case selection passes on Python 3.14.9 and 3.11.15, including direct traversals, actual observe paths and actual-caller late-helper substitutions with zero foreign calls. Exact source/log/XML and matching case sets were checked. No owner/resource policy or permission was widened.

Source `34f1966` adds the startup-specific branch-ordering policy: root open/fstat; component stat/open/matching fstat; first missing; complete ordered ancestor fstat/stat pass; missing confirmation; second complete ancestor pass; then an absence outcome. Fifty-five policy DATA cases pass on each Python version, including exact action/parent indexes, unsafe ancestors, sticky-root behavior, appearance, changed ancestors, invalid missing sites, Unicode/control input and component/UTF-8 byte limits. Independent review checked the transitions and identified coverage gaps that were corrected. These functions perform no filesystem calls and are not native admission or receipts. The policy is not wired into StartupArtifactOwner; original Scope-time path/type/code binding, actual native returns/FD cleanup, literal finishes and effect/pass publication still require integration. A broader 100-case current regression is running; minimum is queued only after success. No result is claimed for that run.

Earlier evidence stays scoped: producer12 at `d117656`, ACK/origin/real-path15 at `6755ffe`, return-event successor16 at `eb16eef`, parent directory/resource/cache23 current at `9a247bb`, and older22 current/minimum at `c981bc2`. None automatically qualifies a later caller. Initial observer greens that swallowed assertions remain withdrawn. Dated syntax inventories are review aids, not current execution or authority evidence. Full startup shared-metadata adoption, other native operations, factory/service/resource limits, authenticated character/media delivery, physical devices and release acceptance remain open. No upstream capability blocker is established by this local work.

Deployment remains separate: recorded LLY520 Hermes 0.23.0 (`0f0e96f`) / HMP `5ecd2ba` receipts verify graceful restart, files/listener/TLS and preserved configuration/controls. Hermes/Belac/School Bot were ready; Lucas/Serenity retained their prior unavailable baseline. ColPanicM2 has the separately verified HMP safety backport. Those records do not prove this experimental candidate or current phone UI. R3 local-media code was installed separately; media access and complete character delivery do not follow from installation. These changes are uninstalled; bot-character and host-local image delivery remain unfinished. No new host/device/grant/provider/model/job/release action occurred. The full roadmap goal remains active.

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
