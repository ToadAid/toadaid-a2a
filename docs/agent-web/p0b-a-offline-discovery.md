# P0B-A — offline discovery inspection (structural profile only)

**Status:** local-only prototype, no web service. **NOT DEPLOYED.** The P0B discovery gate is **partially implemented, not accepted**. No live Agent Card is published.

## Why this first slice

A2A 1.0 discovery describes real agent skills and actual supported protocol-binding interfaces. This repository does not yet host an A2A interface or Agent0 connection. Publishing a card would falsely advertise service. P0B-A instead builds the offline safety/profile inspector that will later guard proposed public Agent Cards.

## Inputs and outputs

- Read one **local** UTF-8 JSON file, at most 65,536 bytes; no HTTP fetch, DNS resolution, server socket, deployment, credentials, model or MCP access.
- Run: `python3 -m agent_web.card_inspector /path/to/card.json`.
- Exit 0: `PROFILE_SHAPE_OK_UNVERIFIED`; **not** valid protocol conformance, approved admission, host ownership, endpoint availability, reachability, advertised-skill truthfulness or publication authority.
- Exit 1: rejected structural profile. Exit 2: usage error. Input contents and credential values are not displayed.
- Accept only this conservative **public candidate profile**: HTTPS domain endpoints (no IPs, localhost, embedded credentials, query or fragment), A2A `1.0` per-interface `protocolVersion`, standard `JSONRPC`, `GRPC` or `HTTP+JSON` binding, bounded cards and required structural fields. This is not a complete, general-purpose A2A validator.
- Reject duplicate JSON keys, legacy top-level v0 fields, unsafe or missing endpoints, duplicate/empty skills, unsafe security references, and credential-shaped fields. Other semantic checks remain for official schema qualification and live proof.

The test uses an `example.org` **synthetic in-memory fixture** which has no service behind it. Its structural acceptance is explicitly **not** proof of a real agent, service, skill or usable endpoint. Nothing in the repository should serve or register it as an Agent Card.

## Sources checked (2026-10-30)

Official A2A specification: https://a2a-protocol.org/latest/specification/

Agent Card well-known path: `/.well-known/agent-card.json`. In A2A v1.0, `supportedInterfaces[]` carries the actual endpoint, `protocolBinding` and `protocolVersion`; top-level v0 `url` and `preferredTransport` are not used. See specification sections **4.4**, **8** and **9–11**.

**Pinning decision:** this prototype intentionally accepts per-interface `protocolVersion == "1.0"`, but the official spec's moving `latest` URL is a *documentation pointer*, not a frozen schema artifact. A future implementation cut must pin a specific upstream release, source hash, official JSON schema/SDK and execute formal conformance tests. Do not claim official conformance from this limited inspector.

## Next cut: P0B-B (separate Director authorization)

- Pin a concrete official A2A release and schema checksum.
- Implement a loopback-only, **actual supported A2A binding**; advertise only backed interfaces and verified skills.
- Verify zero external exposure, restart behavior, no unapproved writes and negative malformed-card handling.
- Validate with upstream conformance checks before any publication; fail closed on unsupported behavior.
- Separate security/Portal/production review before public exposure, identities or log publication.

**Canonical invariants remain authoritative:** A2A chat grants no execution authority; identity is not capability; journal before delivery; refusal always available.
