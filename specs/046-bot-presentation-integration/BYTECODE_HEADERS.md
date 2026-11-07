# Original bytecode header observations

Status: bounded source classification prerequisite; not runtime admission.

The existing artifact hash loop retains up to the first 16 bytes only for declared
.pyc artifacts. The bytes come from the same actual chunks passed to SHA256,
including split reads. No extra reads, descriptors, counters or allowances are
introduced. Non-bytecode receipts retain an empty byte string. Private selection
and operator-approval configuration paths do not retain this header. Receipt
representations stay redacted, and only successful original receipts publish it.

The original entry interpreter observation now retains the actual importlib.util
module and MAGIC_NUMBER bytes allocation. Currentness compares these originals;
no version-to-magic inference or later replacement baseline is used. This is an
observation under the trusted installed-runtime premise, not complete import
machinery qualification.

selected_bytecode_headers accepts only the actual original continuation owner.
It rejoins that continuation and the original interpreter, derives the selected
.pyc records from the original plan and completed receipts, requires a complete
16-byte header and the original magic, and classifies PEP552 flags 0, 1 or 3.
Reserved/unsupported flags, short headers and magic changes refuse. The returned
record retains the original receipt and a redacted representation. It does not
unmarshal or execute bytecode. Timestamp/unchecked-hash/checked-hash formats do
not by themselves prove source equivalence. The final original continuation and
interpreter checks follow the native root callback before publication.

Remaining mandatory work includes which caches a source loader can consume,
exhaustive absence/presence and source/cache joins, actual current plugin and
import machinery, archive/member declarations and bounded reader, extension ABI
and non-system library closure, listener/native/key composition and physical
character delivery. A hashed archive cannot qualify an undeclared member. No
live gateway, key, permission, provider, model or scheduled job changes follow.

Tests use synthetic headers and never execute those bytecode payloads. Actual
artifact fixtures cover split reads, empty/short headers and unchanged aggregate
byte counts; composed fixtures cover original continuation/magic and format
refusals. Independent bounded source review accepted this scope.
