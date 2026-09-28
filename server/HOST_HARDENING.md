# Host hardening for HMP

This note is for the operator running the Hermes host that HMP (the Hermes Mobile Protocol plugin)
attaches to. It covers **SEC-3: other host surfaces** (`docs/architecture/contracts/HMP_V1.md`,
"Security boundary statement"; ADR-0003 rule 10). Read it once per host before pairing a phone.

## What HMP does and does not protect

HMP's pairing, tokens and per-connection TLS pin secure **only the HMP listener** — the process that
serves `/hmp/v1/...`. Pairing an app does nothing for the Hermes host's other listeners:

- **`api_server`** — Hermes's own HTTP API, if enabled.
- **The dashboard** — its own process, and it can itself approve Hermes pairing requests.
- **`/api/status`** — served without authentication.

None of these are hardened, gated or made safer by pairing a phone. If they are reachable, they are
reachable to anything that can reach them — regardless of whether HMP is paired, running, or even
installed.

## The one rule

**Never expose, un-gate or proxy any host surface to make mobile pairing easier.** Specifically:

- Do not bind `api_server`, the dashboard or any other Hermes listener to a public or `0.0.0.0`
  address "just for the phone." Reachability for the phone comes from being on the same tailnet, not
  from opening a surface up.
- Do not put a TLS-terminating proxy in front of HMP. **No Tailscale Serve, no Tailscale Funnel, no
  other TLS-terminating proxy, in front of HMP — ever.** HMP's client pins the leaf certificate's SPKI
  straight to the instance key (TR-2). A terminating proxy presents a different certificate, so this
  fails the pin by construction; if you are tempted to work around that failure by weakening the pin
  or trusting the proxy's CA, don't — that is exactly the substitution TR-2 exists to catch. Funnel in
  particular republishes the same `*.ts.net` name outside the tailnet, so a client-side name check
  cannot detect that a "private" address has gone public.
- Do not add exceptions, forwarding rules, or firewall openings for the dashboard, `api_server` or
  `/api/status` to work around a connectivity problem. If a phone can't reach the HMP listener over
  the tailnet, that is a tailnet configuration problem to fix on its own terms — not a reason to widen
  what else is reachable.
- Do not disable or bypass Hermes's own authentication on `api_server` or the dashboard "temporarily."
  There is no supported temporary state for that.

## What to actually check

- Confirm `api_server`, the dashboard and any other Hermes listener are bound the way you intend
  (loopback, or tailnet-only with Hermes's own auth in front) — the same as you would run Hermes
  without HMP at all. HMP does not change what is safe to expose here.
- Keep Hermes's own authentication in front of `api_server`, the dashboard and any other surface that
  has one. HMP is not a substitute for it and doesn't know those surfaces exist.
- If `/api/status` is reachable on your tailnet, treat it as unauthenticated and low-sensitivity by
  design — don't route anything sensitive through it, and don't assume pairing hides it.
- Tailscale gives you private *reachability* between your phone and the host. It is not
  *authorization* for anything HMP or Hermes serves. Keep tailnet ACLs as tight as your normal
  practice, independent of HMP.
- The HMP listener itself already refuses non-tailnet peers and non-loopback binds outside the
  documented ranges (TR-4); that check is HMP's alone and says nothing about your other surfaces.

## If you're not sure

If a surface's exposure is unclear, don't guess. Leave it at whatever its Hermes-default binding is
and ask before changing it. HMP is scoped to its own listener; anything else is host administration
and stays the operator's call.
