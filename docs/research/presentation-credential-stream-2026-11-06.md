# Bounded credential frame digest source checkpoint

Independent read-only source/test review accepted the data-only streaming digest
helper. Root's expanded affected regression passed **658 tests, one skipped**, in
25.79 seconds; configured repository lint passed. The reviewer did not execute
tests or native operations.

`CommittedFrameDigest` first checks the exact bounded HBR1 v2 prefix/header against
its retained commitment and original binding. It then hashes body chunks no
larger than 65,536 bytes, refusing excess total length before progress. It includes
the exact original prefix/header bytes in the digest, rather than hashing a
reconstructed body alone. Finish requires the complete declared body and exact
committed full-frame SHA. It allocates no second full body buffer; this source
property is not a measured RSS or native-memory bound.

The object is confined to its original PID/thread. Initialization and finish are
one-use; failures latch and cannot be repaired by reinitialization, resumed input
or a second finish. Typed retained metadata and hash ownership are checked after
native hash calls before progress or result publication. Returned digest data is
not signature authority, completed transfer, child custody, native release or
permission to publish.

Eighteen new cases cover all seven phase body families, the maximum allowed
RESULT body, different chunk boundaries, exact original-header inclusion,
truncation, body tampering, oversize/foreign chunks, signed wrong-digest/length,
commitment/binding drift without foreign comparison and actual other-thread
refusal. All inputs and keys are synthetic.

The actual authenticated receiver must retain its signature-checked commitment
and feed this helper only from its original controlled cursor. Freely constructed
commitment/digest data grants no authority. Original phase/sequence, native scope,
clock/budget, first cause and custody checks remain mandatory. This helper performs
no IO or signing and does not open the current unsigned-phase refusal. Integration
into the original streaming and direct broker controller/result paths, production
runtime admission, full GO/image publication and physical/release qualification
remain unfinished. No live host or device was changed.
