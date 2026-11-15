# Host setup check

Status: draft implementation. This is the read-only diagnostic shared by a
future interactive setup flow. It does not configure Hermes.

## Operator outcome

After installing HMP, an operator can run `hermes hmp setup check` to learn
whether this exact Hermes build is read-compatible, whether HMP has a current
instance identity, and whether its listener is running with the expected TLS
identity. The command gives the safe next step when one check fails.

## Requirements

- The command works before first gateway start and changes no host state.
- It neither creates nor migrates the HMP store, identity, routes, or Hermes
  configuration. It never runs a Hermes child command.
- It shows no paths, keys, device IDs, profile names, or untrusted labels.
- A stale, unsafe, or wrong-key listener record cannot produce a ready result.
- It cannot claim that a served profile is routed, authorized, or has a usable
  profile-scoped API key. The public deployment guide remains the source for
  those checks.
- A failed check exits nonzero for scripting; an unsupported build fails closed.

## Clarification

An interactive wizard that applies gateway configuration is a separate
decision. On Hermes `8afaab3703`, writing an explicit multiplex setting can
bypass its boot preflight and change API ingress and secret scoping. This
diagnostic therefore does not offer a shortcut around Hermes migration.
