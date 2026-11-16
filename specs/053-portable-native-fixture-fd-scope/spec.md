# Portable native-fixture descriptor ownership

## Purpose and boundary

The actual native presentation/media journey needs Linux execution while its macOS full journey remains blocked by native database descriptor enumeration. Its existing audit proof uses Darwin F_GETPATH. Introduce a read-only portable helper that verifies an actual writable descriptor still names a singly linked regular file, owned by the current user, under a canonical private owned fixture root. Linux uses its real /proc/self/fd link; unknown platforms and incomplete/changed observations refuse. The helper does not open payloads, chmod, close, repair, grant rights or bypass a native guard.

Before/named/after device+inode, ownership and link checks detect a different-inode descriptor replacement after its kernel path observation; a final access-mode sample also detects a same-inode read-only replacement. The caller must keep exclusive custody of the descriptor and root throughout verification and any later action. The return is sampled metadata, never atomic or durable action authority. Rechecking cannot replace that ownership contract. The fixture admission check is not an OS sandbox against arbitrary same-process native code. It is not yet wired into the native journey, and passing unit tests cannot qualify the complete original matrix.

## Verification and next integration

Real local-kernel tests cover owned writable success without mode/content changes, outside-root and read-only descriptors, hard links, unlinked/closed descriptors, nonprivate/symlink roots and actual dup2 replacements with a different inode or the same inode opened read-only after the kernel path is sampled. A huge exact-integer descriptor is normalized to the same fixed refusal rather than leaking an OverflowError. No platform is faked. macOS tests do not qualify the Linux branch.

An additive standard Ubuntu CI job runs only these bounded synthetic-file tests using existing pinned checkout/setup-uv and frozen server dependencies, read-only repository permissions and no persisted checkout credential. No existing CI job/gate is removed. This job is not a native gateway, provider, device or release acceptance check.

The full portable native runner still requires exact native/HMP source and interpreter/dependency bindings, narrow real Linux proc/kernel metadata observations, an empty credential-bearing environment, fixture network denial, explicit synthetic identity, the complete original two-profile/two-device TLS/media/revocation/natural-cooldown matrix and known/unknown cleanup accounting. No synthetic absence, scan bypass, clock/rate-state patch, forced cleanup, provider/send or live host/device/grant changes are allowed. Linux evidence will not settle the macOS scanner ownership issue.

## Local component evidence

The final13 real-kernel cases pass on Darwin with unchanged helper/test/workflow fingerprints. Before hardening, the same-inode read-only replacement counterexample failed its expected-refusal assertion; after the final flags recheck it passes. The unrepresentable-descriptor case initially escaped as OverflowError and now returns the fixed refusal. A disposable final-source copy with only the inode comparison disabled fails exactly the different-inode replacement case. No shipping code is mutated by that control. These checks do not establish Linux execution, exclusive custody by a future caller, full native gateway integration or macOS scan-thread settlement.
