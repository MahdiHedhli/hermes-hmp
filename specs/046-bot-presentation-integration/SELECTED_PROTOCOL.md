# BI1 explicit protocol selection and clock lifecycle

## Reviewed source boundary

Trusted StartupEnrollment now selects protocol_version 1 or 2, with 1 as the
unchanged default. Exact integer validation rejects coercion and unknown values.
Its retained values tuple now has nine fields, including protocol selection;
channel/service and native clock guards migrate together. Frames cannot change
that enrollment or trigger negotiation/fallback.

For selected v2, SocketChannel retains an exact NativeClockOwner allocation before
calling its initializer. Raw channel authentication used by clock construction
never calls qualified framing, avoiding initialization recursion. Framing time
requires completed native qualification on the same channel and calls the
concrete NativeClockOwner.sample implementation, then rechecks the same owner.
A partially initialized or poisoned clock cannot admit frames; mutable instance
sample overrides are not qualification.

Encoding and header-first decoding require the selected version. The bounded
v2 channel model supports BEGIN/READY framing only. v2 CANCEL, GO, RESULT,
STATUS/ACK lifecycle and broker work dispatch remain explicitly refused until
the original-budget and cleanup-owner integration below is complete. This is
not a deployed capability or an alternative to the complete character feature.

The subsequent [exclusive CANCEL receiver](INHERITED_CANCEL.md) now has selected
version2 grammar and bounded semantic budget adoption. Ordinary channel CANCEL
and service v2 dispatch remain refused until its gateway sender and service
retirement are joined. No competing general reader or terminal owner may reuse
an adopted receiver channel.

## Separate local closure facts

SocketChannel.close still observes socket closure only. close_clock separately
requires that socket fact and dispatches the concrete NativeClockOwner.close_local
implementation. Returned socket closure cannot fabricate clock-FD closure, and
an instance method override cannot report it. Partial clock initialization and
ambiguous close remain retained. Broker connection records are removed only
when both local facts are known; neither releases native/registry/process debt.
No code creates a new listener, modifies permissions or changes installed hosts.

## Causal and native evidence

The focused selected/clock/service/terminal model suite passes 141 tests with one
Linux-native skip on Python 3.13 independently. Tests cover exact enrollment,
version mismatch, partial initialization retention, instance overrides, poisoned
clock refusal, separate closure and closed v2 broker work admission. Local model
peer/clock facts are explicitly mocked.

The private exact-owned-helper native test now runs both selected v1 and selected
v2 clock construction on Darwin; it performs no BEGIN/GO or profile work. It
freezes the existing cancellation budget, closes the connection, observes helper
exit and preserves the first cleanup end before local FD retirement. Linux
native case status must be assessed from exact-run evidence, not green totals.

## Coupled work remaining

1. Local original CancellationBudget binding is implemented before native and
   broker resource effects. The remote owner now seals exact selected clock,
   immutable domain values and qualification with the operation and original work
   end. Inherited transport adoption remains open; no new budget at cancel time.
2. Route every local EOF/timeout/revocation and authenticated inherited window
   through the same minimum. Registry/resource adoption can only shorten the
   earlier frozen end. Unknown clock or delivery retains unknown debt.
3. The [retained no-frame cleanup source](REMOTE_CLEANUP.md) now owns work/cleanup
   tasks before effects, retires work, joins its I/O and uses the original frozen
   cleanup end. Remaining: record scoped CANCEL-write intent and transmit only
   after both-end inherited-window integration. No replay after ambiguity.
4. Join v2 grammar, status lifecycle and both transport ends before allowing v2
   broker dispatch. Preserve raw-auth versus qualified work separation and
   retain clock resources until their ownership facts can actually be retired.
5. Complete async native GO intent, independently validated RESULT, typed started
   terminal proof, credential retirement, runtime admission, authenticated routes,
   full character rendering and signed physical qualification. Host-local images
   follow character delivery; these requirements are not replaced by framing.

The subsequent [PID-realm source repair](PROC_PID_REALM.md) closes the foreign-
proc-view qualification gap before selected-v2 publication. Its focused clock/
selected convergence passes 106 cases with one Linux-native skip independently
on Python 3.13; actual Linux repair qualification is still separate.
