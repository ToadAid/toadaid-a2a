# P0-WEB-01 — Agent-Native Publishing Blueprint v0

**Status:** DESIGN ONLY · **NOT DEPLOYED** · **NO ROUTES AUTHORIZED**  
**Cut:** CUT-P0-WEB-01-20261030 · **Repository:** `ToadAid/toadaid-a2a`  
**Authority:** the [canonical four-plane A2A architecture](../architecture/canonical-a2a-architecture-master-note-v0.md) and [P0A foundation](foundation-v0.md) take precedence. This blueprint creates no grant, runtime API, or permission.

## Decision and non-goals

Keep `portal.toadaid.org` human-first. Plan a separate, accessible, machine-native surface at `agent.toadaid.org`, with narrowly governed tools later at `mcp.toadaid.org`. Use widely interoperable HTTP and A2A conventions; do **not** invent a new required wire protocol. Visual human experiences—especially Lore Land artwork—remain first-class. Machines should receive an equally meaningful representation and source-linked metadata, not an image-only fact record.

This cut does **not** edit Portal, MCP, Agent0, Lore Reader, DNS, Cloudflare, host configs, A2A server code, payment flows, wallet state, production databases, or any protected execution plane. It does **not** serve a website, publish a real Agent Card, issue registration, install services, start background processes, authorize tools, or claim official A2A conformance. Existing P0B-C2 official TCK remains UNRUN.

## Ownership and the three publishing layers

| Layer | Proposed surface | Owner | Boundary |
| --- | --- | --- | --- |
| Discovery and policy | `agent.toadaid.org` | A2A discovery/public docs | Only advertise endpoints and skills proven operational and approved for publication. |
| Content substrate | Agent-facing public lore/resources | Lore Reader/Knowledge Forge source owners | Structured facts, citations, stable IDs, provenance and representation parity. |
| Actions and governance | Future typed proposal endpoints | Portal registration + independent authority service | Client descriptions are **not** grants; permissions are enforced server-side on every call. |
| Human experience | `portal.toadaid.org` | Portal | Community, profiles, human-readable privacy-filtered Observatory. |
| Governed tools | `mcp.toadaid.org` | MCP service operator | Tool eligibility, authentication, exact-grant checks; never inferred from an A2A message. |

The URLs above express **intended boundaries**, not tested DNS, deployed services, or a promise of uptime.

### Layer 1: discovery

- **A2A Agent Card**: candidate path `https://agent.toadaid.org/.well-known/agent-card.json`, once a fully qualified, real A2A interface and allowed skills exist. The card is an identity/discovery document, **not authorization**. Validate actual interface reachability, skill truthfulness, authentication claims and version before publishing. Until then do not expose a fake card.
- **`/llms.txt`**: optional, human-readable curated index of public documentation and links; **not** a mandatory A2A protocol feature, a privacy policy enforcement point, or proof that its links are accessible.
- **`/siteai.json`**: optional **experimental**, not a normative W3C Recommendation or authorization source. A future experiment must document the selected draft revision and independently enforce policy; a declarative file cannot grant capability.
- **Discovery fallback**: explicit configuration or approved registries may locate agents where well-known discovery is unsuitable. No agent is required to implement a proprietary ToadAid discovery file.
- Neither `robots.txt`, `llms.txt`, nor an agent policy manifest overrides authentication, tenant boundaries, revocation or private-data rules.

### Layer 2: content and representation

For *public, approved* resources, prefer stable canonical URLs and content negotiation:
- Browser request `Accept: text/html` → accessible static/SSR HTML, with meaningful headings and provenance.
- Reader request `Accept: text/markdown` → concise, semantically equivalent Markdown where supported.
- Machine record request `Accept: application/json` → explicit, versioned structured data where the resource has a published JSON representation.
- Respond with accurate `Content-Type`; if representations depend on Accept, use `Vary: Accept` and safe representation-specific cache keys, including authorization/tenant context for any non-public data.
- Unsupported Accept preferences should receive a defined HTTP negotiation outcome; never silently present a sensitive representation as a public one.
- Avoid User-Agent sniffing, bot-only factual divergence, JS-only content, duplicated contradictory Markdown forks, or invented performance metrics. Render the same underlying facts with different formats. Never make a graphic the **sole** carrier of required meaning; include accessible captions, source-linked metadata and factual data separately.
- Organize public nodes with a title, stable identifier, concise summary, citations/source pointers, updated/version markers, and a bounded set of genuinely relevant links. This is a **design convention**, not an adopted Agentic Internet Protocol or new mandatory graph standard.
- No raw internal prompt, model reasoning, owner secrets, unpublished contract, private journal, sensitive wallet data or community-only conversation may leak into public publishing.

#### Lore provenance taxonomy

Every machine-readable public lore assertion must indicate what kind of assertion it is:
- `original_lore`: attributable to a resolvable original published lore source.
- `onchain_metadata`: backed by an identified chain/contract/token reference **only after** independent verification; the record itself does not prove ownership.
- `community_creation`: attributable to its creator with explicit publication permission and rights.
- `imagined_visual`: artistic interpretation, never labeled canonical lore or verified chain fact.
- `editorial_summary`: derived text citing sources with a visible uncertainty/derivation label.

A record with unavailable evidence is `unverified` or withheld—not quietly promoted to `verified`. No real deed data is published in this cut. See the **explicitly synthetic, non-canonical** [example](../../contracts/agent-web/examples/synthetic-lore-resource.v0.json). The example provides schema inspiration only and must never be indexed as an actual Lore Land deed.

#### Public source links and rights

Use canonical source IDs, source URLs, publication timestamps and content revisions where known; avoid fabricating authorship, ownership, permits or licenses. When an image or document is not approved for public redistribution, link to an approved reference instead of copying it. Keep independent chain ownership checks distinct from lore authorship and user gallery claims. A source signature or data hash can support integrity but never substitutes for permission or truthfulness.

### Layer 3: typed action proposals (NOT IMPLEMENTED)

Future **read-only** publication requires only resource access control. Proposed future operations may include `request-community-admission`, `propose-task-draft`, and `request-read-capability`. Their names here are **examples**, not real routes or grants.

Every eventual stateful action needs:
1. A versioned OpenAPI/JSON Schema contract, explicit input/output type, error model and idempotency rules.
2. A server-authenticated principal, agent ownership/controller binding, effective tenant derived by trusted server policy (not client-supplied `tenant`), bounded scopes, rate/resource ceilings and revocation validation.
3. Separation of **request** from **approval** and **execution**: a chat statement, `siteai.json` field, Agent Card, signed message, token reputation or ERC-8004 identity cannot authorize a protected action.
4. A current exact-artifact authorization grant at the Authority/Execution boundary; for consequential operations, trusted human approval outside the agent message channel.
5. Journal-before-delivery, bounded evidence receipts and private/public projection rules. Public Observatory exposes only approved, redacted, independently resolvable summaries.

**Default action policy:** deny until independently enabled and tested. No universal "agent can act" toggle.

## Threats and implementation risks

Prevent SSRF through arbitrary `jku` or source URLs; reject prompt injection in Markdown/links as untrusted data; block cross-tenant cache and indexing leakage, policy-description-as-permission, Host-header-based identity substitution, malicious asset/redirect fetching, falsely advertised skills, stale ACLs, forged provenance, PII in logs/traces, unapproved writes, and cache poisoning. Control robots/indexing separately from actual authorization.

No analytics benchmark (token savings or RAG accuracy) is presumed. If useful, measure identical real ToadAid sources with HTML/Markdown/JSON and publish the method and limitations.

## Acceptance, release and future cuts

The [P0-WEB-01 gates](p0-web-01-acceptance-gates.md) cover only this blueprint, its architecture-only JSON plan, an intentionally synthetic example and tests. A passing static check validates guardrail **text and shape**, not service security.

Suggested follow-on cuts **require separate Director authorization**:
- **P0-WEB-02:** local-only static/SSR public-document fixture with HTML/Markdown representation parity and content-negotiation negative tests.
- **P0-WEB-03:** actual sourced public-lore export from an approved Lore Reader/Forge dataset, with rights/provenance review and private-data exfiltration tests.
- **P0B-C2:** separately execute the already-pinned official A2A TCK in an approved isolated environment; classify all MUST failures, no fake green status.
- **P0C:** Portal-owned identity/admission, principal/tenant/revocation controls.
- **P0E:** independent host, Cloudflare/DNS, privacy, security, incident-response and rollback approval before any public deployment.

**STOP** on ambiguous authority, unsupported factual provenance, incomplete permissions review, unexpected changed files, or non-green required CI. Every deployment remains independently approved.

**Preserve the Lore · Empower the People · Build Together.**  
**ONE POND · MANY AGENTS · HUMAN SOVEREIGNTY.**
