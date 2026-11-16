# Internal observation contract

`parse_group_capabilities(value)` returns frozen `NativeGroupCapabilities` or
raises `InvalidGroupCapabilitiesError` with one fixed content-free message. Input is
already-decoded plain JSON data. No decoder/frame-bound guarantee is added.

Retained DATA: positive protocol integer, exact driver/persistent booleans,
known method names, known feature names, positive local-capped log count.
`advertises(method)` answers known-name membership only; an unrecognized query
raises the same fixed error. It does not imply that the native actor or HMP
caller may use that method. There is no ready/allowed/supported-combined result.

Boundaries: at most64 top-level exact String keys of1..128 characters; validate
keys shallowly before field lookups, without traversing ignored values. At most128 methods,32 features,80 ASCII characters per token; native
protocol and log count fit positive signed32-bit DATA. Unknown bounded tokens are
dropped; duplicate known tokens normalize without changing semantics. Future
extra top-level keys are ignored without traversal. `advertises` validates an exact built-in String before hashing/equality. No raw payload reference is
retained. Method/feature sets are immutable. Driverfalse is preserved.

Caller prerequisite: exclusively own stable decoded built-in containers for the
whole synchronous parse. No concurrent input mutation is supported or fenced
here. Freezing the returned DATA does not establish original-input custody,
transport authority or a bounded JSON decoder/frame.
