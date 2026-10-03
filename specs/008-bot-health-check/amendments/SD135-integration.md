# SD1, SD3 and SD5: isolated integration candidate

Status: source composition prepared; independent review and candidate CI pending.
No installed Hermes, owner configuration, native gateway or mobile deployment.

## Requirements and scope

Combine the three independently reviewed repairs on the exact common parent
`3e676ec10266ef958ca631b6f8384c6aa297745e`:

- SD5, source `7b8138e4e62bd7cff975909f1a1cc09b6cee73c5` (PR #93): the
  default scoped API key follows the existing stripped 16-character floor;
  exact accepted key bytes and named-profile authority remain unchanged.
- SD3, source `69bd1d6f2d03d78ebe0ea8cfe36d1e5ac039dfc1` (PR #94): device
  metadata listing refuses a declared Hermes session before store opening.
  Ordinary operator listing retains its existing non-TTY behavior. The existing
  session-before-TTY mutation checks retain their ordering.
- SD1, source `c0d0945b64058e3f337c8ff7181ec3294387df9a` (PR #95): listener
  records preserve all 128 supported profile identities and health entries
  without truncation. Local file reads, writes and removals use a 64 KiB bound;
  legacy small parsing and pinned network ready reads remain at 16 KiB.

The composition introduces no new production behavior beyond these repairs.
Its CLI file must equal the accepted SD1 CLI with exactly the accepted SD3 helper
extraction and pre-open dispatch guard applied. Its bridge and bridge tests must
equal SD5; CLI tests must equal SD3; listener tests and original SD1 contract and
amendment must equal SD1. Other production, authority, adapter, custody, wire,
native, dependency and CI files remain at the common parent.

## Verification gates

- [x] Three source commits applied without conflict in a separate worktree.
- [ ] Exact composition and untouched-file preservation independently reviewed.
- [ ] Candidate CI passes lint, unit/tool tests, closed surface, log hygiene and
  privacy checks on the exact published candidate head.
- [ ] Integration accepted from the independent review and exact CI evidence.

Existing cases include 65 new SD1 inventory/size/security/failure cases, 20 SD3
populated device-list controls and 10 SD5 scoped-key boundary controls. Their
separate passing CI runs do not prove the combined candidate. The common-parent
suite had 2,615 passes; all 95 additional cases should yield 2,710 passes if the
combined suite retains its 17 skips. This is an expected count, not a test result.
No additional tests merely mirroring the cherry-picked changes are introduced.

## Security boundaries and remaining work

Session environment presence remains a mitigation, not an authenticated
same-OS-user boundary. Key length is not entropy proof. For listener refreshes
outside the supported 128-profile domain, an older record can remain fresh for
up to 45 seconds; freshness does not prove the current live roster. Older
16 KiB readers reject the new large records. These limits remain explicit.

Native/shared-Desktop bounded observation, real phone/card/media validation,
push sealing/registration/relay, owner activation, deployment and release gates
remain separate. This integration adds no exact-build availability allowlist,
upstream patch, phone execution fallback, new user grant or live access.
