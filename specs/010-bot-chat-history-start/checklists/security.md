# Security checklist

- [x] Bearer and per-bot authorization precede session lookup and content reads.
- [x] A foreign or unknown opaque ref is indistinguishable from a missing ref.
- [x] The existing session-browsing kill switch removes the route.
- [x] Limit and per-device rate bounds still apply.
- [x] No search term is accepted and the route adds no content or credential logging.
- [x] The route cannot alter the send path or Hermes execution ownership.
- [ ] Verify the complete app search flow against an isolated qualified build before shipping.
