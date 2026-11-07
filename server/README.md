# HMP implementation

`hmp_plugin/` contains the Hermes platform adapter, operator CLI, pairing and authorization store, HMP wire handling, guarded send path, and compatibility gate. Its `register(ctx)` entry point adds exactly one platform adapter and one CLI command. The repository root contains the install wrapper used by Hermes's bare `owner/repo` installer.

The package source is preserved from the private F1 implementation. See [HMP v1](../docs/architecture/contracts/HMP_V1.md) for its wire contract, [deployment](DEPLOYMENT.md) for profile routing, and [contributing](../CONTRIBUTING.md) for checks.

The internal `presentation_credential_cleanup_frame.py` stage continues one
newly authenticated frame on the retained reader/socket/task. It returns bounded
consistency data only and is not registered for production delivery. Scope and
remaining lifecycle gates are tracked in
[the signed result contract](../specs/046-bot-presentation-integration/SIGNED_RESULT_READ.md).
