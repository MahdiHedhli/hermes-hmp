# Original filesystem encoding for native link traversal

The implementation in `c379255` is an LP3 prerequisite, not a connected native
link driver or image feature. The actual early entry origin retains the original
`str.encode` method descriptor and the interpreter's original filesystem
encoding/error getters and returned settings. It does not nominate a later
`os.fsencode` export or assume UTF-8.

The origin keeps its outer five-field schema. Its environment now has four
fields, its own function table seven, and its exact type table eleven. Existing
plan/policy indices remain unchanged. Both complete primitive Scope mirrors and
the actual entry guard use the updated closed schema. Module rows have fixed
canonical names; current namespace name values must be exact matching strings
before any registry lookup.

`encode_basename` takes the actual retained origin and an exact bounded component
string. It refuses empty, dot, dot-dot, slash, control, DEL and surrogate input.
It checks the held current validator before invoking it, queries the original
C filesystem-setting getters before and after encoding, and calls the captured
string method with the original encoding/error values. The result must be exact
bounded bytes without slash/NUL/dot/dot-dot. Tuple primitives extract retained
origin fields; original constructor/code/default/global/member/dispatch checks
precede construction and follow validation returns. The returned
`_EncodedBasename` retains the actual C-method bytes object, original name and
origin, with a redacted representation.

The actual link driver must obtain this helper from its early origin, check its
original function/code/defaults before invocation, retain the literal return
across resource construction, and bind its bytes to the original policy basename
and actual parent descriptor. Equal/copy DATA cannot establish original return
custody. The helper grants no file access, native debit, ACK, provider connection
or image-service permission. Codec machinery can execute initialization; this is
not a blanket no-I/O or complete factory/runtime attestation claim.

LP3 remains open: integrate every fixed metadata site, distinct typed readlink
result/consumer/commit/ACK, actual byte accounting/raw retirement, complete
before/after/recheck traversal, literal finishes/snapshots/facts and reserved
reverse cleanup. Preserve all original actor/parent audits and no-replay rules.
Remaining native owners/enumeration, factory/service and runtime/device/release
qualification follow separately.

Exact source passes 203 current-Python and 202 selected minimum-Python checks.
All 202 common cases and source footprints match, with unchanged tracked source
and saved log/XML hashes independently verified. Current additionally observes
normal cleanup. The 33 encoding controls include actual C-return byte identity,
Unicode, invalid inputs before any setting query, helper/type/constructor and
namespace-name substitutions, and actual isolated entry/lineage identity with
unchanged native accounting. These are sampled source checks, not Linux-host,
physical Android/iOS, service or release qualification.
