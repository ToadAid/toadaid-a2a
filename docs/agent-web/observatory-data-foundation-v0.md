# Agent Observatory data foundation v0 (AO-P0A)

**Cut:** CUT-AO-P0A-20261103 (+ R1 security repairs)
**Status:** LOCAL SYNTHETIC FOUNDATION — **NOT DEPLOYED**
**Repository:** `ToadAid/toadaid-a2a` (base `d53275a638a506e3242e7e1c6c8c970c6cdbe7c4`)

Executable, read-only, bounded observability data foundation for the future
`agent.toadaid.org/dashboard/`. It does not reopen or amend the canonical A2A
architecture master note v0, the Agent-Native Web foundation, `topology.v0.json`,
the publishing plan, or the lore rights/handoff cuts.

## What exists in this cut

- `observatory/model.py` — bounded event model. Every record carries:
  `eventKind`, `eventId`, `correlationId`, `occurredAtUtc` (strict ISO-8601
  UTC), `evidenceClass`, `sourceIdentity`, `tenantRef`, `ownerRef`,
  `privacyClassification`, `visibilityClass`, a fixed **all-false**
  `authorityFlags` block, and an exact-whitelist `payload`.
- `observatory/feed.py` — bounded append-only recorder with a **trusted
  ingestion seam** (producer provenance is authenticated against an opaque
  producer credential bound to component, evidence classes, tenant/owner
  scope, relayable agents and human-receipt relay; component strings typed by
  callers are never credentials — R1) and a strictly read-only
  **owner-scoped** dashboard reader serving detached, deep-copied snapshots
  (R1: retained references cannot rewrite audited history).
- `observatory/contract.py` — the machine-readable interface contract (read
  authorization seam **and** trusted producer ingestion seam) and a synthetic
  example response for Codex's frontend work; item order is documented
  truthfully as recorder insertion order (R1).
- `contracts/agent-web/observatory-feed.v0.schema.json` — JSON Schema
  (draft 2020-12) for the feed response, aligned exactly with the generated
  feed and stored example (R1: five-flag `authorityFlags`, no unadvertised
  extra keys). The `$id` is NOT a live hosted URL.
- `contracts/examples/synthetic-observatory-feed.v0.json` — synthetic example,
  schema-conformant and byte-for-field identical to the generated example (R1).
- `observatory/model.py` additionally pins per-kind payload **leaf types**
  (identifier-only participants, typed int counters, bounded typed refs,
  calendar-real ISO-8601 UTC timestamps — R1).
- `tests/test_observatory_foundation.py` — unit + adversarial tests, including
  R1 regressions: forged component strings, binding scope breaches, retained-
  reference mutation attempts, schema-conformance validation, and typed/negative
  payload controls.

## Evidence classes (per record, always explicit)

| Class | Meaning | Presentation rule |
|---|---|---|
| `agent_reported` | Information claimed by an agent | Always served with `claimed: true` — never silently trusted |
| `infrastructure_observed` | Evidence from a trusted built-in component | Only class allowed to confirm registration status |
| `human_authorized` | Independently recorded human decision | Recorded by `independent-off-chat-human-process` only |
| `unverified` | Authenticity cannot be established | Projects conservatively (never "verified" anywhere) |

## Privacy model (Director clarification)

1. **PRIVATE OWNER DASHBOARD** — `/dashboard/`: authenticated, authorized
   humans only; owners may view only their own registered agents; ownership
   and tenant isolation enforced on every request; **fails closed** when
   authorization is missing or unavailable (the default trust adapter refuses
   everything).
2. **PUBLIC AGENT DIRECTORY** — `/agents/`: SEPARATE FUTURE CUT; requires
   explicit owner publication consent; any attempt to project a public
   directory from this cut is refused.
3. **THIS CUT'S SCOPE** — synthetic, read-only, local/offline fixtures; no
   public routes; no live authentication claims; the contract supports future
   owner-scoped access via a trusted-adapter seam without inventing or
   bypassing a production authentication system.

`PRIVATE BY DEFAULT · PUBLIC BY EXPLICIT CONSENT.`

## Boundaries (not done by this cut)

No production migration, provider activation, live agent admission, agent
registration, credential issuance, MCP tool authority or permission, wallet
access, A2A authority, execution eligibility, DNS routing, protected-host
mutation, deployment, or background service activation. The canonical 7-line
invariant block and the constitutional summary of the master note remain
untouched and guarded by tests.

## Director questions held for a later ruling

1. Which real authentication/authorization system should back the
   trusted-adapter seam (Portal identity is the candidate).
2. Retention/deletion policy for the private journal.
3. Sign the exact frontend contract revision before Codex UX/UI.

`ONE CUT · ONE PROOF · ONE DIRECTOR RULING.`