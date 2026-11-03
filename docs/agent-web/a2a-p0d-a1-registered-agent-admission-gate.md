# CUT-A2A-P0D-A1-20261103 — Universal Registered-Agent Admission Gate

**Status: NOT DEPLOYED.** Local synthetic engine only. No public Agent
Card, no external endpoint, no production gateway, no deployment. No
upstream A2A conformance claim. The pinned A2A protocol contracts and the
loopback probe are untouched by this cut.

**Boundary:** A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY — an admitted message
authorizes NO tool, payment, wallet, deployment, protected-host mutation,
or registration change. Every receipt re-asserts all-false authority
flags by construction.

## What this cut is

An executable, transport-independent, framework-neutral registration-aware
A2A participation and message-routing core:

- `admission/model.py` — the registration decision record: an
  ADAPTER-VERIFIED record built through an exact whitelist signature
  (no `**kwargs` passthrough). It binds stable agent identity, verified
  owner/controller reference, tenant, registration status, credential
  generation, revocation epoch, evidence observation and expiry instants,
  and the explicit A2A participation scopes. None of these implies
  another automatically.
- `admission/gate.py` — the participation gate and router. An
  A2A message is admitted ONLY after independently verifying trusted
  registration decisions held by an injected adapter, separately for the
  sender (`a2a-message-send`) and the recipient (`a2a-message-receive`),
  under each agent's own exact identity context. Routing is journal-first:
  the metadata journal entry is committed before the delivery result.
- `admission/__init__.py` — the fail-closed boundary declaration.

## Structural laws (all enforced by code and by tests)

1. **Claims never authorize.** The request schema carries no claim fields
   at all: an Agent Card, a message body, or a browser claim has no field
   to live in, so every forgery dies as `REQUEST_KEYS_NOT_ADMITTED`
   before any decision is consulted.
2. **Adapter seam fails closed.** A default-constructed
   `RegisteredAgentGate()` (no adapter, no clock) admits nothing and
   refuses everything. Adapter records are rebuilt and compared
   canonically; an extra field or a flipped authority flag is refused as
   `REGISTRATION_DECISION_TAMPERED`.
3. **Status and freshness.** `revoked`, `suspended`, `unregistered`, and
   unknown statuses are refused with distinct codes; expired evidence is
   refused (`<=` is expired at the exact boundary instant).
4. **Scoping.** Send and receive are separate participation scopes;
   neither implies the other; both sides of a delivery are verified
   independently.
5. **Tenant isolation.** Cross-tenant delivery is a reachable refusal
   (`CROSS_TENANT_DELIVERY_REFUSED`). Different owners within one tenant
   may address each other; different tenants may not.
6. **Journal is metadata-only.** Entries store
   `{messageId, requestDigest, prev, digest}` — canonical digests only,
   never message bodies. Identical replays are idempotent; a conflicting
   digest under the same messageId is refused; capacity fails closed;
   export/restore verifies the hash chain and refuses broken or foreign
   state; a duplicated messageId is refused even inside a perfectly
   re-signed chain.
7. **Framework neutrality.** Framework names (`FRAMEWORK_KINDS`) are
   descriptive metadata only — never proof of identity or authority. The
   two-agent synthetic rehearsal uses two descriptive labels
   (`openclaw`, `hermes`) as METADATA with no integration claim of any
   kind: nothing framework-specific is wired, implemented, or tested.
8. **Owner independence.** No Diamond, ERC-8004, MCP, or provider
   condition exists anywhere on the decision model or the gate. External
   agents from any ecosystem are admitted on the same terms: registered,
   current evidence, authorized scope.

## What is NOT in this cut

- No production registration service, authentication system, key
  handling, or network transport. The adapter seam accepts any
  independently verified implementation in a future cut; the synthetic
  adapter is explicitly labeled SYNTHETIC OFFLINE ONLY.
- No A2A message semantics beyond local admission (no task execution, no
  media handling, no streaming).
- No public directory exposure: admission decisions grant
  `a2a-message-send` / `a2a-message-receive` only and every receipt keeps
  `publicDirectoryExposed: false`.
- No changes to Portal, MCP, Diamond OS, wallets, Lore Land contracts, or
  production hosting.

## R1 (review `5754596528`) — director-ordered hardening

Four blockers repaired, all test-covered:

- **R1-1 — sender SEND enforcement.** `route()` ALWAYS requires
  `a2a-message-send` from the sender's verified decision, regardless of
  the request's declared scope; a route request declaring anything else
  is refused as `SENDER_SCOPE_MISMATCH`, and a send-less sender is
  refused as `PARTICIPATION_SCOPE_NOT_AUTHORIZED`. A receive-only agent
  can never initiate delivery.
- **R1-2 — recipient-bound replay identity.** The journal key is now a
  delivery digest over (request digest + canonical verified recipient
  identity). The same message ID aimed at a DIFFERENT registered
  recipient is a conflicting replay (`REPLAY_MESSAGE_ID_CONFLICT`), never
  an identical one; the journal field is `deliveryDigest` (rename honest).
  Covered across same-tenant distinct recipients and across
  export/restore.
- **R1-3 — true UTC conversion.** Aware clocks are converted with
  `astimezone(timezone.utc)` — never offset-stripped; non-UTC offsets can
  no longer revive expired evidence. Positive and negative tests with
  +02:00, -06:00, and +05:45 offsets straddle expiry boundaries.
- **R1-4 — caller authentication seam.** Registration is NOT
  authentication. Every `authorize()`/`route()` call now requires an
  opaque `CallerCredential` bound by an injected trusted caller-identity
  verifier to a verified `{agentRef, tenantRef, ownerRef}` principal; the
  request context must EQUAL the verified binding
  (`CALLER_IDENTITY_MISMATCH` otherwise). A missing verifier, a None or
  string or dict credential, a foreign credential, or a tampered binding
  all refuse. No production authentication, Portal login, or live
  connection: the synthetic verifier is explicitly SYNTHETIC OFFLINE
  ONLY.

Additional hardening in the same pass: recipient tenant/owner identifiers
are pinned before any adapter call
(`RECIPIENT_{TENANT,OWNER}_REF_NOT_ADMITTED`); malformed collection-valued
enum inputs (list/dict where a string enum is required — status,
framework, scopes, declared scope, message type) now produce explicit
refusals instead of uncontrolled TypeErrors (guard added in
`admission/model.py` and the request validators); and the journal is
documented as IN-MEMORY, non-durable state whose restored hash chain is
tamper-EVIDENCE only — a hash chain does not authenticate externally
supplied history.

## Verification (local, offline)

`python3 -m unittest discover -s tests -v` — 316 tests at this cut's
baseline (236 baseline + 80 in
`tests/test_a2a_p0d_admission_gate.py`), covering: model binding and
kwarg smuggling, calendar-real timestamps, the full construction-refusal
matrix plus malformed-collection enums, fail-closed default gate, all
three trust seams at this cut's baseline (caller verifier / registration
adapter / clock) each refusing independently when missing, caller-identity
enforcement (R1-4), sender send enforcement (R1-1), recipient-bound replay across
recipients and export/restore (R1-2), aware-clock UTC conversion
boundary pairs with nonzero offsets (R1-3), adapter tamper and malformed
records, every registration status, evidence expiry including the
inclusive boundary, claim forgery (Agent Card, execution, payment,
wallet, deploy, registration-change, directory claims), inert message
body claims, owner/tenant context mismatch, participation scoping on
both sides of a delivery, request/recipient shape refusals including
pre-adapter recipient pinning, self-delivery, replay idempotence and
conflict, journal capacity, export/restore restart, broken/tampered
chain refusals, duplicated messageId in a re-signed chain,
metadata-only journal contents, cross-tenant refusal (reachable, and it
writes no journal entry), receipt binding of both agents, the full
two-agent rehearsal A→B and B→A with descriptive framework labels,
revocation mid-conversation, the preserved invariant verbatim, and
constants.

NOTA (P0D-A2): the gate now carries a fourth fail-closed seam — the
trusted credential-lifecycle state source enforcing
REVOCATION_OVERRIDES_PRIOR_APPROVAL on every admission. The fixture
gates in the P0D-A1 test file inject it alongside the original three
seams; the dedicated lifecycle adversarial suite and its refusal codes
are documented in
[a2a-p0d-a2-credential-lifecycle-enforcement.md](a2a-p0d-a2-credential-lifecycle-enforcement.md).

## Director decisions still open (NOT assumed)

- The trusted adapter contract here is a seam: production registration
  (who issues decisions, how evidence is observed, how revocation
  propagates) is a separate future cut.
- Same-tenant-only delivery is the implemented policy; cross-tenant A2A
  routing (if ever wanted) needs an explicit Director ruling.
- Credential generation and revocation epoch are carried but not yet
  consumed by any credential-rotation or revocation-propagation cut.

## Base and boundary

- Base commit: `cc7eec4ee0f84f9d501fe0d891d2f8f8f363b9a9` (origin/main
  after PR #14 squash-merge).
- PR #15 cut commit: `3ef28b6f2a03bd3c65a96a66c74510d75bc8ece0`
  (branch `cut-p0d-a1-registered-agent-admission-20261103`).
- R1 state: the four review-blocking repairs above are implemented and
  locally verified as UNCOMMITTED changes on top of the PR #15 cut
  commit; stopped before commit, push, PR update, or merge per the
  R1 mission order.

ONE CUT · ONE PROOF · ONE DIRECTOR RULING.
HUMANS AUTHORIZE · AGENTS PROVE · AUTHORITY IS NEVER ASSUMED.