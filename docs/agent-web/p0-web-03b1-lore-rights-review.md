# P0-WEB-03B1 — lore rights review intake (NO publication)

**Status: RIGHTS / PUBLICATION HOLD · NOT DEPLOYED · NO REAL LORE EXPORTED.**  
**Cut:** CUT-P0-WEB-03B1-20261030 · `ToadAid/toadaid-a2a` only.

## Why this cut exists

The [P0-WEB-03A source review](p0-web-03a-lore-source-inventory.md) confirmed the Lore Reader's **one canonical authored source**, `ToadAid/toadaid.github.io/lore/data.json`. The source is publicly accessible but our inspection did **not** find a blanket republication license or independently verified consent for republishing original lore and media on a new agent surface. The content and media rights remain **UNKNOWN**. The observed 132-record source is NOT shipped or copied into this cut.

This cut establishes an **offline intake and review classifier** so authorized custodians can collect scope and evidence references *without granting rights from chat, self-assertion, forged identity, a signature alone, or a local JSON file*. This is a safeguard for the later human decision—not a legal determination.

## Files and authority boundaries

- `contracts/agent-web/lore-rights-review-request.v0.schema.json`: versioned **design schema** for a bounded, untrusted local request. Its `$id` is illustrative, NOT a hosted schema endpoint.
- `contracts/agent-web/examples/synthetic-lore-rights-request.v0.json`: entirely fictional request with dummy Git SHA/source digest and unknown rights. Not a Tobyworld record or rights receipt.
- `agent_web/lore_rights_review.py`: stdlib-only, read-only local classifier; prints *only* a sanitized outcome and reason codes; never echoes people, source record IDs or private evidence references.
- `tests/test_lore_rights_review.py`: negative controls and synthetic claim tests.

The packet describes **what is requested**: `evaluate_metadata`, `evaluate_lore_text`, `evaluate_media_reference`, or `evaluate_media_binary`; intended public agent-facing audience; exact source generation and bounded record identifiers; and references to private evidence **not embedded in the public repo**.

The `source` must match an existing `agent_web.lore_provenance` inventory generated from a reviewed local Git object. The check binds repository/path, full commit, Git blob SHA-1, SHA-256 of actual source bytes, and count. A matching pair of **self-submitted files still does not authenticate the upstream maintainer or prove rights**. This cut cannot move the canonical Lore Reader import or replace its exact-Git-object source rules.

### Rights evidence distinctions

The operator may describe the following **unverified claims**: `unknown`, `restricted`, `disputed`, `permission_claimed`, or `public_domain_claimed`. No setting means "approved". References to potential permission, attribution, privacy, withdrawal, independent human attestation and media review are **opaque IDs for future human verification**, never documents or URLs to fetch. A claimed public-domain status is **not** a legal ruling.

Text, metadata, media references, and media binaries require separate scope analysis:
- Metadata evaluation cannot silently add `original`, `comment` or `img`.
- Lore text evaluation must explicitly include `original` or `comment`; preserve them as distinct canonical fields, not blended or reattributed text. Archive chronology remains distinct from publication time.
- Media reference evaluation is not media preservation. Legacy `img` is neither a verified artifact nor evidence of redistribution rights.
- **Media binary evaluation ALWAYS remains on independent HOLD**, even when all packet evidence claims look complete. A later rights/media artifact gate is required for any rehosting, thumbnails or derivatives.

## Verdicts, never grants

**`HOLD_NO_PUBLICATION`** means required binding, request shape, source policy or rights evidence is missing, uncertain or conflicting. Reasons are generic codes; the tool never prints user-supplied content or proof IDs.

**`READY_FOR_INDEPENDENT_HUMAN_REVIEW_ONLY`** means an untrusted packet has the required structure and claimed references. It is NOT a verification that evidence exists, that the claimant owns rights, that permission applies to the requested format/audience, or that an independent reviewer actually approved it.

**Both statuses ALWAYS set `publicationAuthorized=false`, `publicLoreExportEnabled=false`, `mediaRehostingAuthorized=false`, `rightsLegallyDetermined=false`, `rightsClearedByProgram=false`, `humanApprovalSatisfiedByPacket=false`, and `deploymentAuthorized=false`.** An exit code of 0 means an assessment was printed, never permission.

## Local, optional operator invocation — not run automatically

First generate a canonical source inventory from a *separately reviewed local* Git commit, outside the A2A repository:

```bash
set -uo pipefail
python3 -m agent_web.lore_provenance --canonical-repo /absolute/local/toadaid.github.io --commit FULL_REVIEWED_COMMIT > /private/inventory.json
python3 -m agent_web.lore_rights_review --inventory /private/inventory.json --packet /private/rights-review-request.json
```

Paths are **placeholders**, not checked user-machine paths; never put real rights evidence, correspondence, legal agreements, PII or private approval documents in the public Git repository or CI artifacts. Use a protected private store with human-controlled access for evidence documents. No network fetch, source export, file write, approval API or public route is implemented. The validator does not read or authenticate referenced proof documents.

To test with fictional inputs only: `python3 -m unittest discover -s tests -v`.

### Independent future decisions (not granted by this cut)

1. **P0-WEB-03B2:** An authorized rights custodian and independent reviewer evaluate real proof, rights chain, intended use, exact excerpt/fields, attribution, limitations, expiration, withdrawal/revocation, privacy, cross-border and rehosting requirements. Record an attributable, revocable decision outside the agent-chat channel.
2. Verify local canonical Git object origin with separately trusted maintainer/source evidence. Programmatic metadata equality is not proof of provenance or lawful reuse.
3. Only after a separate, recorded Director publication decision may a new local-only redacted export fixture be proposed; any real agent-facing deployment needs independent P0E review.
4. **P0B-C2 official A2A TCK remains UNRUN**. The last known manual attempt was SKIPPED; its gate has been repaired, but no official compatibility report is claimed.

No public endpoint, credential, Agent Card, Portal, MCP, Knowledge Forge, Agent0, Lore Reader, DNS, Cloudflare, wallet, on-chain transaction, host or service is changed by P0-WEB-03B1.

**PRESERVE THE LORE · EMPOWER THE PEOPLE · BUILD TOGETHER.**  
**ONE POND · MANY AGENTS · HUMAN SOVEREIGNTY.**
