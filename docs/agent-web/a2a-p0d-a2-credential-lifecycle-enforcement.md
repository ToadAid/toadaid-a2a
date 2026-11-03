# A2A-P0D-A2 — trusted credential-lifecycle enforcement (CUT-A2A-P0D-A2-20261103)

**Status:** LOCAL SYNTHETIC ENGINE · NOT DEPLOYED · NOT AN AUTHENTICATION
SYSTEM. This is an offline executable security-engine extension of
[P0D-A1](a2a-p0d-a1-registered-agent-admission-gate.md). No database,
identity provider, Portal account, external framework, network, Agent
Card, or live agent is connected here, and none is created.

## 1. Cut ID and mission

CUT-A2A-P0D-A2-20261103 extends the P0D-A1 registered-agent admission
gate with **independently verified credential-lifecycle state** so that
an agent cannot regain messaging permission using stale registration
evidence after **credential rotation, revocation, suspension, or
emergency disablement**.

Motivating principle (verified by tests, not decorative):

> A registration record containing `credentialGeneration` and
> `revocationEpoch` does not, by itself, prove those values are current.
> No agent-supplied claim can establish its own current credential state.

Constitutional rules preserved verbatim:
`REVOCATION_OVERRIDES_PRIOR_APPROVAL` and
`A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY`.

## 2. The four trust seams (was three)

The gate in `admission/gate.py` (`RegisteredAgentGate`) now fails closed
unless FOUR independent seams are injected:

1. **Trusted caller identity** (`trusted_caller_verifier`, R1-4) — WHO is
   asking; opaque `CallerCredential` → verified principal binding.
2. **Trusted registration decisions** (`trusted_registration_adapter`) —
   WHAT the registered agent may do (statuses, evidence, scopes).
3. **Trusted credential-lifecycle state** (`trusted_lifecycle_source`,
   NEW in this cut) — WHICH credential generation and revocation epoch
   are CURRENT, under an exact three-field identity query
   {agentRef, tenantRef, ownerRef}.
4. **Trusted clock** (`now`) — WHEN the evidence is still fresh.

**No state source means refusal** (`LIFECYCLE_SOURCE_NOT_TRUSTED`); a
malformed, missing, inconsistent, or untrusted state never defaults to
authorization. The lifecycle source is independent of caller-supplied
registration claims: state is fetched under the same exact identity
context as registration and its identity fields must equal the query
exactly (`LIFECYCLE_STATE_IDENTITY_MISMATCH`).

## 3. Lifecycle state contract (`admission/lifecycle.py`)

`build_lifecycle_state(...)` is an exact-whitelist builder (no **kwargs,
no passthrough). One trusted state record is exactly
`LIFECYCLE_STATE_KEYS`:

| Field | Rule |
| --- | --- |
| `kind` | `"toadaid-a2a-credential-lifecycle-state"` (constant) |
| `agentRef` / `tenantRef` / `ownerRef` | `^[a-z][a-z0-9-]{2,63}$` identifiers |
| `lifecycleStatus` | closed frozenset `LIFECYCLE_STATUSES` |
| `currentCredentialGeneration` | bounded non-negative int (no bool), ≤ `MAX_LIFECYCLE_COUNTER` |
| `currentRevocationEpoch` | bounded non-negative int (no bool), ≤ `MAX_LIFECYCLE_COUNTER` |
| `observedAtUtc` | calendar-real ISO-8601 UTC `%Y-%m-%dT%H:%M:%SZ` |

`LIFECYCLE_STATUSES = {"registered", "suspended", "revoked", "disabled"}` —
`registered` is the only admitting status; **`disabled` models EMERGENCY
DISABLEMENT** (a separately refusing status, so an emergency cannot be
expressed as a merely "suspended" or silently-recoverable state). A
reactivated agent appears as `registered` again **with current
generation/epoch fresh evidence** — never silently restored counters.

`synthetic_lifecycle_source(states)` is SYNTHETIC OFFLINE ONLY (declared
in its docstring): validates every state at construction (shape, kind,
values, per-key identity), returns validated deep copies, and is never
wired to production. Production stance: a real deployment injects an
independently observed lifecycle authority; that is a future cut.

## 4. Enforcement points and refusal codes

`RegisteredAgentGate._enforce_lifecycle(identity_query, decision)` runs
on EVERY `authorize()` call (sender side) and on EVERY `route()` call
for BOTH sender and recipient, after the respective registration
decision is verified and BEFORE any journal write.

Refusal order (all fail-closed):

| Refusal code | Trigger |
| --- | --- |
| `LIFECYCLE_SOURCE_NOT_TRUSTED` | no source injected, non-callable |
| `LIFECYCLE_QUERY_NOT_ADMITTED` | internal identity-query shape error |
| `LIFECYCLE_STATE_UNAVAILABLE` | source returns None (state-source disappearance) |
| `LIFECYCLE_STATE_SHAPE_INVALID` | non-dict / wrong keys / garbage response |
| `LIFECYCLE_STATE_KIND_INVALID`* | kind mismatch caught via rebuild comparison |
| `LIFECYCLE_STATE_TAMPERED` | rebuilt record ≠ raw record (e.g. forged kind) |
| `OBSERVATORY_REFUSAL family` | wrong VALUES (bad status/counters/stamp, e.g. `LIFECYCLE_STATUS_NOT_ADMITTED`) |
| `LIFECYCLE_STATE_IDENTITY_MISMATCH` | state identity ≠ pinned query identity |
| `CREDENTIAL_STATE_ROLLBACK` | source reports a counter below the gate's per-agent high-watermark |
| `LIFECYCLE_STATUS_REVOKED` / `_SUSPENDED` / `_DISABLED` | current status refuses (explicit revocation, suspension, emergency disablement) |
| `CREDENTIAL_GENERATION_STALE` | decision generation < current |
| `CREDENTIAL_GENERATION_NOT_CURRENT` | decision generation > current (future claim — higher is NOT automatically trusted) |
| `REVOCATION_EPOCH_STALE` | decision epoch < current (REVOCATION_OVERRIDES_PRIOR_APPROVAL) |
| `REVOCATION_EPOCH_NOT_CURRENT` | decision epoch > current (future claim) |

\* in the gate the rebuilt record always carries the canonical kind, so
a forged kind surfaces as `LIFECYCLE_STATE_TAMPERED`; the dedicated
`LIFECYCLE_STATE_KIND_INVALID` code exists in `admission/lifecycle.py`
for direct record validation.

Credential enforcement semantics:

- **Current generation permits** an otherwise-valid decision.
- **Older generation refuses** — rotation invalidates every
  previous-generation decision immediately.
- **A claimed future generation refuses** — newly rotated credentials
  do not become trusted merely because their generation is higher.
- **Malformed generation refuses** — booleans, strings, negatives, and
  out-of-bounds counters are explicit refusals in both the decision
  model and the lifecycle model.
- **A current trusted caller-identity binding and an independently
  verified registration decision remain mandatory** — the lifecycle
  seam is an ADDITIONAL gate, not a substitute; it can never rescue a
  bad caller binding, tampered decision, expired evidence, missing
  scope, or cross-tenant context.

Revocation-epoch semantics:

- **Current epoch permits** otherwise-valid participation.
- **Stale epoch refuses** — a decision minted before a revocation never
  authorizes afterwards.
- **A claimed future epoch refuses**.
- **Explicit revocation / suspension / emergency disablement refuse**
  through the CURRENT lifecycle status, even while older adapter
  decisions were valid when issued.
- **Reactivation cannot silently restore stale credentials**: after
  epoch N revoked and returned to `registered`, an epoch-N−1 decision
  still refuses (`REVOCATION_EPOCH_STALE`); only fresh evidence at the
  current epoch and generation admits.

## 5. The monotonic high-watermark (and its limits)

The gate keeps, PER AGENT, the maximum source-reported credential
generation and revocation epoch ever observed, refusing a source that
reports a lower value (`CREDENTIAL_STATE_ROLLBACK`). Equal-or-higher
reports refresh the watermark.

**Disclosed limitation:** the watermark is IN-MEMORY ONLY — it provides
**no durable rollback protection after process restart** (a restarted
gate accepts a rolled-back source again until it observes a high-water
value). No cryptographic provenance is invented, and the watermark is
never fed from anything agents claim. Durability is a separate future
cut (it needs durable, independently trusted state — same class of
decision as the durable journal).

## 6. Replay after revocation

Replay identity (R1-2) is unchanged: the journal key binds the request
digest to the VERIFIED recipient identity. What changes is ordering:
lifecycle enforcement happens **before** `journal.check_and_record`, so

- an **identical replay after a revocation refuses**
  (`LIFECYCLE_STATUS_*` / stale-evidence codes) and appends **NO journal
  entry** — a replay never bypasses a revocation that occurred since its
  original admission;
- a **conflicting replay after a revocation** likewise refuses at the
  lifecycle stage;
- an identical replay with UNCHANGED current state remains
  idempotent (`replayed-idempotent`, one journal entry);
- lifecycle refusals (on either admission side) never append a journal
  entry — journal length is asserted in the adversarial suite.

## 7. Verification (local, offline)

`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v` —
**368 tests OK** (316 preserved baseline + 52 new in
`tests/test_a2a_p0d_credential_lifecycle.py`). No existing test was
removed or weakened (no assertion lines in the removed hunks of the
P0D-A1 test file; only fixture gate constructions gained the new
injected seam and the module docstring was updated). `git diff --check`
clean.

Adversarial controls implemented (all negative unless stated):

1. Old SENDER credential after rotation → `CREDENTIAL_GENERATION_STALE`,
   journal unchanged.
2. Old RECIPIENT credential after rotation → same, journal unchanged.
3. Revocation between consecutive messages →
   `LIFECYCLE_STATUS_REVOKED`; exactly one journal entry remains.
4. Suspension between consecutive messages →
   `LIFECYCLE_STATUS_SUSPENDED`.
5. Emergency disablement (`disabled`, sender authorize+route and as
   recipient-between-messages) → `LIFECYCLE_STATUS_DISABLED`.
6. State-source disappearance between messages →
   `LIFECYCLE_STATE_UNAVAILABLE` (authorize and route).
7. Malformed source responses → garbage/non-dict/wrong keys/extra keys/
   wrong kind/wrong values; shape/tamper/value refusals, never
   authorization.
8. Agent, owner, and tenant binding mismatch of the STATE record →
   `LIFECYCLE_STATE_IDENTITY_MISMATCH` per field; foreign-key agentRef
   refused at the source factory (`LIFECYCLE_SOURCE_KEY_MISMATCH`).
9. Generation rollback → `CREDENTIAL_STATE_ROLLBACK` (per-agent,
   equal-counters allowed, refusal writes no journal entry).
10. Revocation-epoch rollback → `CREDENTIAL_STATE_ROLLBACK`, including
    the un-revocation-after-revocation attack.
11. Future-generation claim → `CREDENTIAL_GENERATION_NOT_CURRENT`;
    future-epoch claim → `REVOCATION_EPOCH_NOT_CURRENT`.
12. Replayed message after revocation → refused, no journal entry;
    conflicting replay likewise; unchanged-state replay stays
    idempotent.
13. Two different owners within the same tenant → still permitted
    (owner isolation does not collapse tenant policy).
14. Cross-tenant refusal preserved → `CROSS_TENANT_DELIVERY_REFUSED`,
    writes no journal entry.
15. All-false authority flags and the boundary string on every delivery
    receipt; `A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY` invariant tests.

Model/source unit controls: closed status vocabulary, exact state keys,
no-kwargs smuggling, full construction-refusal matrix (identifiers,
statuses incl. collection-typed values, counters incl. booleans and
bounds, calendar-real timestamps), source independence (deep copies),
factory shape/key validation, and disclosure assertions (watermark
IN-MEMORY wording, `REVOCATION_OVERRIDES_PRIOR_APPROVAL`, the
no-agent-claim line, unchanged gate status).

## 8. Remaining limitations (explicit, NOT assumed away)

- **In-memory lifecycle evidence:** the trusted lifecycle source, the
  high-watermark, and the journal are process memory. Restart loses the
  watermark and any durable propagation of revocation; this cut is an
  OFFLINE FOUNDATION, not a durability cut.
- **No real lifecycle authority exists:** no database, identity
  provider, Portal account, or external framework is connected; the
  synthetic source fixture is SYNTHETIC OFFLINE ONLY.
- **No production registration or authentication:** all P0D-A1
  boundaries stand (no agent admission on live surfaces, no public
  Agent Card, no Portal integration, no OpenClaw/Hermes live
  integration).
- **No credential issuance to real agents**, no wallets, payments, MCP
  tools, or host execution; admitted messages retain
  `A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY`.
- **No external networking, no deployment, no DNS changes.**
- GATE_STATUS remains `LOCAL_SYNTHETIC_ENGINE_NOT_DEPLOYED`; the
  receipt shape is unchanged (lifecycle enforcement is invisible in
  receipts — it can only remove authorization, never add any).