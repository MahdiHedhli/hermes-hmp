# Fixed gateway startup-to-listener composition

Status: next PS1 implementation contract; not implemented, installed or admitted.
This preserves PAIRED_STARTUP_COMPOSITION.md and CREDENTIAL_ADMISSION.md. It is an
HMP-owned integration task, not an established upstream blocker.

## Fixed entry and independent approval anchor

GatewayStartupOwner.start() is called by the fixed installed gateway entry before
native bootstrap or listener creation. No HTTP/request constructor receives this
method. Retain its partial owner before effects and retain the original
GatewayEntryOwner before bootstrap. The fixed entry derives its operator-controlled
installation root from installed startup configuration, never profile/media data.
Do not add a public qualified flag, caller-supplied verifier callback or manifests
to the listener binding interface.

A bounded no-follow private approval-record loader is required first. It must bind
the exact selection size/SHA/schema independently of the inventoried entry/recipe.
Do not put the selection hash inside a wrapper whose hash that selection transitively
pins: this creates circular commitments. Installation-root selection is a trusted
operator action outside network traffic, and must be explicit in the eventual
installer/launcher contract. The record cannot approve its own observed bytes.
Candidate generation remains distinct from operator approval. No installer, live
file, key or activation change is authorized by this source contract.

Run the existing original schema2 selection/recipe/entry/package/runtime-link
owners under the same aggregate accounting. Do not rebuild expectations from
current files, select a new PM generation or reconstruct the original kernel lease.
Retain the actual activation/import observations and required minimum-version/API
eligibility independently of HMP installation integrity; newer Hermes builds are
not denied by a tested-commit allowlist.

## Runtime admission remains an actual implementation prerequisite

Implement the selected platform loader policy against actual interpreter and
activation origins, current loaded modules/extensions, declared reachable roots
and future-import rules. File snapshot success alone cannot satisfy it. Specify
which system loader roots are trusted and how changed/late import origins retire
admission; do not claim hostile same-UID isolation or executed-image attestation.
No synthetic VerifiedInstall or caller Boolean is an admission substitute.
Only the completed independently anchored joins may publish a typed startup
admission. Failed/unknown acquisition permanently retires the original allocation
and preserves original local cleanup ownership.

## Actual listener binding

bind_listener(actual_context) retains a partial original binding before native
callbacks or constructors. Join the actual loop/process/thread, listener generation
and fence, instance, store, bridge, identity and native owner to the admitted startup.
Capture original references and fixed owner methods, recheck after effects and
before publication. Refuse foreign/copied/stale/revoked generations and leave a
replacement intact. Expose no caller-provided current/native_current callbacks.

Only this binding constructs PresentationNativeService with its own retained
methods and passes the actual service explicitly to ParentAuthorityAdapter. The
unbound default remains fail-closed elsewhere. A prepared listener is not a key or
producer admission. Gateway-only role-key acquisition follows the complete startup
joins through existing private descriptor custody; it never creates/replaces keys
from requests. Broker admission, normal terminal/DRAIN, signed ACK and native
credit release remain separate requirements before fresh PRE_EMIT publication.

## Required causal acceptance

- Independent anchor versus same-file-derived/circular approval; missing, wrong
  schema/size/hash, private-mode/ownership/link and changed-root refusal.
- Actual entry and activation continuity; no late bootstrap/reselection or
  reconstructed lease; changed runtime/import/extension/system-loader roots.
- Wrong/copied listener/store/bridge/identity/fence/native owner, wrong loop/thread/
  process/instance, callback-time mutation, retirement and replacement preservation.
- Partial native/service/key construction with retained known/unknown cleanup and
  no retry; no operational authority or image bytes from snapshot-only inputs.
- Full native/broker lifecycle, physical platform and release acceptance remain
  separate. Test success in one stage must not complete those rows.

Independent read-only architecture review identified these concrete prerequisites
on November 7, 2026. The next source task is the approval-anchor/installer selection
contract and loader, followed by actual loader-policy enforcement and listener
binding. Do not collapse them into a generic callback-based factory.
