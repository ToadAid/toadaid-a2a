# Agent-Native Web — staged acceptance gates

**Status:** design/qualification planning; **NOT DEPLOYED**. A gate is not a standing authorization.

## P0A — public foundation (this cut)

- [x] Scope remains in the existing public `toadaid-a2a` repository; no duplicate gateway repository.
- [x] Document Portal/A2A/MCP separation and inheritance from the canonical A2A architecture.
- [x] Record non-live machine-readable topology and privacy/authority invariants.
- [x] Introduce dependency-free tests and bounded PR CI.
- [x] Director verified exact P0A PR #3 head, diff, base and successful CI before squash merge; post-merge CI green.

**Acceptance evidence:** committed documents, topology, test suite, CI outcome, exact-head squash-merge receipt. No live service is asserted.

## P0B — read-only discovery, separate cut and authorization

**P0B-A (completed in PR #4):** offline, bounded, no-network candidate A2A 1.0 card structural inspector with negative controls. No public service or claim of endpoint availability. See [P0B-A](p0b-a-offline-discovery.md).

**P0B-B (completed in PR #5):** pinned upstream A2A v1.0.1 normative proto and specification source identity, implemented a real **127.0.0.1-only** JSON-RPC v1.0 `SendMessage` static acknowledgment probe with honest local Agent Card, private journal-before-delivery, bounded input, idempotent replay, single-writer lock and real socket negative tests. See [P0B-B limitations and evidence](p0b-b-loopback-probe.md).

- [x] Local-only discovery and actual bounded JSON-RPC binding, without public endpoints, models or tools.
- [x] Pin official upstream tag/commit plus normative proto and spec Git object identities.
- [x] P0B-B 25 local tests plus PR and post-merge CI passed; does not confer official A2A conformance.
**P0B-C1 (this cut):** separate-process, standard-library client reads the actual loopback Agent Card and exchanges real JSON-RPC with the separately spawned P0B-B server; tests refusal of advertised capabilities and remote URLs. Official TCK source commit, runner and `uv.lock` Git object identities are frozen in [P0B-C1](p0b-c1-interop-tck-readiness.md). This is **same-repository independent-process smoke only**, not independent upstream conformance.

- [x] P0B-C1 client and negative tests added; PR CI still must qualify exact head.
- [x] Pin upstream TCK source and dependency lockfile (source identification only).
- [ ] **Official independent A2A TCK MUST/SHOULD/MAY suite NOT RUN**; official compatibility NOT established.
- [ ] **Independently maintained A2A SDK client NOT RUN** against this probe; do not claim external SDK interoperability.
- [ ] Resolve TCK mandatory failures, unsupported methods and protocol semantics before any general-conformance statement.
- [ ] Complete real agent principal-bound journaling, identity/admission, revocation, privacy and operational safety review in separately authorized cuts.
- [ ] Production Agent Card, DNS, tunnel and public exposure require a future explicit Director deployment gate.

**P0B remains INCOMPLETE.** P0B-B and P0B-C1 are bounded local proofs; neither authorizes gateway activation.

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
