# Plan: phone attachment native primitives

- Parent process (`run`): builds the scratch roots, fingerprints owning files, spawns the child
  under the native interpreter with a minimal environment and `PYTHONDONTWRITEBYTECODE=1`,
  re-fingerprints, removes scratch, prints the summary.
- Child (`child`): re-asserts isolation, installs the IP-socket denial, then imports native code
  and runs the five subcases. It prints one JSON object of booleans/counts.
- Tests (`tools/fixtures/tests/test_phone_attachment_primitives.py`): pure-Python unit tests for
  the parent helpers that need no native build, plus native tests that skip when the pinned
  interpreter is absent.
- Trust boundary: the fixture never imports or changes HMP runtime; it touches only the native
  source (read) and its own scratch tree.
- Native source binding: archive copy, provenance `ca705dbf`; not a Git SHA attestation.
- Private-import note: the native helpers used here are not plugin APIs. Results describe this
  build only.
