# Child entry/package-policy decision — review requested

The controlled processing flow is reviewed source, but the fixed isolated launch
still names a missing presentation_child.py. Do not advertise readiness from the
launch recipe or invoke the gateway package initializer to work around this.

## Proposed implementation

Use a standalone fixed script with an explicit private namespace rooted only at
its own code directory. It imports the statically named presentation processing
modules via relative imports, without sys.path changes, plugin __init__, CLI,
adapter, bridge, identity, native config or provider initialization. No request
chooses a module/code directory. Its bootstrap and exact code-source verification
need focused review; a supplied manifest string is not an attestation.

The child must not derive directory ownership policy from uncharged filesystem
stat calls before the shared ledger starts. Current closed IPC input carries
root/home/profile/UID/GID plus global modes but no qualified ancestor policy.
The current trusted scope-factory seam demonstrates processing; it is not an
actual implementation of policy transfer into an isolated child.

Proposed private IPC schema2 adds directory_policy as one row per lexical root-to-
home prefix, each row [uid,gid,mode]. Paths are derived from the already bounded
home, not repeated in the policy. Root uid/gid remain0; other UIDs must be0 or the
service UID; root/home ownership must exactly match service UID/GID; modes remain
700/750/755 with no group/other write. Maximum32 rows and original8192-byte input
ceiling remain. The parent obtains policy under its already owned/native-authorized
read plane, retaining real work/thread custody. The fixed reader still verifies
named and held descriptors with no-follow semantics before body reads.

The child reconstructs DirectoryRule only from that closed parent-qualified
policy. Local markers, policy rows, source hashes and GO do not grant permission.
Parent native reauthentication, current home binding, owned child identity and
PRE_EMIT remain required. No live route or child launch is authorized by this
proposal itself; existing feature implementation authorization supplies scope,
while independent review supplies the contract gate.

## Decision needed from independent contract review

Confirm or correct the fixed namespace bootstrap and compact policy transfer.
Prefer a suitable existing native primitive if one is actually available; do not
invent one. Review closed schema/version migration, absence fallback, bounds,
parent policy-read ownership and no initializer/credential inheritance. Child
supervisor wait/group/IPC/signal/hard-deadline implementation remains a separate
required task. This decision does not narrow classic/blobatar/custom-image parity.
