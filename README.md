# ToadAid A2A

Sovereign Agent-to-Agent conversation, task, authority, and evidence protocol for ToadAid.

This repository is architecture-first. The existing canonical constitution governs the small, local-only development prototypes; no production A2A gateway is deployed.

## Architecture documents

- [Canonical A2A Architecture Master Note v0](docs/architecture/canonical-a2a-architecture-master-note-v0.md)
- [Governed Work-Market Blueprint v0.1](docs/architecture/governed-work-market-blueprint-v0.1.md)

## Agent-Native Web foundation (P0A)

The [Agent-Native Web foundation](docs/agent-web/foundation-v0.md) defines the proposed public agent-facing surface at `agent.toadaid.org`, alongside Portal registration, MCP capabilities, and human-readable observability.

- [P0 acceptance gates](docs/agent-web/acceptance-gates-v0.md)
- [Machine-readable *architecture-only* topology](contracts/agent-web/topology.v0.json)
- Validate with `python3 -m unittest discover -s tests -v`

**Status: NOT DEPLOYED.** The topology is not an A2A Agent Card, registry API, authorization grant, hosted endpoint, or assertion that any service is live. A2A chat has no execution authority; all deployment and protected-host work requires a separate Director ruling.

## P0B-A — offline Agent Card inspector (local-only)

Run `python3 -m agent_web.card_inspector LOCAL_CARD.json` to inspect A2A 1.0 public-candidate card *structure* without network access. Read [P0B-A limitations and evidence](docs/agent-web/p0b-a-offline-discovery.md). A passing inspector result **does not** confirm conformance, endpoint availability, skill support, or authorization to publish. P0B remains incomplete.

## P0B-B — localhost JSON-RPC fixed-response probe

A **separately started, localhost-only** A2A v1.0 JSON-RPC `SendMessage` probe now serves an honest local Agent Card and one fixed-response skill. It is NOT Agent0, not externally reachable by design, and does not grant execution authority. Its input hash and output are journaled privately before delivery; no models, MCP tools, Portal registration, wallets, external endpoints or protected host operations are used.

- [P0B-B protocol pin, limitations, instructions and tests](docs/agent-web/p0b-b-loopback-probe.md)
- [Upstream release v1.0.1 pin](contracts/agent-web/a2a-upstream-v1.0.1.json)
- Run the local test suite with `python3 -m unittest discover -s tests -v`.

**NOT DEPLOYED.** Full P0B acceptance and independent official A2A conformance remain separate gates. Do not publicly serve the test Agent Card or reuse its loopback URL as a production interface.

## P0B-C1 — independent-process client smoke and official TCK readiness

A separate Python client process discovers and talks to our explicitly started **localhost-only** fixture without importing its server code. This is a narrow, controlled interoperability smoke, **not** an external SDK or official TCK conformance result.

- [P0B-C1 evidence, TCK pin and limitations](docs/agent-web/p0b-c1-interop-tck-readiness.md)
- [Pinned official TCK source and lockfile](contracts/agent-web/a2a-tck-pin-20261030.json)
- All safe, temporary localhost tests: `python3 -m unittest discover -s tests -v`

**TCK NOT RUN. P0B remains incomplete. NOT DEPLOYED.** No production Agent Card, real Agent0 connection, agent registration, public networking, or new execution authority is created.

## P0-WEB-01 — Agent-Native Publishing Blueprint (architecture only)

The [P0-WEB-01 publishing blueprint](docs/agent-web/p0-web-01-agent-native-publishing-blueprint.md) proposes discovery, safe public lore publishing, HTML/Markdown/JSON content negotiation, source/rights provenance, and action/consent boundaries without changing the human Portal.

- [Plan, architecture-only; NOT DEPLOYED](contracts/agent-web/publishing-plan.v0.json)
- [Explicitly fictional sample record; never a real deed](contracts/agent-web/examples/synthetic-lore-resource.v0.json)
- [Independent release gates](docs/agent-web/p0-web-01-acceptance-gates.md)
- Validate static invariants and all existing tests: `python3 -m unittest discover -s tests -v`

**NO ROUTES AUTHORIZED.** Neither the A2A Agent Card nor `/llms.txt`, `/siteai.json`, Markdown serving, lore JSON publishing, or actions are made public by this cut. P0B-C2 official TCK remains UNRUN.
