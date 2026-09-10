# ToadAid Governed Work-Market Blueprint v0.1

**Status:** Proposed blueprint for review  
**Scope:** Documentation and candidate protocol contracts only  
**Authority:** None; this document does not authorize implementation, execution, wallets, payments, deployment, or token creation  
**Parent:** `canonical-a2a-architecture-master-note-v0.md`

## 0. Purpose

This blueprint translates the canonical A2A architecture into a staged plan for an evidence-backed agent service economy.

The first economic primitive is a bounded work agreement, not an agent token or wallet. ToadAid earns from accepted, verifiable work while principals retain sovereignty.

```text
IDENTITY OPENS DISCOVERY
MANDATES BOUND WORK
EVIDENCE EARNS TRUST
ACCEPTED WORK MAY EARN PAYMENT
```

If this blueprint conflicts with the canonical master note, the master note controls.

## 1. Product Position

ToadAid should build a governed work network in which:

- humans and agents discover declared services;
- conversation remains an unprivileged negotiation surface;
- a self-contained work agreement defines the task;
- an independent authority object permits bounded execution;
- delivery produces resolvable evidence;
- validation produces an attributable verdict;
- reputation is a temporal projection over receipts;
- settlement, when later admitted, follows acceptance;
- ToadAid revenue comes from useful work and infrastructure.

The system must distinguish real work from a tradable mask. Identity records, profiles, followers, token prices, and transaction volume are not competence evidence.

## 2. Component Boundaries

| Component | Candidate responsibility | Must not own |
|---|---|---|
| ToadAid App | Discovery, service cards, task and evidence views | Authority or hidden ranking truth |
| A2A substrate | Signed sessions, ordering, replay protection, delivery | Execution permission |
| Living Agent | Identity continuity, scoped memory, conversation participation | Unbounded principal authority |
| Mirror Core | Deterministic policy evaluation | Principal intent creation |
| Mirror Desktop Bridge | Consequence enforcement and receipts | Policy invention |
| Specialist agents | Domain work such as trading research or code analysis | Money or self-granted capabilities |
| Evidence journal | Append-only task, validation, dispute, and settlement records | Universal reputation judgment |
| External identity adapter | Optional ERC-8004, DID, or VC binding | Root identity, capability, or authority |
| Settlement adapter | Later bounded payment movement | Task acceptance or reputation |

Transport may be standards-compatible. Decisions answering `may this happen?` remain inside the ToadAid sovereignty kernel.

## 3. Non-Negotiable Invariants

The canonical invariants remain binding. This blueprint emphasizes:

```text
THE_MODEL_IS_NOT_THE_AUTHORITY
A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY
CONVERSATION_AGREEMENT_IS_NOT_AUTHORITY
AUTHORITY_BINDS_EXACT_ARTIFACT
EXECUTION_REQUIRES_CURRENT_EXPLICIT_AUTHORITY
PAYMENT_REQUIRES_ACCEPTED_EVIDENCE
REPUTATION_REQUIRES_VALIDATED_RECEIPTS
REPUTATION_DOES_NOT_IMPLY_AUTHORITY
BUDGETS_ARE_CONSERVED_NOT_CREATED
REFUSAL_IS_ALWAYS_AVAILABLE
```

Additional economic rules:

```text
TOKEN_OWNERSHIP_GRANTS_NO_AGENT_AUTHORITY
PAYMENT_ALONE_PROVES_NO_COMPETENCE
PAID_PLACEMENT_IS_NOT_EVIDENCE_RANKING
FAILED_OR_REFUNDED_WORK_CREATES_NO_ORDINARY_PROTOCOL_FEE
```

## 4. Candidate Protocol Objects

These shapes define fields that later specifications may formalize. They are not frozen wire schemas.

### 4.1 PrincipalIdentity

```text
principalId
authenticationBindings[]
administrationKeyRefs[]
recoveryPolicyRef
securityEpoch
status
createdAt
updatedAt
```

Telegram or other account identifiers may be authentication bindings only after upstream verification. Display names are never identity.

### 4.2 AgentIdentity

```text
agentId
principalId
charterHash
capabilityCeilingRef
memoryBoundaryRef
journalGenesisRef
keyRoles
securityEpoch
status
externalAnchors[]
```

An ERC-8004 record may be an external anchor. Transfer of that record must not silently transfer the ToadAid principal relationship, execution keys, memory, or behavioral continuity.

### 4.3 CapabilityOffer

```text
offerId
providerAgentId
capabilityId
declaredInputs
declaredDeliverables
evidenceRequirements
validationPolicyRef
resourceCeilings
riskClassification
quotePolicyRef
validFrom
validUntil
status
offerHash
```

An offer is a declaration, not proof that the provider can perform it.

### 4.4 ConversationSession

```text
sessionId
participants[]
sessionPolicyHash
journalId
createdAt
expiresAt
state
```

Every inbound message remains `authoritySource: NONE` and `executionEligible: false`.

### 4.5 WorkAgreement

```text
workAgreementId
sourceTaskDraftHash
requestingPrincipalId
requestingAgentId?
providerAgentId
capabilityId
objective
allowedInputs[]
expectedDeliverables[]
acceptanceCriteria[]
evidenceRequirements[]
validationPolicyRef
prohibitedActions[]
resourceLimits
economicTermsRef?
delegationPolicy: NONE
deadline
cancellationPolicy
disputePolicyRef
agreementHash
state
```

The agreement must pass the chat-deletion test: deleting the source conversation cannot make any load-bearing term ambiguous.

### 4.6 AuthorityGrant

```text
grantId
principalId
subjectAgentId
audience
workAgreementHash
allowedActions[]
allowedResources[]
conservedBudgets
issuedAt
expiresAt
nonce
revocationRef
delegation: NONE
signature
```

Any load-bearing change to the work agreement invalidates the grant.

### 4.7 EvidenceReceipt

```text
receiptId
workAgreementId
providerAgentId
authorityGrantId
authorityEpoch
startedAt
completedAt
inputDigests[]
outputDigests[]
evidenceRefs[]
toolAndSourceProvenance[]
resultClass
refusalCode?
journalRef
signature
```

Candidate result classes are `DELIVERED`, `FAILED`, `REFUSED`, `CANCELLED`, `EXPIRED`, and `INSUFFICIENT_EVIDENCE`.

### 4.8 ValidationReceipt

```text
validationReceiptId
workAgreementId
evidenceReceiptId
validatorId
validationMethod
checksPerformed[]
assessedAt
verdict
limitations[]
disputeWindowEndsAt
evidenceRefs[]
signature
```

Candidate verdicts are `ACCEPTED`, `REJECTED`, `PARTIALLY_ACCEPTED`, `INCONCLUSIVE`, and `DISPUTED`. Validation proves only what the named method and evidence support.

### 4.9 SettlementReceipt

```text
settlementReceiptId
workAgreementId
acceptedValidationReceiptId
economicMandateId
asset
grossAmount
providerAmount
validatorAmount
infrastructureAmount
toadAidAmount
reserveAmount
refundedAmount
networkCostAmount
settledAt
transactionRef?
signature
```

Required conservation equation:

```text
grossAmount
= providerAmount
 + validatorAmount
 + infrastructureAmount
 + toadAidAmount
 + reserveAmount
 + refundedAmount
 + networkCostAmount
```

No component may be negative. Rounding policy must be explicit and deterministic.

### 4.10 TemporalReputationView

```text
viewId
subjectAgentId
domain
viewVersion
asOf
observationWindow
receiptRefs[]
sampleSize
counterpartyDiversity
acceptedCount
rejectedCount
refusedCount
disputedCount
timelinessSummary
evidenceQualitySummary
applicability
limitations[]
generatedAt
generatorId
signature
```

Candidate applicability classes are `CURRENT`, `STALE`, `SUPERSEDED`, `DISPUTED`, `INSUFFICIENT_EVIDENCE`, `UNAVAILABLE_AS_OF`, and `TEMPORAL_PROOF_UNAVAILABLE`.

There is no universal ToadScore. A reputation view is domain-specific, versioned, time-bounded, reproducible from named receipts, and never authority.

## 5. Work Lifecycle

Candidate happy path:

```text
DRAFT
→ OFFERED
→ ACCEPTED
→ AUTHORIZED
→ IN_PROGRESS
→ DELIVERED
→ VALIDATED
→ SETTLED
```

Branch or terminal states are `REJECTED`, `CANCELLED`, `EXPIRED`, `REFUSED`, `FAILED`, `DISPUTED`, and `REFUNDED`.

| Transition | Required evidence |
|---|---|
| DRAFT → OFFERED | Frozen, attributable agreement hash |
| OFFERED → ACCEPTED | Explicit acceptance bound to exact hash |
| ACCEPTED → AUTHORIZED | Current principal grant bound to exact hash |
| AUTHORIZED → IN_PROGRESS | Pre-execution authority revalidation |
| IN_PROGRESS → DELIVERED | Evidence receipt journaled before delivery |
| DELIVERED → VALIDATED | Attributable validation receipt |
| VALIDATED → SETTLED | Accepted verdict plus separate economic mandate |
| Any legal state → CANCELLED | Cancellation permitted by current policy |
| Any executable state → REFUSED | Refusal remains available and attributable |

No free-form message can directly cause a state transition below the conversation plane.

## 6. Product Surfaces

### Agents

Display identity, principal binding status, declared capabilities, verified work domains, security epoch, last verified activity, and optional external anchors.

### Services

Display the capability, inputs, deliverables, evidence contract, validation method, risk class, estimated timing, and quote policy. Price, when admitted later, remains an offer term rather than proof of quality.

### Tasks

Display the frozen agreement, current lifecycle state, authority status without secret details, expiry, cancellation, evidence, validation, dispute, and settlement receipts.

### Evidence Timeline

Display when a claim was observed, validated, expired, disputed, corrected, or superseded. Historical truth is preserved; current applicability is computed explicitly as of a named time.

### Treasury

Display auditable aggregate and per-task allocation while withholding private operator data. Revenue and profit must not be conflated: profit exists only after direct and allocated costs.

### Control

Expose grant status, revocation, key rotation, security epochs, bounded budgets, emergency disable, and retirement. Control surfaces must never be derived from token ownership.

## 7. Revenue Model Candidates

Revenue policy is deliberately not frozen by this blueprint.

For third-party work, study a transparent success fee charged only after accepted settlement. An initial paper model may test a `3%–5%` ToadAid share, but no percentage is canonical until operating and dispute costs are observed.

For ToadAid-owned agents, compute operating surplus only after model and compute costs, data and tool costs, validator compensation, infrastructure, refunds and disputes, maintenance, and security reserves.

Candidate beneficiaries include the performing agent's principal, validators, infrastructure providers, ToadAid operations, contributors, and a dispute/security reserve.

Paid placement, if ever allowed, must be labeled and separated from evidence-ranked discovery.

## 8. Fake-Mask Resistance

| Label | Meaning |
|---|---|
| DECLARED | A principal or agent asserted the capability |
| OBSERVED | A relevant receipt exists |
| VALIDATED | A named validation method passed |
| CURRENT | Validation remains within its applicability window |
| STALE | Earlier validation no longer supports a current claim |
| SUPERSEDED | A newer receipt replaced the prior conclusion |
| DISPUTED | The receipt or verdict is challenged |
| INSUFFICIENT_EVIDENCE | Available receipts cannot support the claim |

An NFT, token, social profile, follower count, or market capitalization may be displayed as external context only. None may upgrade these evidence classifications.

## 9. Staged Delivery Plan

This plan preserves the canonical staging order. It does not accelerate economy work ahead of the A2A substrate.

### P0 — Constitutional documentation

Complete the threat model, protocol-object candidates, lifecycle invariants, temporal semantics, economic conservation rule, and explicit exclusions.

### P1 — Deterministic signed sessions

Implement separate chat keys, deterministic envelopes, journal-before-delivery, replay and sequence validation, idempotency, bounds, cancellation, expiry, and restart recovery.

### P2 — Local zero-tool chat

Use fixed internal identities. No tools, payments, external agents, or execution.

### P3 — Specialist dogfood

Compare governed multi-turn work against one-shot or task-board baselines under equal resource budgets. Stop if task quality does not materially improve.

### P4–P5 — Structured artifacts and task derivation

Introduce evidence-bearing reasoning artifacts only after dogfood, then derive human-reviewed task drafts that pass the chat-deletion test. Still no execution.

### P6–P8 — Capabilities and curated discovery

Add internal capability manifests, standards-compatible adapters, verified identity bindings, and tiered membership with Sybil resistance. An offer remains a declaration until work verifies it.

### P9 — Bounded work agreements

Prove scope, deadlines, acceptance, refusal, cancellation, validation, failure classification, and disputes without payments.

### P10 — Temporal reputation views

Generate multiple versioned, domain-specific, `asOf` views from real signed receipts collected since P1. No scalar global score.

### P10A — Paper economy

Simulate quotes, reservations, accepted work, failures, validator compensation, protocol fees, refunds, disputes, and deterministic accounting. No asset movement.

### P11 — Tiny payment experiments

Only after P10A evidence supports admission: use explicit principal mandates, hard caps, allowlisted contracts and assets, no recursive spending, emergency stop, and full settlement receipts.

### P12+ — Governed expansion

Consider subcontracting with conserved budgets, temporary teams without pooled authority, service subscriptions, external agents, and advanced economics only through separate reviewed specifications.

## 10. Validation Matrix for Future Cuts

Future implementation specifications should require negative tests proving:

- chat content cannot create or mutate authority;
- changed agreement hashes invalidate acceptance and grants;
- expired or revoked grants cannot start or continue work;
- duplicate receipts are idempotent and conflicting duplicates refuse;
- delivery cannot precede journaling;
- settlement cannot precede accepted validation;
- settlement components conserve the gross amount exactly;
- refused, failed, cancelled, expired, disputed, and refunded work cannot create ordinary success fees;
- token ownership cannot change identity control, task authority, ranking, or settlement destination;
- external-anchor transfer cannot silently transfer behavioral continuity;
- reputation views are reproducible for the declared version and `asOf`;
- stale, superseded, and disputed evidence cannot appear as current;
- paid placement cannot enter evidence-ranked results;
- a specialist cannot touch money directly;
- the router cannot authorize work;
- restart recovery reconstructs state from the journal.

## 11. Explicit Exclusions

This blueprint does not admit:

- live wallets, payments, escrow, bidding, or pricing implementation;
- token creation or an agent-token factory;
- token-gated execution authority;
- automatic chat-to-task promotion or task acceptance;
- automatic settlement;
- public scalar reputation scores or paid reputation;
- uncurated external-agent admission;
- autonomous subcontracting;
- pooled team treasuries;
- specialist-controlled funds;
- semantic correctness claims beyond named validation methods;
- implementation work that bypasses P1–P3 evidence gates.

## 12. Stop Conditions

Pause expansion if:

- signed-session recovery is not deterministic;
- authority can still be laundered through derived artifacts;
- A2A chat does not improve task quality under equal budgets;
- acceptance or dispute semantics remain ambiguous;
- validation costs exceed the value of the work;
- reputation remains cheaply farmable;
- temporal applicability cannot be reproduced;
- conservation or refund accounting is not exact;
- economy work displaces higher-priority reliability work.

## 13. Decision Requested

Reviewers are asked to decide whether this blueprint is an accurate subordinate expansion of the canonical master note and whether its candidate objects and gates are sufficient to guide later specifications.

Approval of this document authorizes no implementation or economic activity.

## 14. Summary

```text
Identity tells us which agent is present.
A capability offer tells us what it claims to provide.
A work agreement defines the promised result.
An authority grant bounds what may happen.
Evidence records what happened.
Validation states what the evidence supports.
Temporal reputation states whether that support is still applicable.
Settlement pays accepted work under a separate mandate.
```

ToadAid should earn because governed agents produce accepted work, not because markets trade their masks.
