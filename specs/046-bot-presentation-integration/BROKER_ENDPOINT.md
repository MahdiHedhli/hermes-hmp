# BR4b held private endpoint snapshot

Status: source-only prerequisite. Independent contract review accepted this scope
before implementation. No service imports it; no endpoint or host is changed.

The owner takes one fixed startup directory and non-root UID. The socket basename
is the literal `presentation.sock`; no phone/request path or name is accepted.
It walks absolute canonical components from an opened `/` using FD-relative
`O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC` opens. Each partial record is retained before
further fallible work. Root and every ancestor FD remain held until local close;
there is no absolute-path reopen after a `resolve()` check.

Ancestors must be directories owned by root or the expected UID. Set-ID bits
refuse. Group/other writable ancestors refuse unless owned by root with sticky
semantics (including the standard root-owned sticky temporary directory). The
endpoint directory must be expected-UID-owned with mode exactly 0700, including
no special bits. The literal endpoint entry is observed relative to that held
FD with no symlink following; type must be socket, UID expected, mode exactly
0600 and link count one. UTF-8 full socket path is bounded to 102 bytes for the
supported POSIX socket path shapes. This is a pathname bound, not a transport.

Held FD identities and each current parent-relative entry must still match.
Socket and lineage are checked again before returning an owner-minted snapshot.
Observed disappearance/replacement/owner/mode/type drift refuses permanently for
that owner, even if later restored. Missing endpoint at initial acquisition has a
separate refusal code and never causes creation or automatic repair. A partial
acquisition exception retains the exact owner for cleanup and diagnosis.

Only exact captured integer FDs and original native identities may be closed.
Close intent precedes the syscall; each known FD is attempted once. Ambiguous
close is retained without retry; EBADF alone is not a close observation. Even a
successful close return must be followed by observation that the owned slot is
closed; a no-op or reuse leaves uncertainty. This is local FD state, never broker
or child closure, and cannot release a registry reservation.

Snapshots are neither peer/code/boot attestation nor reusable authorization.
Before/after pathname observations cannot atomically bind a future connect to
a socket inode. The future connection owner must repeat endpoint checks and join
them with kernel peer expectations and qualified broker boot identity. That
connection/runtime/service qualification, native auth integration and physical
delivery remain separate gates. Same-UID administrator/root remain trusted;
there is no claimed protection from arbitrary concurrent same-process FD
manipulation or hostile kernel/filesystem behavior.

Acceptance includes actual private socket and FD fixtures: ancestor symlink and
replacement during acquisition, retained directory replacement, socket replacement
and sticky refusal after restoration, missing/wrong-type/UID/mode entries, startup
type bounds, partial open, descriptor coercion/reuse, ambiguous/no-op close,
owner-minted observation isolation and primitive/reference guards before any
foreign equality/traversal; held-but-removed directories and preexisting EBADF;
and no creation/connect/unlink/repair by the
helper. Production service/runtime and platform connection qualification do not
follow from these tests.
