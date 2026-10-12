# Native media TLS smoke check

`native_media_tls_smoke.py` exercises actual native plugin discovery, HMP adapter
components, profile routing, PairingStore grants, SessionDB rows, HMP pairing and
bearer routes, TLS 1.3, and the production Dart SPKI-pinned pool. It verifies one
image descriptor, matching PNG bytes, wrong-pin rejection, and exact HTTP 403 after
native grant revocation.

Run only in a fresh disposable root owned by the current user with mode 0700.
Create `home`, `home/plugins`, and `runtime`; enable only HMP in the private
`home/config.yaml` and expose the reviewed HMP checkout as `home/plugins/hmp`.
Set `HERMES_HOME` and `HERMES_RUNTIME_DIR` before launching the isolated native
interpreter. Do not inherit provider credentials, proxies, or live-host settings.

Arguments, in order:

1. Disposable root.
2. Version-matched native Hermes source checkout.
3. Reviewed HMP checkout.
4. Dart executable.
5. Materialized app package configuration using the reviewed hmp_client source.
6. `tools/fixtures/native_media_pinned_fetch.dart`.

The script invokes the actual registered native image tool against one fixed
loopback provider response, then explicitly appends its returned result through
SessionDB. It creates only synthetic image rows and dummy device keys. Pairing offer
and operator confirmation use the real helper code; request/completion, session
read and binary fetch use HTTP. The Python client validates the certificate
fingerprint; the Dart client validates the production SPKI pin. The token file is
created exclusively with mode 0600 and removed after the child settles. Keep all
remaining diagnostic files private. A timeout remains a failure; child cleanup is
not a bounded process-custody certification.

This smoke check does not run an external image provider, automatic agent-loop
persistence, full adapter startup/shutdown,
Flutter screen, or physical Android/iOS device. Do not treat it as release or
physical feature qualification. The separate producer and Flutter decoder checks
have their own evidence scopes.
