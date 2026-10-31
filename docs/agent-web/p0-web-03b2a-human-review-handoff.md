# P0-WEB-03B2A — independent human rights-review handoff

**Status:** STRUCTURE / SOURCE-SCOPE BINDING ONLY · **NOT A RIGHTS DECISION** · **NOT DEPLOYED**.  
**Cut:** CUT-P0-WEB-03B2A-20261030 · A2A public repository only.

## Director question

What is needed before agents can retrieve real Tobyworld lore, beyond an untrusted rights claim? The [P0-WEB-03B1 intake](p0-web-03b1-lore-rights-review.md) can check the shape and claimed evidence references of a request, but **cannot authenticate a rights owner, a reviewer, legal permission, or an authorization artifact**. This cut adds an offline *handoff* for independent human adjudication while preserving those limits.

**This is not completion of P0-WEB-03B2's real human rights decision.** No actual owner, custodian, author or reviewer has submitted an authenticated rights determination in this cut. The existing canon remains `ToadAid/toadaid.github.io/lore/data.json`; the A2A repo has no authority to amend it. Public accessibility is not automatic permission to duplicate original lore or media.

## Three separate roles and decisions

1. **Requesting agent / project operator:** requests precise source generation, record IDs, fields, intended audience and purpose. Agent and chat submissions are untrusted and cannot be permissions.
2. **Custodian / rights-holder and independent human reviewer:** establish who holds relevant rights, verify actual proof and attribution, assess permitted scope and duration, conflicts, privacy, objections, withdrawal/revocation and any media-specific rights. The reviewer identity and independence must be verified **outside chat and outside the public A2A repo**.
3. **Director / production operator:** independently judges release readiness *after* documented rights decisions and protocol/security/privacy gates, and separately approves any governed export/deployment. Neither a human-review worksheet nor rights consent automatically authorizes a server or MCP action.

A real rights decision requires evidence that *actually* supports the requested use; an apparent human signature, machine-generated digest, uploaded JSON packet or opaque evidence identifier is never sufficient by itself.

## The handoff contract (not an approval contract)

- `contracts/agent-web/lore-human-review-handoff.v0.schema.json`: versioned **local-only design** shape; its URN is not a live hosted URL or credential.
- `contracts/agent-web/examples/synthetic-human-review-handoff.v0.json`: intentionally invalid, purely fictional, unapproved case with unresolved objections, fake digests and no reviewer evidence. Never repurpose as a real case.
- `agent_web/lore_human_handoff.py`: stdlib read-only local checker. It binds its submitted docket to the exact canonical-source `sourceDigest`, Git blob identity, and a SHA-256 of the actual B1 request's deterministic JSON encoding. It also calls the existing B1 intake classifier and will not advance an incomplete request.
- `tests/test_lore_human_handoff.py`: synthetic negative controls, including mismatched digests, unknown stages, wrong channel, missing reviewer evidence, media scope, objections, withdrawal and input smuggling.

The hash binds the **bytes of the submitted logical request**. It does not cryptographically authenticate the submitted source as published by its owner, validate rights evidence, prove a human signature, or establish a revocation registry.

### Review docket evidence references

Only short, opaque **private evidence references** are admitted (never proof text or URLs): reviewer identity, reviewer independence, rights chain, permission scope, attribution, privacy, withdrawal plan, conflicts disclosure, and a media evidence reference when a media operation is requested.

All supplied references can be fabricated by the submitter. This tool tests structural completeness only. The actual document custody, signatures where appropriate, rightsholder attestations, reviewer independence, rights scope, expiration, disputes, affected parties, attribution format, commercial/derivative limits, jurisdiction and withdrawal response must be reviewed by authorized humans in a protected system.

### Refusal and objection preservation

- `HOLD_INDEPENDENT_HUMAN_REVIEW`: B1 intake not ready, mismatched source/request, missing pointers, unresolved objections, wrong review channel, withdrawn/declined case, unknown stage (including `approved`/`published`) or invalid shape.
- `STRUCTURALLY_READY_FOR_HUMAN_REVIEW_ONLY`: a claimed B1 packet plus local docket contains the requested references, matching self-submitted hash and *no stated* unresolved objections. **It is not an independent human decision or a source of permission.**
- **Objections remain visible as reason codes.** A caller cannot label a case approved, silently ignore an objection or reanimate a declined/withdrawn case by assigning a publication flag.
- The tool never emits the packet, record ID, evidence references, human identities, private documents or legal determinations. It never sets a public export, media rehosting, rights clearance, approved grant or deployment flag to true.

A false or fabricated `objectionCodes: []` list does **not** prove objections are resolved: only an external human-controlled review record can establish that.

## Operator-local demonstration (synthetic or private only)

```bash
set -uo pipefail
python3 -m unittest discover -s tests -v
python3 -m agent_web.lore_human_handoff \
  --packet /private/review-request.json \
  --inventory /private/local-source-inventory.json \
  --docket /private/review-handoff.json
```

The paths above are placeholders for independently protected local documents; **do not upload private documents, signed agreements, correspondence, identity details or real human reviewer records to this public repository**. The command does no network fetching, writes no files, and returns sanitized JSON with all authority flags false. Exit 0 means only that an assessment was printed, not that the review passed.

## Human review checklist (outside this repo)

The future reviewer records, in an independently controlled review system, a **specific, attributable and revocable** decision for each requested material category. The review must establish:

- **Authenticity:** verified source/custodian and exact approved Git generation, not merely a matching local `origin` string.
- **Chain of rights:** who actually owns/controls publication and reuse rights for original passages, commentary, photographs or artworks; assess third-party contributions individually.
- **Use:** which exact content, excerpts, fields, audience, territory, redistribution, derivatives and commercial use are permitted or restricted.
- **Attribution and privacy:** required author/source credit, publicity preferences, third-party privacy, redaction, and conflict-of-interest handling.
- **Life cycle:** expiration, cancellation/withdrawal, objections and dispute handling, preservation vs public display, incident response and takedown.
- **Independent final gate:** documented Director ruling for a *separate* read-only, local redacted export proof before any public agent-readable route. Real media binaries require an additional distinct gate.

A project maintainer's approval to build software does **not** automatically grant republication rights to someone else's text or artwork.

## Stop boundaries / next cuts

**P0-WEB-03B2B (human-held):** obtain real scoped rights and independent reviews outside agent chat; no claim that this cut completes it. **P0-WEB-03C (future):** only after recorded decisions, propose an approved narrow local export fixture. **P0E:** independent privacy/security/host/DNS/rollback approval before any public deployment. **P0B-C2:** official A2A TCK has still not run successfully; the one skipped manual workflow is not conformance evidence.

**No human approval obtained · no source text copied · no media exported · no domain/service changed · no authorization granted.**

**ONE POND · MANY AGENTS · HUMAN SOVEREIGNTY.**
