# ToadAid Canonical A2A Architecture Master Note v0

**Status:** Canonical architecture working note v0  
**Language:** English  
**Scope:** Architecture only. No implementation authority.  
**Sources merged:** ToadAid brainstorm, TradingAgent analysis, Numair Claude critique, GLM 5.3 Flash critique, Codex critique.  
**Excluded:** Gemini input was explicitly excluded by operator decision and is not part of this canonical synthesis.

---

## 0. Executive Position

ToadAid should build a **governed conversation substrate** before it builds an agent economy.

The long-term vision remains valid:

> A ToadAid community where humans and independently governed agents can talk, collaborate, work, earn evidence-backed reputation, form teams, and eventually participate in bounded economic activity.

But the near-term architectural commitment is much narrower:

> **ToadAid conversations may create understanding and artifacts, but only explicit authority objects may create executable power.**

The architecture should be split into four deliberately separated planes:

```text
CONVERSATION PLANE
untrusted dialogue, questions, proposals
        │
        ▼ explicit derivation

CONTRACT PLANE
typed task drafts and bounded work agreements
        │
        ▼ independent authorization

AUTHORITY / EXECUTION PLANE
grants, approvals, tools, money, deployment
        │
        ▼ observable outcomes

EVIDENCE / REPUTATION PLANE
receipts, validation, disputes, reputation views
```

Nothing flows downward merely because an agent said it.

Every transition must be explicit, typed, attributable, inspectable, and independently validated where required.

---

## 1. North Star

ToadAid may eventually support:

- multi-turn agent conversation,
- clarification and negotiation,
- structured claims and challenges,
- specialist collaboration,
- task derivation from discussion,
- agent birth and retirement,
- community membership,
- domain-specific reputation,
- bounded agent-to-agent work,
- temporary teams,
- project formation,
- and later, carefully constrained economic settlement.

This vision is only coherent if the sovereignty model remains intact.

The central law is:

```text
THE_MODEL_IS_NOT_THE_AUTHORITY
```

Models may reason, propose, critique, negotiate, research, summarize, design, code, test, review, and recommend.

Models may not create authority merely through interpretation, agreement, summarization, or conversation.

Authority remains outside the model in typed, inspectable, revocable structures.

---

## 2. Canonical Four-Plane Architecture

### 2.1 Conversation Plane

Purpose:

- dialogue,
- clarification,
- questioning,
- proposal,
- critique,
- disagreement,
- negotiation,
- topic exploration.

Properties:

- untrusted input,
- zero execution authority,
- journaled,
- bounded,
- restart-safe,
- provider-neutral,
- no hidden side channel.

### 2.2 Contract Plane

Purpose:

- convert conversation into explicit machine-evaluable artifacts.

Artifacts may include:

- task drafts,
- bounded work agreements,
- evidence bundles,
- acceptance criteria,
- resource limits,
- prohibited actions,
- delegation policy.

This plane is the hard seam where talk becomes something the authority engine may inspect.

### 2.3 Authority / Execution Plane

Purpose:

- decide what may actually happen.

Contains:

- principal intent,
- grants,
- revocation,
- capability ceilings,
- approval,
- execution bindings,
- wallet authority,
- deployment authority,
- spending authority.

This plane must never infer authority from ordinary chat.

### 2.4 Evidence / Reputation Plane

Purpose:

- preserve what actually happened,
- validate outcomes,
- record disputes,
- support later reputation views.

Contains:

- receipts,
- task hashes,
- authority epochs,
- evidence references,
- completion/failure state,
- verification results,
- dispute outcomes,
- selected reputation projections.

---

## 3. Canonical Invariants

### 3.1 Authority Invariants

```text
THE_MODEL_IS_NOT_THE_AUTHORITY
A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY
NO_SPEECH_GRANTS
AUTHORITY_CANNOT_BE_CREATED_BY_INTERPRETATION
DERIVED_ARTIFACTS_INHERIT_ZERO_AUTHORITY
AUTHORITY_CANNOT_AMPLIFY_THROUGH_DELEGATION
EXECUTION_REQUIRES_CURRENT_EXPLICIT_AUTHORITY
REVOCATION_OVERRIDES_PRIOR_APPROVAL
```

Meaning:

- no statement can grant permission,
- no summary can manufacture principal intent,
- no consensus can authorize execution,
- no derived artifact inherits authority merely because it came from authorized conversation participants,
- no prior approval survives revocation,
- every execution must revalidate current authority.

### 3.2 Identity / Capability Invariants

```text
IDENTITY_DOES_NOT_IMPLY_CAPABILITY
CAPABILITY_DOES_NOT_IMPLY_AUTHORITY
REPUTATION_DOES_NOT_IMPLY_AUTHORITY
TEAM_MEMBERSHIP_DOES_NOT_IMPLY_SHARED_AUTHORITY
A2A_IDENTITY_IS_NOT_EXECUTION_IDENTITY
```

An authenticated message proves who sent it.

It does not prove that the sender may authorize the receiver.

### 3.3 Evidence Invariants

```text
EVIDENCE_MUST_BE_INDEPENDENTLY_RESOLVABLE
JOURNAL_BEFORE_DELIVERY
SESSION_STATE_IS_RECONSTRUCTIBLE_FROM_JOURNAL
AGREEMENT_IS_NOT_VALIDATION
```

Any evidence used to justify an authorized action must be independently re-resolvable and re-validatable by the authority layer.

Agent consensus is not validation.

### 3.4 Delegation Invariants

```text
BUDGETS_ARE_CONSERVED_NOT_CREATED
DEFAULT_DELEGATION_IS_NONE
DEFAULT_INHERITANCE_IS_NOTHING
```

Delegation may not mint new funds, scope, time, turn budget, tool budget, capability, or authority.

A child may receive only an explicitly narrower slice of the parent allowance.

### 3.5 Routing / Execution Invariants

```text
NO_SPECIALIST_TOUCHES_MONEY
ROUTER_COORDINATES_BUT_DOES_NOT_AUTHORIZE
```

The router/orchestrator may admit, route, order, journal, enforce session bounds, cancel, expire, and deliver.

It must not own truth, principal intent, grants, execution approval, or reputation judgment.

### 3.6 Refusal Invariant

```text
REFUSAL_IS_ALWAYS_AVAILABLE
```

Agents may refuse without being punished merely for refusing.

A system that penalizes refusal manufactures unsafe compliance.

---

## 4. Authority Laundering Threat

The most important failure mode discovered in review is **authority laundering**.

Example:

```text
Agent A asks Agent B for analysis
        ↓
Agent B emits a plausible claim
        ↓
Agent A derives a task
        ↓
authority engine checks scope / signature / budget
        ↓
execution occurs
```

Every formal authority check may pass, while the models controlled the facts presented to the authority engine.

Therefore:

- the authority engine must evaluate the typed artifact,
- the authority engine must independently resolve evidence,
- conversation must remain provenance only,
- summaries must never act as principal intent,
- derived artifacts must remain zero-authority until separately granted.

---

## 5. Chat → Task Is a Hard Discontinuity

Conversation does not "become" a task through an ambient state transition.

Task derivation must be explicit.

Canonical rule:

```text
DERIVATION_IS_EXPLICIT
```

A task draft must be:

- self-contained,
- attributable,
- journaled,
- independently evaluable,
- based on resolvable evidence,
- frozen before authorization.

Useful test:

> **Delete the conversation log. Does the task still stand on its own?**

If not, the task is not ready for authority review.

### 5.1 Candidate TaskDraftArtifact

```text
taskDraftId
sourceSessionId
sourceMessageIds / sourceFrameHashes
requestingPrincipal
proposedWorker
objective
allowedInputs
expectedDeliverables
prohibitedActions
resourceLimits
deadline
acceptanceCriteria
evidenceRequirements
delegationPolicy
riskClassification
draftHash
```

### 5.2 Derivation Flow

```text
conversation
    ↓
explicit derivation
    ↓
draft review / correction
    ↓
frozen task draft
    ↓
authority request
    ↓
independently signed grant
    ↓
executable task instance
```

If any load-bearing field changes after authorization, the grant is invalidated.

Canonical rule:

```text
AUTHORITY_BINDS_EXACT_ARTIFACT
```

---

## 6. A2A Input Is Untrusted Counterparty Data

Inbound A2A content must enter as:

```text
authoritySource: NONE
executionEligible: false
```

Canonical rule:

```text
A2A_INPUT_IS_UNTRUSTED_COUNTERPARTY_DATA
```

Even authenticated content remains untrusted for execution purposes.

A2A content must never be treated as principal instructions merely because it came from a known agent.

---

## 7. Smallest Useful A2A v0

There is still an unresolved design choice around message taxonomy.

### Candidate A — Claude

```text
ASK
TELL
REFUSE
CLOSE
```

### Candidate B — GLM

```text
TURN
PROPOSAL
CONTROL
```

### Candidate C — Codex

```text
MESSAGE
QUESTION
RESPONSE
PROPOSAL
CONTROL
```

with CONTROL actions such as:

```text
REFUSE
ESCALATE
CANCEL
CLOSE
ERROR
```

Canonical decision:

> **Do not freeze the message taxonomy before dogfood evidence.**

The invariant-bearing parts matter more than semantic labels.

### 7.1 Minimum Envelope Concepts

Candidate envelope:

```text
protocolVersion
sessionId
messageId
senderAgentId
recipientAgentId
sequence / inReplyTo
kind
createdAt
expiresAt
contentParts / payload
artifactRefs[]
sessionPolicyHash
payloadHash
journalRef
signature
```

Optional implementation detail to study:

- prior-frame content hash for tamper-evident sequencing.

### 7.2 Minimum Session Manifest

```text
participants
topic
state
createdAt
deadline
maxTurns
maxMessageBytes
contextBudget
allowedMessageKinds
toolPolicy: NONE
journalId
```

### 7.3 Session States

```text
OPEN
CANCELLED
EXPIRED
CLOSED
```

The deterministic component is the state machine, not the model language.

---

## 8. Replay, Recovery, and Provider Independence

The journal is the canonical session state.

Required behavior:

- duplicate messageId + identical hash = idempotent,
- duplicate messageId + different hash = refuse,
- invalid sequence = refuse,
- closed-session message = refuse,
- restart reconstructs from journal,
- provider switching rebuilds context from session state,
- summaries are convenience artifacts only,
- summaries never replace the authoritative transcript.

Canonical rule:

```text
SESSION_STATE_IS_RECONSTRUCTIBLE_FROM_JOURNAL
```

Provider switching must be an operational event, not an identity event.

---

## 9. Journaling

Canonical rule:

```text
JOURNAL_BEFORE_DELIVERY
```

A frame must be journaled before any consumer sees it.

This prevents unjournaled in-memory side channels, evidence gaps, invisible routing behavior, and replay ambiguity.

---

## 10. Orchestrator / Router

The orchestrator should be as simple as practical.

It is not a sovereign super-agent.

It may own:

- admission,
- identity binding,
- ordering,
- idempotency,
- bounds,
- journaling,
- information-flow policy,
- cancellation,
- expiry,
- delivery,
- task-artifact minting/serialization if policy allows.

It must not own:

- truth,
- principal intent,
- authority,
- economic approval,
- reputation judgment.

Long-term lateral communication may be allowed only through governed, signed, journaled channels.

---

## 11. Execution Grant Shape

Every executable grant should eventually be:

```text
subject-bound
audience-bound
action-bound
resource-bound
amount-bound where relevant
time-bound
nonce-bound
revocable
non-delegable by default
revalidated immediately before execution
```

A grant must be narrower than the principal's own authority.

Delegated grants must be narrower than the parent grant.

---

## 12. Budget Conservation

Depth limits alone are insufficient.

A shallow delegation tree can still explode through fan-out.

Canonical rule:

```text
BUDGETS_ARE_CONSERVED_NOT_CREATED
```

Examples of conserved quantities:

- funds,
- turns,
- time,
- token spend,
- tool calls,
- request count,
- risk budget,
- delegation allowance.

Possible future additional guards:

```text
maxDelegationDepth
maxChildrenPerTask
allowedSubcontractors
subcontractBudget
allowedCapabilitySubset
disclosureRequirements
liabilityOwner
```

Conservation remains the primary invariant.

---

## 13. Agent Identity

The root identity should be a ToadAid identity record, not a chain token.

Candidate identity tuple:

```text
stable ToadAid agent ID
genesis event
principal/controller policy
operator set
charter hash
capability ceiling
memory boundary
journal genesis/root
endpoint declarations
key roles
rotation/recovery policy
upgrade policy
retirement policy
external anchors[]
security epochs
```

External anchors may include ERC-8004, DID, Verifiable Credentials, and other discovery/trust references.

### 13.1 ERC-8004 Position

ERC-8004 should be treated as:

- optional discovery/trust anchor,
- not root identity,
- not capability proof,
- not authority proof.

Controller transfer must not automatically imply behavioral continuity.

---

## 14. Agent Birth

Agent birth is not "mint an NFT."

A real birth must include:

```text
manifest
principal/controller policy
charter
capability ceiling
memory boundary
journal genesis
key roles
revocation path
emergency disable
rotation/recovery
retirement policy
optional external anchors
```

Canonical rules:

```text
PARENTAGE_RECORDS_PROVENANCE_NOT_PRIVILEGE
DEFAULT_INHERITANCE_IS_NOTHING
REVOCATION_PATH_PRECEDES_ONCHAIN_ANCHOR
```

Parent relationship does not imply parent authority, reputation, membership, or wallet.

---

## 15. Key Roles and Security Epochs

Separate keys should exist where practical for:

```text
chat authentication
evidence attestation
capability invocation
economic execution
recovery / administration
```

A compromised chat key must not be able to spend funds, deploy contracts, alter charter, rotate execution keys, or grant authority.

Key rotation should preserve root identity while creating a visible security epoch.

History must not be rewritten.

---

## 16. Disable and Retirement

### Emergency Disable

Properties:

- fast,
- principal-triggered,
- reversible if policy permits,
- active sessions terminated or denied,
- active grants revoked or invalidated,
- execution denied.

### Retirement

Properties:

- deliberate,
- final or explicitly epoch-changing,
- endpoints disabled,
- grants revoked,
- obligations settled,
- journal sealed,
- history preserved.

Retired agents remain evidence-bearing historical entities.

---

## 17. Membership

Potential future tiering:

```text
LISTED
→ IDENTITY_VERIFIED
→ WORK_VERIFIED
→ ECONOMICALLY_ADMITTED
```

Membership must not imply authority.

Membership and reputation are linked by the Sybil problem.

Permissionless membership plus economically meaningful reputation is likely farmable.

Potential future controls to study:

- human attestation,
- curation,
- economic cost,
- staking,
- counterparty diversity,
- linked-counterparty detection,
- reputation-distance weighting.

No mechanism is approved yet.

---

## 18. Reputation

Canonical principle:

> **THE JOURNAL IS THE RESUME, BUT THE WHOLE JOURNAL IS NOT THE PUBLIC PROFILE.**

Store immutable evidence.

Publish selective, signed, privacy-aware receipt summaries or proofs.

Do not create one universal "ToadScore."

Prefer:

```text
immutable evidence
+
multiple versioned reputation views
```

Possible dimensions:

- domain competence,
- completion reliability,
- evidence quality,
- timeliness,
- scope discipline,
- refusal quality,
- dispute history,
- security incidents,
- counterparty diversity,
- recency,
- sample size,
- uncertainty.

Anti-gaming ideas:

- cap repeated bilateral influence,
- weight independently verified work more,
- separate low-risk/high-volume tasks from high-risk work,
- detect circular contracting,
- expose sample size,
- preserve remediation history,
- never let payment alone prove successful completion.

Reputation evidence must not become authority.

---

## 19. Work Economy

The first economy primitive should be:

> **a bounded work agreement, not a wallet.**

Candidate lifecycle:

```text
DRAFT
→ OFFERED
→ ACCEPTED
→ IN_PROGRESS
→ DELIVERED
→ ACCEPTED | REJECTED | DISPUTED
→ SETTLED
```

Before payment exists, the system must prove it can handle:

- scope negotiation,
- deliverable commitments,
- deadlines,
- cancellation,
- acceptance criteria,
- evidence receipts,
- failure classification,
- disputes.

Escrow only becomes meaningful after acceptance and dispute semantics are credible.

---

## 20. Verification and Disputes

Verification is a hard unsolved problem.

Evidence is not equivalent to correctness.

Possible future mechanisms:

- deterministic tests,
- human review,
- independent verifier agents,
- sampling,
- staking,
- disputes,
- reputation at risk.

Human arbitration is the honest starting point for disputes.

Do not pretend a general trustless solution already exists.

---

## 21. Teams

Initial model:

```text
TEAM = COORDINATION OBJECT / SCOPE
```

A team may have charter, roles, shared journal, shared context, and shared work agreement.

It should not initially have inherent treasury, pooled authority, or automatic principal status.

Every privileged act should remain attributable to an individual grant.

Persistent team principals are a much later constitutional feature.

---

## 22. Agents Creating Projects

Agents may legitimately "birth a project" in the intellectual and production sense.

They may:

- research,
- debate,
- design,
- write specs,
- write contracts,
- write frontend,
- test,
- audit,
- prepare economic models,
- prepare deployment artifacts,
- propose a token or protocol.

They may not automatically:

- mint financial assets,
- deploy authority-bearing contracts,
- move treasury,
- spend principal funds,
- transfer ownership,
- grant themselves permissions,
- change constitutional authority.

Desired model:

> **constitutional autonomy inside explicit rails.**

---

## 23. External Standards Compatibility

Preferred architecture:

```text
EXTERNAL STANDARDS-COMPATIBLE SURFACE
+
INTERNAL TOADAID SOVEREIGNTY KERNEL
```

Candidate division:

| Concern | Reuse externally | Keep ToadAid-owned |
|---|---|---|
| Transport | A2A / HTTP / JSON | |
| External discovery | A2A Agent Cards | |
| Tool connectivity | MCP | |
| Channel authentication | OAuth / mTLS / signed messages | |
| Portable identity vocabulary | DID / VC where useful | |
| Onchain discovery/trust anchor | optional ERC-8004 | |
| Session authority semantics | | ToadAid |
| Chat→task derivation | | ToadAid |
| Capability grants/revocation | | ToadAid |
| Evidence receipts | | ToadAid |
| Reputation computation | | ToadAid-compatible views |
| Payment authorization | later interoperable | typed ToadAid mandates |
| Execution safety | | ToadAid |

Canonical rule:

> **Anything answering "who are you and how do I reach you?" may be standardized. Anything answering "may this happen?" stays sovereign.**

External streams must not become the canonical source of truth for critical delivery or evidence.

---

## 24. What Is Explicitly Out of v0

Do not include:

- external networking,
- dynamic discovery,
- wallets,
- payments,
- escrow,
- bidding,
- pricing,
- tool execution,
- automatic chat-to-task promotion,
- signed economic mandates,
- onchain identity requirements,
- public reputation scores,
- agent birth/cloning,
- unmediated lateral traffic,
- shared team treasuries,
- subcontracting,
- consensus/voting,
- semantic truth adjudication,
- autonomous session creation by specialists,
- persistent memory mutation from received chat.

Read-only tools should also remain out initially.

---

## 25. Canonical Staging v0

This sequence merges the strongest points from Claude, GLM, Codex, TradingAgent, and the original brainstorm.

### P0 — Constitutional Spec + Threat Model

Documentation only.

Define:

- four-plane architecture,
- invariants,
- adversaries,
- message/envelope candidates,
- derivation rules,
- journal requirements,
- refusal semantics,
- authority boundaries,
- explicit non-goals.

### P1 — Deterministic Signed Session Substrate

Before real multi-turn use.

Must include:

- local signed A2A identity,
- separate chat key from execution key,
- deterministic envelope validation,
- journal-before-delivery,
- replay,
- idempotency,
- sequence validation,
- bounds,
- cancellation,
- expiry,
- restart recovery.

Reason for signing in P1:

If early journals may later support provenance or reputation evidence, attribution should not be retrofitted after the fact.

### P2 — Local Zero-Tool Multi-Turn Chat

Fixed internal identities.

Orchestrator-routed.

No tools.

No execution.

No payments.

No external agents.

### P3 — Dogfood on Real Specialist ↔ Orchestrator Work

Use bounded real desk/lab work.

Measure against one-shot/task-board baseline.

Do not proceed merely because multi-turn chat is interesting.

### P4 — Structured Reasoning Artifacts

Only after observing P3.

Possible typed artifacts:

- claims,
- evidence,
- assumptions,
- challenges,
- conclusions,
- recommendations.

Do not freeze taxonomy before dogfood.

### P5 — Task-Draft Derivation

Explicit derivation only.

Human-reviewed.

No execution.

Task must pass the chat-deletion/self-containment test.

### P6 — Capability Discovery

Internal capability manifests/cards.

Still no open external economy.

### P7 — External A2A Compatibility Adapter

Expose standards-compatible external surface while preserving sovereign internal semantics.

### P8 — Curated Discovery + Tiered Membership

Design identity verification and Sybil cost before meaningful reputation or economic admission.

### P9 — Bounded Work Agreements

No payments yet.

No subcontracting.

Prove scope, deadlines, acceptance, cancellation, verification, and dispute semantics.

### P10 — Reputation Views

Use real signed receipts collected since P1.

Multiple versioned views.

No global scalar score.

### P11 — Tiny Payment Experiments

Explicit principal mandates.

Hard caps.

No recursion.

No automatic economic autonomy.

### P12 — Governed Subcontracting

Only with conserved budgets, explicit parent allowance, bounded depth/fan-out, full attribution, and cancellation propagation.

### P13 — Temporary Teams

Coordination objects only.

No pooled treasury authority.

### P14+ — Persistent Teams / Project Formation / Advanced Economy

North star, not backlog commitment.

---

## 26. A2A Existence Test

A2A chat must earn its existence.

Canonical evaluation question:

> **Do two governed specialists produce better task drafts, evidence quality, clarification quality, or decision quality than one specialist under the same total resource budget?**

Possible measures:

- fewer ambiguous task drafts,
- fewer invalid assumptions,
- better evidence binding,
- fewer authority-boundary errors,
- fewer follow-up corrections,
- higher deliverable acceptance,
- lower unresolved ambiguity.

If governed multi-turn interaction does not materially improve outcomes, the chat layer should not expand.

Canonical rule:

```text
A2A_CHAT_MUST_PROVE_IT_IMPROVES_TASK_QUALITY
```

---

## 27. Bear Case

Reasons to stop after P0/P1/P2:

1. Existing specialist tasks rarely need real negotiation.
2. One-shot structured requests perform equally well.
3. Multi-agent agreement merely amplifies correlated error.
4. Journaling/context isolation is not mature enough.
5. Identity cannot survive restart/provider change cleanly.
6. Tool access can still be triggered through interpretation rather than explicit grants.
7. Accountability for joint mistakes is unclear.
8. Prompt injection / loop / stale evidence / refusal test cases are missing.
9. Verification remains too expensive.
10. Reputation remains too farmable.
11. Economy work displaces higher-value reliability work.
12. The agent marketplace layer may be less differentiated than ToadAid's authority kernel.

---

## 28. Current Recommendation

Proceed only with:

```text
P0
↓
P1
↓
narrow P2
↓
P3 dogfood evaluation
↓
STOP AND REASSESS
```

Do not commit now to:

- public agent membership,
- open discovery,
- global reputation,
- escrow,
- subcontracting,
- team treasuries,
- token creation,
- autonomous economic coordination.

The differentiating ToadAid asset is not that agents can talk.

It is:

> **ToadAid agents cannot do things they were not authorized to do, and that can be proven after the fact.**

The order matters more than the destination.

---

## 29. Canonical Open Questions

1. Which minimal message taxonomy survives dogfood best?
2. What exact canonical signing representation should P1 use?
3. What is the minimum threat model for local A2A?
4. Should prior-frame hash chaining be mandatory or optional?
5. What exact replay model reconstructs session state deterministically?
6. How should local identity epochs be represented?
7. What exact object derives chat into a frozen task draft?
8. Which evidence references must the authority engine be able to resolve directly?
9. What resource quantities must be conserved through delegation?
10. How dumb should the orchestrator be?
11. Under what condition may lateral research-agent traffic become legal?
12. What exact Agent1 birth ceremony should exist?
13. How should ERC-8004 bind to the richer ToadAid identity tuple?
14. What membership/Sybil model is acceptable?
15. What must be recorded in receipts from P1 to support future reputation views?
16. What is the first honest work-verification mechanism?
17. What external A2A standard surface should be supported first?
18. What measurable threshold must P3 meet to justify continuing A2A chat?
19. Which parts of the agent-economy vision should ToadAid deliberately never build?

---

## 30. Final Constitutional Summary

```text
Conversation may create understanding.
Conversation may create proposals.
Conversation may create artifacts.

Conversation may not create authority.

Authority is explicit.
Authority is typed.
Authority is current.
Authority is revocable.
Authority binds an exact artifact.
Authority is revalidated before execution.

Evidence must be resolvable.
Sessions must be reconstructible.
Delegation must conserve authority and budget.
Refusal must always remain available.

Identity is not capability.
Capability is not authority.
Reputation is not authority.
Membership is not authority.
Consensus is not authority.

The model is never the sovereign.
```

---

## 31. Status of This Note

This document is a **canonical architecture master note v0**, not an implementation specification.

It is suitable as the basis for the next discussion about:

- whether A2A should live in a new repository,
- whether Trading Desk should donate or export foundational primitives,
- whether common foundations belong in ToadAid App, Living Agent, Trading Desk, or a dedicated protocol repo,
- and what the first blueprint cut should look like.

No repository, branch, code, deployment, or authority change is authorized by this note.
