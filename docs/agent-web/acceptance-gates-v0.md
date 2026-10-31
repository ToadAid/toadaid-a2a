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

## P0-WEB-01 — proposed Agent-Native publishing surface (parallel documentation cut)

See [P0-WEB-01 blueprint](p0-web-01-agent-native-publishing-blueprint.md) and [separate acceptance gates](p0-web-01-acceptance-gates.md). This is **architecture-only; NOT DEPLOYED** and does not supersede P0B-C2, P0C or P0E.

- [x] Specify machine-native discovery plan distinct from human Portal and governed MCP.
- [x] Explicitly classify A2A Agent Card, optional `llms.txt`, experimental `siteai.json`; no discovery document confers authorization.
- [x] Specify same-source HTML/Markdown/JSON variants, `Accept` negotiation and safe `Vary: Accept` caching.
- [x] Specify copyright/rights, provenance classification, non-canonical synthetic sample and no private journal export.
- [x] Bind future actions to authenticated server-side policy, current exact-artifact grants, and separate human approval.
- [ ] Qualify static plan tests in PR CI and exact-head squash merge with verified post-merge CI.
- [ ] **Actual public route implementation, A2A conformance and deployment remain separately unapproved.**

## P0-WEB-02 — controlled synthetic representation fixture

See [P0-WEB-02 proof scope](p0-web-02-local-negotiation.md). **Local-only. NOT DEPLOYED.**

- [x] Explicitly started loopback fixture for one non-canonical fictional record, not a real Lore Land.
- [x] Render one allowlisted public-source projection as HTML, Markdown or JSON using a bounded Accept subset.
- [x] HTTP status and header controls: Content-Type, Vary, no-store, noindex, CSP; negative malformed/oversized Accept and unknown routes.
- [x] No server-side action processing, no mutation methods, no external fetch; test that accidental secret fields stay excluded.
- [ ] Exact-head PR CI verifies all static and live-loopback tests.
- [ ] Director reviews exact PR scope and squash merges only with green CI and post-merge proof.
- [ ] Official A2A TCK, real Lore rights verification, public publishing, credentials and action authorization remain separate gates.

## P0B-C2A — manually gated official TCK runner preparation

See [P0B-C2A qualification plan](p0b-c2a-manual-tck-harness.md). **Runner prep only; official TCK NOT RUN.**

- [x] Prepare explicit `workflow_dispatch` for main with guarded acknowledgement; no automatic PR/push execution.
- [x] Freeze and verify official TCK upstream commit, tree, runner, project and dependency-lock Git object identities before installation.
- [x] Require GitHub-hosted disposable runner, no persistent checkout credentials, no production host, real data or tools.
- [x] Use the current bounded synthetic loopback A2A probe, run upstream JSON-RPC MUST tests, retain raw compatibility reports and failure status.
- [x] Fail closed on TCK nonzero exit, missing reports, empty/all-skipped suites, errors and failures; no test bypass or green-only report.
- [ ] Director separately authorizes manual dispatch on main and verifies the authentic Actions run and collected evidence.
- [ ] Official upstream TCK results reviewed and mandatory failures classified; this gate is NOT complete.
- [ ] External SDK interoperability, SHOULD/MAY and full protocol conformance remain separately unproven.
- [ ] Any production Agent Card, identity admission, host or public networking separately authorized.

**No effect on P0B-C2's pending conformance status or P0E deployment gate.**

## P0B-C2B — Director gate diagnostic repair (no TCK execution)

The first manual attempt (Actions run #41118047825) was **SKIPPED**. Main ref was correct; the exact submitted input was not exposed, so the input mismatch remains an inference, not confirmed fact.

- [x] Move branch and exact Director approval checking to the first executable step, before checkout/dependencies.
- [x] Failed/invalid input produces a visible, red, generic refusal without echoing input values; wrong ref also refuses.
- [x] Keep manual-only dispatch, read-only permissions, pinned upstream sources, ephemeral loopback server and unchanged TCK command.
- [x] If gate is denied, do not upload nonexistent evidence; if approved but TCK fails, preserve raw reports and nonzero status.
- [x] Add synthetic negative tests for empty/incorrect/whitespace approval and non-main ref; no official TCK in PR CI.
- [ ] Exact-head PR CI and review; guarded squash merge; post-merge CI confirmation.
- [ ] New separately authorized manual trial with unmodified upstream reports. **Official TCK NOT RUN yet.**

**A green gate check is not an A2A conformance claim, tool approval or deployment grant.**

## P0-WEB-03A — canonical lore source binding, metadata only

See [P0-WEB-03A provenance and rights gates](p0-web-03a-lore-source-inventory.md). No real public publishing is authorized.

- [x] Inspect Lore Reader's permanent canonical source identity, exact-commit importer, ID preservation and archive-date semantics.
- [x] Observe canonical `lore/data.json` at an explicit, generation-specific public commit (132 records) without vendoring original content.
- [x] Provide an offline read-only Git-object inventory emitting SHA-256 and bounded record counts, **not** lore text, images, rights grants or publication endpoints.
- [x] Refuse duplicate IDs, invalid source records, unreviewed object identifiers and altered origin strings; tests use synthetic local Git data.
- [x] Explicitly mark text/media rights as unknown and public exports as forbidden until documented rights and provenance review.
- [ ] Exact-head PR CI, scope review, squash merge and post-merge CI verified.
- [ ] **P0-WEB-03B:** independent provenance/rights/admission before real content export.
- [ ] **P0B-C2:** official A2A TCK and **P0E:** deployment remain separate gates.

**Public GitHub accessibility is not an automatic redistribution license.**
