# BI1 Linux proc PID realm qualification

## Finding and scope

Native procfs origin alone does not prove that numeric process paths use the
caller's PID namespace. A proc mount inherited or bind-mounted from an ancestor
PID namespace can map the socket's reported peer PID to a different process.
An original socket peer pidfd being alive prevents reuse of that process in the
caller's namespace; it does not by itself fix a mismatched proc mount realm.

This was found during selected-v2 source integration, before publication of that
integration and with v2 broker work still disabled. No deployed host was probed,
changed or shown affected. It is a source qualification defect, not an observed
host incident. The source repair is independently reviewed with causal tests;
actual Linux kernel evidence for the repair remains separate.

## Self-only realm proof

The observer now retains a native pidfd_open(getpid(), 0) for itself. The caller
cannot disappear/reuse its own PID while running; original PID/UID/thread context
is checked throughout. The native pidfd is retained and validated before opening
fixed `self/fdinfo/<own-fd>` relative to the held real proc root. This does not
read PID1, another user's metadata, credentials, process memory or arbitrary paths.

Kernel pidfd fdinfo prints Pid in the proc mount's PID namespace and NSpid from
that namespace through the target's active namespace. Exactly one NSpid element,
equal to both Pid and current native getpid, establishes the same realm for this
self pidfd. Extra elements refuse even when all numbers happen to coincide.
Missing fields, duplicate fields, signed/noncanonical numbers, extra tokens,
truncation and over-limit output refuse without echoing native metadata.

The read is capped at 2,049 bytes and accepted only up to 2,048, with bounded
fields/lines and a final newline. Native proc/pidfd origin, noninheritable FD
identity, held fdinfo linkage and current ownership are checked around access.
The realm proof runs before the first numeric peer path, each work peer lookup,
and local cleanup clock sampling. The actual socket peer pidfd remains live
before/after peer namespace observation.

Held time namespace descriptors additionally require native NS_GET_NSTYPE to
return CLONE_NEWTIME, alongside actual nsfs origin and matching identities.
Unsupported APIs or permissions refuse; there is no root request, namespace
change, new-kernel version allowlist, PID1 fallback or guessed realm.

## Explicit premises and remaining gates

The proc subtree must be trusted and unmodified by the root/same-UID host
administrator. The checks do not defend against privileged preexisting descendant
bind-overmounts or arbitrary Python/FD tampering. Those remain outside the audited
runtime premise; native fstatfs alone is not a mount-layout attestation.

Every partial acquisition is retained and closed only with the existing native
EBADF observation/no-retry rule. Realm/kind uncertainty permanently poisons local
clock eligibility and never renews cleanup time or releases reservation debt.
The repair is not service-manager, v2 cancellation, GO/result, route or device
qualification. Full character delivery and host-local images remain required.

Primary semantics: [Linux PID namespaces](https://man7.org/linux/man-pages/man7/pid_namespaces.7.html),
[kernel pidfd fdinfo](https://github.com/torvalds/linux/blob/v6.13/fs/pidfs.c),
[namespace type ioctl](https://github.com/torvalds/linux/blob/v6.13/include/uapi/linux/nsfs.h).
