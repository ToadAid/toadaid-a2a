# P0-WEB-01 — Agent-Native Publishing Blueprint acceptance gates

**Status:** DOCUMENTATION / PLAN ONLY · **NOT DEPLOYED** · **NO SERVICE OR GRANT AUTHORIZED**.

## Scope of this cut

- [x] Public `toadaid-a2a` only; canonical architecture remains unchanged.
- [x] Keep human Portal, agent-native discovery, governed MCP and protected authority planes distinct.
- [x] Define honest discovery plan: A2A Agent Card conditional on operational proof; `llms.txt` optional; `siteai.json` experimental and non-authoritative.
- [x] Define HTML/Markdown/JSON publication contract, content negotiation, `Vary: Accept`, privacy-safe caching and format parity.
- [x] Define source/rights/provenance taxonomy and synthetic non-canonical lore example; **no real deed owner or lore claim**.
- [x] Define future typed-action consent/authorization boundary; publication cannot mint grants.
- [x] Architecture-only JSON plan and stdlib invariant/negative-control tests included.
- [ ] PR reviewed with exact head/base/title/seven-file scope and all CI green.
- [ ] Exact-head squash merge, verified new main and successful post-merge CI.

## Release facts

- `agent.toadaid.org` advertised Agent Card: **NOT PUBLISHED**.
- `/llms.txt`, `/siteai.json`, Markdown negotiation, lore JSON and action APIs: **NOT IMPLEMENTED OR PUBLISHED** by this cut.
- A2A official TCK: **NOT RUN**.
- Portal, MCP and Agent0 repos: **NOT CHANGED**.
- No production host, Cloudflare route, API credentials, ownership lookup, wallet transaction or service activation authorized.

## Future independent gates

1. Static/SSR fixture, actual HTTP content-negotiation and same-fact parity; malformed Accept, private cache and prompt-injection negative tests.
2. Rights/provenance review against real authoritative public source material; sensitive fields remain unpublished.
3. Actual A2A advertised capability verified with official TCK, separate Portal admission and governance.
4. Security/privacy review, resource limits, deployment/rollback plan and explicit Director authorization.

**Passing this cut cannot satisfy any future publication or production gate.**  
**ONE CUT · ONE PROOF · ONE DIRECTOR RULING.**
