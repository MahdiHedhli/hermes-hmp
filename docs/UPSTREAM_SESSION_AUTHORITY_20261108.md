# Native session authority source recheck — November 8, 2026

Inspected installed source commit: `ed1afb082eb3e46cf2edae9d8f68fb67b09ee4df`.
This is static source evidence, not latest-release, runtime, transport-access or
physical-device qualification. No installed code, live configuration, grants,
sessions or providers changed; no CLI bootstrap, database or credential read.

## Potential native capability

`gateway/session_contract.py` declares `hermes-gateway-v1` and typed
SessionActor/SessionRef/Submission/AdmissionReceipt/SubscriptionSnapshot contracts.
Submission carries request_id; the protocol includes submit, receipt, attach,
response/control and mutation. `gateway/session_mutations.py` contains branch
handling with control and additional create-capability authorization. This
updates an earlier blanket assumption that a canonical native contract is
absent; it does not establish that all operations are supported through HMP.

## Authorization and side effects remain boundaries

The inspected local route in `gateway/run_api.py` redeems a native transport
ticket and binds its served profile, subject, instance and capabilities before
creating the connection. `gateway/session_controls.py` derives the actor from
that authenticated identity; operator permission is decided by the verified
transport, not granted by arbitrary identity data. Existing HMP pairing, Bot
Chat grants or controls must not be silently converted into native operator,
create, approval or session-control rights. The inspected PluginContext/API
source does not establish a qualified HMP device-to-native actor issuer path.
A future integration needs explicit least-privilege mapping and revocation,
profile/device/generation isolation, negotiation and failure semantics.

`SessionAuthority.attach` subscribes a viewer and changes lifecycle state: it
adds subscribers, removes pending closes, cancels orphan close and permits
session delegation. It is not a passive health/readiness probe. `get_session`
also flushes queued usage writes; `get_messages` remains a separate operation.
The timeline module snapshots its own count/page queries, not the independently
checked HMP bot/session eligibility. Do not copy native SQL or treat these
interfaces as a proven atomic authorization-plus-history read.

## Delivery identity remains unqualified

The inspected legacy `admit_peer_turn` in
`gateway/platforms/api_server_bot_chat.py` generates a fresh UUID delivery key.
The new typed request_id/receipt contract alone does not prove that HMP's
external message ID survives legacy API submission and transcript storage.
No repeated send, transcript edit or matching-text suppression is justified.
The duplicate-history issue remains open until exact request/receipt/transcript
identity and ambiguous-outcome reconciliation are verified end to end.

## Independent existing avatar risk

The same pinned source's `profiles.get_asset` still constructs an asset selector
and uses is_file/read_bytes. This source check does not clear the previously
documented bounded-getter/link/size concern or authorize the separate proposed
native hardening. No getter or asset read was invoked.

Next steps are an authorized native actor/transport contract assessment and
source fixtures before any capability advertisement or live integration. Keep
minimum-version support and actual API/security/host gates distinct; this note
is not a new version allowlist or a reason to switch features off globally.

## Independent source follow-up

BasePlatformAdapter documents a gateway_runner back-reference. This supplies
object access/routing, not a separate device principal or capability grant.
Independent read-only review of that interface, PluginContext, the native
verified-ticket ingress and existing HMP bridge paths did not identify a
qualified HMP pairing-to-native actor issuer. This is a bounded finding, not
proof that no such route exists anywhere in the SDK or that an upstream patch
is necessarily required. Any viable integration still needs a native-owned
trust/delegation contract binding the verified HMP device, instance, profile,
explicit session read/submit intersection, current revocation/served-profile/bot
authority, transport/lifetime and audit cleanup.

The native LOCAL session owner check rejects a different principal unless an
operator capability applies. Native owner_identity distinguishes verified OS
grants and authenticated dashboard sign-in; pairing in HMP does not silently
become a dashboard login. API-peer owner recovery, a copied stored owner or a
dummy login provider is not that delegation contract. Jobs/model controls do
not imply native operator/create/control/approve rights.

SessionAuthority.authorize can restore or mount cold session state and touch
retirement state. Combined with attach subscription/lifecycle changes, this
makes both inappropriate as passive background readiness probes. No such
method was invoked in this source review, and no native grant was created.
