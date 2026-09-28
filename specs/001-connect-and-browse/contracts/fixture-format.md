# Contract: F1 Fixture Format and Isolation Rules

Fixtures are synthetic and labelled, and they live in isolated Hermes homes (owner amendment 3). They
never touch the owner's live Hermes, its database, profiles, bots, devices or emulator images. They
are not continuity evidence.

## Manifest: `fixtures/f1/instances.yaml`

```yaml
format: 1
label_prefix: "[F1 SYNTHETIC]"          # every seeded message text starts with this
continuity_evidence: false               # stated explicitly; tools refuse to run if this is changed
device_name_prefix: "f1-fixture-device-"    # CS-22 scannable prefix (required by SCHEMA.json)
operator_label_prefix: "f1-fixture-label-" # CS-22 scannable prefix (required by SCHEMA.json)
instances:
  - key: A                               # fixture-local key, never an iid
    display_label: "Fixture A"
    port: 0                              # 0 = pick a free port at run time
    users:
      - key: userA                       # pre-created HMP user id minted at build time (hmpu_…)
    profiles:
      - name: f1-alpha                   # authorized for userA; non-empty history
        display_name: "Alpha"
        authorize_for: [userA]
        conversation: conv-long          # reference into conversations below
      - name: f1-empty                   # authorized, no history (empty-state case)
        authorize_for: [userA]
        conversation: null
      - name: f1-pending                 # not authorized: pending_operator case
        authorize_for: []
      - name: f1-roles                   # history with non user/assistant roles and hostile text
        authorize_for: [userA]
        conversation: conv-roles
  - key: B
    display_label: "Fixture B"
    users: [{key: userB}]
    profiles:
      - name: f1-alpha                   # SAME profile name as on A, different content (edge case)
        display_name: "Alpha"
        authorize_for: [userB]
        conversation: conv-b
conversations:
  conv-long:  {generate: {count: 600, roles: [user, assistant]}}   # exceeds the max window (500)
  conv-roles: {messages: [{role: user, text: "…"}, {role: tool, text: "…"}, {role: system, text: "…"},
                          {role: assistant, text: "<script>…</script> **md** ‮txt https://example.invalid"}]}
  conv-b:     {generate: {count: 12, roles: [user, assistant]}}
mutations:                               # applied by tools/fixtures/mutate.py during refresh tests
  append:        {conversation: conv-b, add: 3}
  rewrite:       {conversation: conv-long, kind: in_place_compaction}   # new row ids, same session (RO-8)
  new_session:   {conversation: conv-b, kind: session_replaced}          # /new-equivalent (RO-6)
```

## Rules

1. `tools/fixtures/build_fixture.py --build <label> --out <scratch dir>` creates one `HERMES_HOME` per
   instance under a scratch directory. It unsets every inherited `HERMES_*` variable and fails if
   `HERMES_HOME` resolves inside the user's real home Hermes directory.
2. Profiles are created with the build's `hermes profile create` CLI. Per-bot authorization uses the
   supported operator path (`hermes -p <p> pairing approve hmp <request_id>`) after a P6 trigger, or
   the fixture tool performs the same approval through that CLI.
3. Messages and session bindings are written through the target build's own `SessionDB` and
   `SessionStore` APIs, offline (gateway stopped). This code is test tooling and lives only under
   `tools/fixtures/`.
4. Every build ends with a self-check: read back through the plugin's read path, then compare with
   the manifest (research R9).
5. Generated homes, keys and databases are never committed. Only the manifest and the tools are.
6. No real names, hosts, addresses or device identifiers appear in fixtures.
7. **Scannable labels (CS-22).** Every device name a fixture or test client sends in P2 starts with
   `f1-fixture-device-`, and every operator label used at `pair confirm` starts with
   `f1-fixture-label-`. The log scanner (T033) treats any occurrence of these prefixes, or of
   `label_prefix`, in a log as a leak (SR-007 excludes device names, operator labels and message text).
8. **Read-compatibility provenance (CS-19).** Fixture homes built from `git archive` extractions have no
   `.git`. Their builds are listed in `read_compat_builds.json` as fingerprint-only entries, with the
   extraction's commit as `source_sha` (provenance only).
