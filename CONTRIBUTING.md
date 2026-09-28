# Contributing

Thanks for helping improve HMP. Please open an issue for behavior or contract changes before implementing them. Keep pull requests focused and describe the Hermes revision used for compatibility testing.

## Local checks

```sh
uv run --frozen --project server --extra dev pytest server/tests/unit tools/ci/tests tools/fixtures/tests tools/hermes_builds/tests tools/vectors/tests tools/acceptance/tests
uvx ruff==0.16.9 check --config server/pyproject.toml server tools
python3 tools/ci/check_plugin_surface.py
python3 tools/ci/scan_private.py
python3 tools/ci/scan_logs.py
```

Fixture and compatibility tests need extracted Hermes source builds and a real PTY for pairing. They are local-only in this migration because CI does not yet provision those pinned build snapshots and a PTY fixture. See [the install guide](docs/INSTALL.md) for `_refs/` setup. Use an isolated `HERMES_HOME` for any plugin install test.

## Review rules

- Keep the plugin registration surface closed: one platform adapter and one operator CLI.
- Preserve fail-closed behavior on unknown Hermes builds.
- Add or update the [contract](docs/architecture/contracts/HMP_V1.md) when wire behavior changes.
- Never commit secrets, real device IDs, private host paths, private addresses, or owner evidence. Run the zero-baseline privacy scan before pushing.
- Keep app code and private research evidence out of this repository.

The [Spec Kit constitution](.specify/memory/constitution.md) records the project-wide rules. A feature PR should include a focused specification, plan, and verification tasks under `specs/`.
