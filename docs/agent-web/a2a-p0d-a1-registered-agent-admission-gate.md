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

## Verification (local, offline)

`python3 -m unittest discover -s tests -v` — 297 tests OK
(236 baseline + 61 new adversarial cases in
`tests/test_a2a_p0d_admission_gate.py`), covering: model binding and
kwarg smuggling, calendar-real timestamps, the full construction-refusal
matrix, fail-closed default gate and clock handling, adapter tamper and
malformed record refusals, every registration status, evidence expiry
including the inclusive boundary, claim forgery (Agent Card, execution,
payment, wallet, deploy, registration-change, directory claims), message
body claims, owner/tenant context mismatch, participation scoping on both
sides of a delivery, request/recipient shape refusals, self-delivery,
replay idempotence and conflict, journal capacity, export/restore restart,
broken/tampered chain refusals, duplicated messageId in a re-signed
chain, metadata-only journal contents, cross-tenant refusal (reachable,
and it writes no journal entry), receipt binding of both agents, the
full two-agent rehearsal A→B and B→A with descriptive framework labels,
revocation mid-conversation, the preserved invariant verbatim, and
constants.

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
- Worktree: branch `cut-p0d-a1-registered-agent-admission-20261103`.
- Deliverable state: committed NOTHING yet — stopped before commit,
  push, PR, merge, or deployment per mission order.

ONE CUT · ONE PROOF · ONE DIRECTOR RULING.
HUMANS AUTHORIZE · AGENTS PROVE · AUTHORITY IS NEVER ASSUMED.