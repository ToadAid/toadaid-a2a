# P0-WEB-02 — loopback content-negotiation fixture

**Status:** LOCAL SYNTHETIC PROOF ONLY — **NOT DEPLOYED, NOT PUBLIC, NO ACTIONS AUTHORIZED**.

This cut is a bounded implementation of the P0-WEB-01 [publishing blueprint](p0-web-01-agent-native-publishing-blueprint.md). It is not a new public agent-facing website, a live Agent Card, a lore export, an identity service or an execution system.

## What it actually implements

- An operator-initiated Python standard-library HTTP server **bound to IPv4 `127.0.0.1` only**. It is not started automatically, installed as a service, tunneled or reverse-proxied.
- Exactly one **local-only** content route: `GET /fixture/synthetic-lore-resource` (also `HEAD`).
- Reads only the existing explicit fictional example `contracts/agent-web/examples/synthetic-lore-resource.v0.json`. The source must declare `SYNTHETIC-NONCANONICAL-NOT-PUBLISHED`, not be a real deed, and have publication/ownership flags set to false. Otherwise the fixture refuses to render.
- The same allowlisted projection (`recordId`, `status`, `title`, `summary`, `claims`, `provenance`) drives **HTML**, **Markdown**, and **JSON** output. HTML and Markdown embed the exact corresponding projected JSON facts, so semantic parity can be tested without three separately maintained stories. Extra source fields, even if accidentally present, do not enter the output.
- Parses a bounded subset of the HTTP `Accept` header, including exact types, wildcard ranges and `q` quality weights. Defaults to HTML when unspecified. Returns 406 when none are acceptable, 400 for malformed/oversized headers, 404 for all other paths, and 405 for mutation methods.
- Sets accurate `Content-Type`, `Vary: Accept`, `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, a restrictive Content Security Policy and `X-Robots-Tag: noindex, nofollow`.
- Does not access external URLs, remote hosts, wallets, credentials, databases, protected hosts, user accounts, or other ToadAid repositories. No background work or production routing.

The Accept implementation is a deliberately conservative **fixture-level subset** rather than a complete RFC 9110 HTTP negotiation engine. This is a test of explicit representation equivalence, not a production content stack.

## Explicit localhost invocation

From a reviewed checkout in a developer-controlled environment:

```bash
set -uo pipefail
python3 -m unittest discover -s tests -v
python3 -m agent_web.publishing_fixture --port 0
# Prints LOCAL_SYNTHETIC_NOT_DEPLOYED http://127.0.0.1:<ephemeral-port>/fixture/synthetic-lore-resource
# Ctrl-C to end this explicitly started test server. Never expose through a tunnel.
```

To inspect while it is explicitly running, from the same host:

```bash
curl --noproxy '*' -fsS -H 'Accept: text/markdown' http://127.0.0.1:<port>/fixture/synthetic-lore-resource
```

Here `<port>` is a placeholder for the actual ephemeral port; the example is **not** a claim that any endpoint is currently live.

## Tests and safety limits

The automated suite starts the fixture only on localhost and terminates it after qualification. Tests check format parity at the parsed JSON level, `Vary`, no-store, Content-Type, HEAD, weighted Accept and `q=0`, bad headers, unknown discovery/action routes, non-GET mutation refusal, Host-header independence, HTML escaping, synthetic-only source gating, and allowlisted projection that excludes injected private fields.

**Not tested or approved here:**
- Real Tobyworld lore ownership/rights, actual deeds, Knowledge Forge retrieval, genuine source provenance, or any external publication.
- Authenticated/tenant-private content, tenant-aware caching, identity, consent, revocation, task execution, signed cards, real actions, and full A2A TCK compatibility.
- CDN behavior, production HTML/Markdown parity, all Accept grammar, SSR, streaming, rate limiting, or production DoS resistance.

The parent [plan](../../contracts/agent-web/publishing-plan.v0.json) remains `architecture-only-not-deployed`: its release flags must not be changed to true by this fixture.

## Next separately gated work

**P0-WEB-03** may prepare a real public-lore publishing dataset only after source/rights review and independent provenance verification. **P0B-C2** remains the official A2A TCK gate; this fixture does not make it pass. Any public DNS/Cloudflare/Portal/MCP/Agent0 integration requires a separate Director decision and production safety review.

**NO SPEECH GRANTS · ONE CUT · ONE PROOF · ONE DIRECTOR RULING.**
