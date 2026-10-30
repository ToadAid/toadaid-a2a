# ToadAid A2A

Sovereign Agent-to-Agent conversation, task, authority, and evidence protocol for ToadAid.

This repository is intentionally bootstrapped documentation-first. The architecture is governed by reviewed specifications before implementation code is introduced.

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
