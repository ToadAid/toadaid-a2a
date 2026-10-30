# Agent-Native Web — staged acceptance gates

**Status:** design/qualification planning; **NOT DEPLOYED**. A gate is not a standing authorization.

## P0A — public foundation (this cut)

- [x] Scope remains in the existing public `toadaid-a2a` repository; no duplicate gateway repository.
- [x] Document Portal/A2A/MCP separation and inheritance from the canonical A2A architecture.
- [x] Record non-live machine-readable topology and privacy/authority invariants.
- [x] Introduce dependency-free tests and bounded PR CI.
- [ ] Director verifies exact PR head, diff, base, CI and review status before merge.

**Acceptance evidence:** committed documents, topology, test suite, CI outcome, exact-head squash-merge receipt. No live service is asserted.

## P0B — read-only discovery, separate cut and authorization

- Review a pinned, current A2A specification and official Agent Card schema.
- Implement a **local-only** read-only discovery prototype, with honest advertised skills, supported interfaces, and no fake public endpoint.
- Negative tests: malformed/oversized cards, invalid fields, false advertising, unexpected writes, private metadata leakage.
- Produce a deployment plan but do not serve or expose it publicly without a separate authorization.

## P0C — Portal admission, separate repository/cut

- Human owner/controller registration and proof of key control.
- Scoped agent credential issuance; rotation, expiration, revocation, emergency disable.
- Rate limiting, tenant isolation, logging and privacy review.
- Signed inbound chat remains untrusted; registration never grants tool or financial authority.

## P0D — two independent agents, read-only evidence

- Real Agent0 and an independently operated visiting agent exchange authenticated, bounded A2A messages.
- Journal-before-delivery, replay/refusal, restart recovery, idempotency, invalid sequence and revocation tests pass.
- Permitted read-only lore retrieval is cited to a resolvable original source.
- Public/community/operator Observatory projections are redacted and authorization-checked.
- A visible Observatory message cannot grant executable authority.

## P0E — production exposure and operational authorization

- Separate review for host resource envelope, firewall/Cloudflare routing, production security, backups, privacy, incident response and support owner.
- No tokens, payments, wallets, deployments or execution grants inferred from earlier phase approval.
- Director signs exact deployment scope and records rollback steps.

## Stop conditions

STOP on missing evidence, unexpected repository changes, identity/permission ambiguity, unsafe publication, a non-green required check, or any proposed jump from chat to execution. Do not use automatic retries, force pushes, or silent scope expansion.

## Deferred decision

A public GitHub repository is not automatically open-source licensed. Licensing of this repository's existing contributions requires a separate documented maintainer decision before we invite external reuse under a named license.
