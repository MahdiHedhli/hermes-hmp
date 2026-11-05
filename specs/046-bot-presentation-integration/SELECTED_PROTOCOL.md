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

Encoding and header-first decoding require the selected version. Ordinary v2
channel framing supports BEGIN/READY only. The dedicated retained cleanup sender
and exclusive broker receiver now join private service BEGIN/READY/GO/CANCEL
source; neither is a general CANCEL reader/writer. No competing reader or
terminal owner may reuse the adopted receiver channel. RESULT, STATUS/ACK
and started release remain refused. This is not a deployed capability or an
alternative to complete character delivery. See [coupled transport](INHERITED_CANCEL.md).

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
   end. Inherited transport uses that same budget; no new budget at cancel time.
2. Route every local EOF/timeout/revocation and authenticated inherited window
   through the same minimum. Registry/resource adoption can only shorten the
   earlier frozen end. Unknown clock or delivery retains unknown debt.
3. The [retained cleanup source](REMOTE_CLEANUP.md) now owns work/cleanup tasks,
   a scoped completed-BEGIN fact and one-use CANCEL intent. It transmits only
   after work join under the original frozen cutoff; no replay after ambiguity.
4. Private v2 BEGIN/READY/GO/CANCEL service dispatch now joins both ends. Queue and
   READY checks, original-budget abort/poll and partial-task retention preserve
   raw-auth versus qualified work separation. STATUS/ACK remains closed.
5. Async native GO intent and continuous control ownership are source-implemented
   under [the reviewed contract](ASYNC_GO.md). Complete independently validated RESULT, typed started
   terminal proof, credential retirement, runtime admission, authenticated routes,
   full character rendering and signed physical qualification. Host-local images
   follow character delivery; these requirements are not replaced by framing.

The subsequent [PID-realm source repair](PROC_PID_REALM.md) closes the foreign-
proc-view qualification gap before selected-v2 publication. Its focused clock/
selected convergence passes 106 cases with one Linux-native skip independently
on Python 3.13; actual Linux repair qualification is still separate.
