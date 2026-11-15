# Native sender audit experiment — bounded native observation

This experiment investigates kernel sender-at-message identity for the full
character-delivery path. It is not executable-origin, startup or native-policy
authority, and does not qualify a production issuer. All remaining
[runtime issuer](RUNTIME_ISSUER.md) and physical-image requirements stay open.

## First route: failed observation and historical destination uncertainty

The reviewed first registered-port source passed syntax checks and 45 portable
checks. One actual native run then failed: both child sends reported success and
the child exited zero, but the intended receiver accepted zero messages and
returned MACH_RCV_TIMED_OUT (0x10004003). Exact child wait, reported child cleanup,
parent restoration and copied-reference/mapping/own-right releases are recorded
known, with no late settlement. Independent artifact review confirmed those
records; reviewer execution is not claimed.

A destination check was missing: the child used a runtime-managed registered-port
slot without independently establishing that it still denoted the private test
receive right. The two fixed noncomplex test messages' recipient is unverified.
No claim is made that another service accepted or acted on them. They contained
only fixed test fields, no request headers, conversations, profile/file contents,
model/provider data or credentials. LibSystem has XPC fork hooks, but no particular
hook or recipient has been established as the cause. Kernel inheritance alone
was insufficient evidence for the complete userland fork path.

The registered-port route is removed from active source and must not be retried.
Its exact original source and artifacts remain preserved in the private snapshot
`/private/tmp/hermes-native-sender-first-source-20261106` and receipt
`/private/tmp/hermes-native-sender-311-20261106.json`. That receipt separates one
native run from two fake-Popen model receipts. The unresolved historical risk is
`/private/tmp/hermes-native-sender-destination-risk-current-20261106.json`.
A new passing run cannot retroactively establish the earlier recipient.

## Replacement: explicit right assignment to one fresh child

The fixed C helper allocates its own receive right and one send reference, checks
queue capacity for two messages, and snapshots its own SDK EXC_MASK_ALL exception
policy. It uses the public
[posix_spawnattr_setexceptionports_np API](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man3/posix_spawnattr_setexceptionports_np.3.html)
to assign that exact owned right only to a newly created fixed sender child for
EXC_MASK_BREAKPOINT, EXCEPTION_DEFAULT and SDK THREAD_STATE_NONE. No breakpoint is
triggered. No existing process's policy, registered-port table, global bootstrap
name, service-manager job, native home, device, provider or permission is changed.
The parent never writes its own exception policy; its before/after snapshots and
all returned copied references remain separately checked and released.

The spawn target is the same actual executable, in a new private directory,
with fixed arguments and a clean C-locale environment. Only selected OS libSystem
and libbsm dependency identities are admitted; injected startup libraries,
providers and user plugins are absent. Trust in the selected compiler and OS
loader honoring the documented spawn-attribute contract is an explicit fixture
premise, not a full loaded-image/runtime attestation. Child startup consists of
that selected OS runtime and the reviewed fixed C entry; no application/plugin
startup path or ambient gateway fork hook is involved.

Before sending, the child requires its expected parent identity, original bounded
end time, one copied send right and the exact selected mask/behavior/flavor. It
clears the assignment, reads back the cleared mask, and retains the copied right
through its two sends. Destination assurance comes from the exact native spawn
attribute and fixed startup path, not equality of task-local port-name integers
or an exception metadata string. The internal child role is not a public HMP
command, grants API or live gateway deployment route.

## Message origin, body rejection and rights

The child sends two bounded noncomplex messages: one with a false body PID, then
an extended body containing fake audit-trailer bytes. After the exact child wait,
the parent requests kernel audit trailers on its own receive right. It checks the
actual received size and aligned trailer location, format and bounds, then uses
opaque-token library accessors. A payload field or fake trailer cannot replace
kernel sender data. The extended body is refused by the closed diagnostic schema.

The pinned primary-source basis is Apple XNU
`f6217f891ac0bb64f3d375211650a4c1ff8ca1ea`:
[message copyin](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/osfmk/ipc/ipc_kmsg.c)
initializes the sender trailer from the sending task. This is a source finding,
not qualification of a running kernel or accepted HMP operation. Expected child
identity comes from the actual owned spawn and wait, separately from token data.
PID version is observed identity data; it does not attest code or current liveness.

Unexpected complex/remote/voucher rights in a successfully received kernel message
are passed to the documented message destructor before time-based refusal. The
[library implementation](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/libsyscall/mach/mach_msg.c)
disposes message-carried rights rather than the borrowed local receive right.
Because this destructor returns void, the record states only that disposal was
attempted; any unexpected message or unknown copyout permanently fails cleanup
qualification. Releasing the receive port alone is not used as disposal of rights
already copied into a received message.

## Deadlines and retained settlement

Only the fresh helper's local signal defaults change, never the gateway's reaper
or handlers. Exact-child WNOHANG waiting uses the original work/cleanup end times.
ECHILD or other uncertainty retires numeric-PID signal permission permanently.
The child alarm is a secondary bound; no parent hard alarm can orphan the child.
After expiry, an unresolved owner remains alive in settlement-only exact waiting:
no renewed work, message send/receive, allowance or successful late cleanup.

The Python controller retains the same Popen before constructor effects and
continues settlement observation after a timeout or wait error instead of exiting
while the helper may still own a child. External interruption or an unreturning
OS syscall is not claimed safely bounded. The closed result schema distinguishes
resource disposal from timely cleanup; late or settlement-only outcomes cannot
become success. This remains a fixture contract, not HMP hard-wall-clock proof.

## Current verification and remaining feature gates

Replacement C syntax checks (C11, Wall/Wextra/Werror), repository-configured Ruff
and privacy scanning pass. Independent source review accepted one fresh
fixture-only native run. Root then observed 57 passing checks in 0.94 seconds:
56 portable schema/library/timeout-model checks and one actual Darwin run.
The receiver obtained both messages after the exact child exited; kernel sender
identity matched that owned child, the false body PID was ignored, and the
extended fake-trailer body was refused. Recorded cleanup was known and timely,
with no unexpected message, late cleanup or settlement-only outcome.

Selected source/compiler/SDK/binary and dependency metadata are preserved with
the private receipt `/private/tmp/hermes-character-native-sender-current-20261106.json`.
Its manifest separates one native receipt from two fake-Popen model receipts;
the latter are not native runs. Independent artifact review matched executable/
test bindings, all 20 artifact hashes/sizes/modes, compiler/binary/SDK hashes and
all six terminal commands. No reviewer execution is claimed.
The earlier failed route and its unknown historical recipient remain separate
and unresolved. Linux CI skips cannot stand in for native Darwin observations.

Original gateway/listener identity provenance, production runtime/manager trust,
per-operation authorization, terminal/ACK integration, PRE_EMIT/DRAIN and credential
retirement, authenticated routes and signed physical image parity remain open.
No test flag, nonce, expected PID, version or digest becomes permission. The
Hermes minimum-version/best-effort policy is unchanged. Full desktop characters
and host-local chat images remain required and unfinished on phones.
