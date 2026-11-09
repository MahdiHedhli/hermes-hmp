# Native SDK source declaration checks — November 9, 2026

Test-only checker source `72a27a9e30938811b564e27bf09b84bee2808a55`. No production availability/version gate changes.

Committed source snapshots: Hermes ed1afb082eb3e46cf2edae9d8f68fb67b09ee4df (four files) and0f0e96fc8e7fd35aba406e4a9fa341fb969d0b41 (five files, including plugins_context.py). The latter was retrieved through the established read-only host source route after local offline object retrieval refused. Exact git source refs and individual source hashes are retained privately; no native source was imported or executed, and source checkout head/status before/after were unchanged.

The old flat AST test failed on0f0 because PluginContext is explicitly re-exported from hermes_cli.plugins_context. This was a verifier assumption, not evidence that the running API is unavailable. The checker now follows bounded explicit class re-exports/aliases, preserves argument-subset checks, and refuses ambiguous bindings, wildcard imports, cycles, namespace/path escapes and symlinks. Maximum8hops and actual stream.read(1MiB+1) bound the lookup. Synthetic cases prove code is parsed without execution, binding changes are rejected, and a growing-source port never receives an unbounded read request.

Independent read-only review found and resolved visible rebinding forms, wildcard/annotation ambiguity and an initially unbounded read. Final finite repair accepted; earlier checkpoints are not final verifier proof. Successful final source-bound checks:
- ed1:26 cases `/private/tmp/hq-3m3d2s3h/receipt.json`
-0f0:26 cases `/private/tmp/hq-7ch06e3h/receipt.json`
- Python3.11 portable parser:23 cases `/private/tmp/hq-erqs5rhn/receipt.json`

Each current SDK selection includes24 synthetic parser cases and2 real-source registration/abstract-method shape checks. Floor omits the one TypeAlias syntax case unavailable to that parser and includes no native SDK runtime claim. The original flat-check failure is retained in `/private/tmp/hq-dfeq55iy/receipt.json`.

These are immutable-source declaration/signature facts. Arbitrary effective dynamic Python/metaclass behavior, inherited-only/computed exports, hostile mutable-filesystem leases, actual registration side effects, native services/approvals and physical/release qualification remain outside this result. No runtime version allowlist is introduced; later/unknown versions still follow minimum-version and real API/security gates.
