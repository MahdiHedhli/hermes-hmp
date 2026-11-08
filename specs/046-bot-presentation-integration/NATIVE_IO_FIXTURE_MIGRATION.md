# Native binding fixture migration — qualification repair

The combined source1ab9910 baseline failed 215 cases and passed 1,065. Multiple
fixtures replaced canonical os.open/readlink aliases even for normal observation;
the new binding continuity check correctly refuses those replacements. The failed
baseline is preserved and does not qualify the integration.

Test-only observers now watch owned HMP helpers or exact native-function c_call
profile events. Native aliases and production checks remain unchanged. Synthetic
post-native/pre-ack fault timing uses a child-only trace on the exact owned helper
code/source boundary; it is not a production callback or verifier bypass.

A trace exception disables later trace events. Independent profiling therefore
retains all native close observations after the injected fault. Duplicate-close
checks use original descriptor-record identity, not numeric fd values, which can
be reused legitimately. Assertions retain exact original total, fd identity,
close-attempt flags, one unknown record and the actual injected fault. Native-open
attempt observations precede effects; successful helper returns are not used as
proof of zero attempts.

Four normal paths and 74 first-migration operator/link checks passed. Independent
read-only review accepted the refined descriptor monitor, but that V2 refinement
is NOT RUN while a separate 144-case residual check remains active. Further
failures still need classification; no blanket fixture-only/full-pass claim is
made. No production implementation, live host/device or permission change.

Validation outputs must use explicit run configuration and a unique private run
directory, with source/test manifest and machine-readable result counts. A copied
filename previously overwrote the raw reader baseline binding; its successful
log and prior in-session binding inspection remain, but the lost original record
is not reconstructed. The failed native-field receipt is retained separately.
