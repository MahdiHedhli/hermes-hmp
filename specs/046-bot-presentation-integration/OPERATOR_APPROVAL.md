# Fixed operator approval anchor

Status: bounded source implementation and independent review accepted. This
completes PS1-ANCHOR source work, not the startup factory, runtime/import policy,
listener/native/key authority, broker lifecycle or physical image qualification.
No installed gateway configuration, private key or live home was read or changed.

## Root and trust

GatewayApprovalOwner.load(original_entry) takes no caller path, manifest, expected
bytes or qualification callback. It retains the original early entry/activation
and partial owner before native API or file effects. The documented native
hermes_constants.get_default_hermes_root binding selects the default-instance root,
with fixed suffix plugin-data/hmp/presentation/gateway-startup. Root selection
introduces no new environment variable or profile/request-controlled path.

The API module file/spec origin and held function code origin join the original
activation native root. Module/function/code/file/spec origin/loader are captured
before calling the API and rechecked afterward. Changed origins and preloaded
lookalikes refuse before artifact IO. This is native API provenance under the
existing trusted-administrator/runtime premise, not source-byte attestation or a
Hermes commit allowlist. Full loader-policy and actual listener IID/root joins
remain required. Loading never initializes identity or creates files/directories.

The fixed private leaf gateway-approval.json is an operator-installed trust input.
Its observed hash is a retained read fact, not an independent approval of its own
bytes. Keep it outside the entry/recipe inventory hash cycle; no wrapper embeds a
configuration hash that transitively hashes the same wrapper. Candidate generation
and installation approval remain distinct. No automatic installer/activation is
provided by this slice.

## Closed canonical record

The record is 1..4096 bytes, exactly canonical ASCII JSON with sorted keys and
compact separators, no newline, duplicates, missing/unknown keys or alternate
scalar types. Booleans are not integer versions or sizes.

| Field | Accepted value |
| --- | --- |
| schema | Integer 1 |
| kind | HMP_GATEWAY_OPERATOR_APPROVAL |
| selection_schema | Integer 2 |
| selection_size | Integer 1..65536 |
| selection_sha256 | Exactly 64 lowercase hexadecimal characters |
| recipe_schema | Explicit integer 1 or 2 |
| recipe_size | Integer 1..65536 |

Only the fixed sibling gateway-startup.json is derived. No document path, URL,
command, seed, bearer, provider configuration or arbitrary key filename is accepted.
StartupSelectionOwner.load_operator_selection consumes the actual original approval
owner. Recipe loading enforces the original declared variant AND size before
acquisition and in current/retained joins. Explicit D1/D2 paths stay separate;
there is no body-driven detection, fallback or retry. Legacy external expectation
loaders remain DATA-only and cannot manufacture this operator-owner lineage.

## Original IO and lifetime

Descriptor-relative no-follow traversal checks all ancestry ownership/write rules;
the immediate directory is owned by the original UID with mode0700, and the leaf
is regular, single-link, owned by that UID with mode0600. Before/after metadata,
exact EOF, bounded actual reads and known one-close closure remain mandatory.
A failed EOF probe can observe one extra byte; it records that effect and refuses.
Unknown outcomes latch failure and retain original local cleanup debt.

Original read-effect and descriptor allocations are retained before effects and
joined with the original count/fact at publication. Foreign scope/root/count/fact
or ledger replacements are preserved and refused; they are not overwritten or
retried. Only the original accumulation buffer is cleared. Python immutable copies
are not claimed securely erased. Redacted representations/errors expose no path
or raw record. The fixed source has no network or permission-write operation.

Approval bytes and the selection bytes both contribute their actual original
prefix to recipe/package/runtime counters and file limits. The held observed
approval row describes incurred IO; it is never promoted to self-approval.
The recipe's bounded coarse prefix and exact original-parent cap include both.
After the final native activation callback, selection repeats the pure original
approval-parent join before publication. Same-context currentness failure is
permanent; wrong-thread/process queries refuse without retiring the original
owner. No restored root/API or copied receipt resurrects a failed allocation.

## Verification and remaining scope

Focused causal coverage includes private modes/links/ancestor refusal, canonical
schema/type/size/hash fields, missing/oversized input, native API origin/callback
changes, copied roots/facts/counters/read ledgers, unknown read/close, retirement,
late parent replacement, wrong-thread and duplicate/no-retry behavior. Actual
isolated compositions carry both prefixes through complete entry, regular runtime,
leaf-link IO and a scaled exact document-limit success. Wrong recipe variant/size
refuses before any artifact open or recipe owner acquisition.

The final current-interpreter regression passes 849 tests with source hashes
unchanged. A separate driver passed 122 actual Python 3.11.15 child fixtures (74 existing
recipe/plan/link IO, 44 approval and 4 composed cases), with source unchanged.
This is not the full Python 3.11 plugin suite. Neither fixtures nor packaging
qualify installed/native runtime admission. PS1-LOADER,
PS1-LISTENER and PS1-KEYS remain open, followed by separate broker/terminal/ACK/
release/PRE_EMIT and physical acceptance. Approval failure refuses this feature's
admission; it must not stop unrelated gateway features.
