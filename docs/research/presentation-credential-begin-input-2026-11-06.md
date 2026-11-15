# Two-stage BEGIN/input consistency prerequisite

Independent read-only review accepted the bounded data-only source and tests.
`stage_begin_commitment` checks a fixed gateway-to-broker BEGIN, sequence zero,
closed held context, pinned role signatures and the signed frame claim. Its input
and scope hashes remain UNADOPTED statements until the actual body is validated.
The existing bounded header checker can then check the following HBR1-v2 header
before body allocation. No caller input hash is inserted into held native context.

`check_begin_frame` reverifies the original signed bytes rather than trusting a
caller-constructed staged object. It verifies the entire exact frame, decodes the
bounded input3 packet, independently derives its input/scope hashes from that
same packet and binding, and checks its exact original deadline. It returns only
`ConsistentBeginInput` data. Constructing or receiving that data does not adopt an
input, reserve a registry ticket, read files, authorize a profile or start a child.

Root's final affected regression passed **956 tests, one skipped**, in 27.17
seconds; configured repository-wide Ruff passed. The 58-case phase/stream/scope
subset passed in 0.29 seconds. New tests show signed-but-wrong input/scope hashes,
exact deadline mismatch, open/wrong phase context and correctly signed invalid
input3 refusal. Valid changed profile/challenge/epoch/avatar-operation/name inputs
with a new correct frame/input hash cannot reuse the old scope. One initial
profile fixture failed native input shape before reaching this boundary; fixing
its home, directory chain and exact parent counts reached the intended check.
No production guard was weakened. The reviewer ran no tests or live actions.

Still required: the original broker actor must retain the actual staged record,
channel/task/read cursor and current role generation; independently validate the
full input before registry/resource effects; conserve actual native scope,
deadline/cancellation and completed-transfer evidence. This helper cannot prove
that an actor read bytes or independently authorize any native operation. Full
signed transport/direct-writer/cleanup/native-publication integration and physical
qualification remain open. Existing unsigned phase gates remain closed.
