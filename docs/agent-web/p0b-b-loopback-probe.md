# P0B-B — governed loopback A2A discovery and fixed-response probe

**Status:** P0B-B local prototype qualified by in-repository tests; **NOT DEPLOYED**, **NOT PUBLIC**, **NOT Agent0**. This does not satisfy the full P0B conformance/deployment gate.

## Exact upstream pin

A2A official repository tag **v1.0.1**, commit `3303592588e388e62e0f69f701af531d2f4e3991` (GitHub tag object resolves to this immutable commit as verified 2026-10-30). The normative Protocol Buffers definition at `specification/a2a.proto` has Git blob SHA-1 `400cdbad934654e27d7abbae1e145923eb40ac52`, and its release documentation at `docs/specification.md` has Git blob SHA-1 `382185a53b312cd6a60f5ac536ec5a356437ce77`. This is a **Git object identity**, not an invented SHA-256 digest or a substitute for full protocol certification. See [upstream pin data](../../contracts/agent-web/a2a-upstream-v1.0.1.json).

- Pinned release: `https://github.com/a2aproject/A2A/tree/3303592588e388e62e0f69f701af531d2f4e3991`
- Normative schema: `https://github.com/a2aproject/A2A/blob/3303592588e388e62e0f69f701af531d2f4e3991/specification/a2a.proto`
- Documentation: `https://github.com/a2aproject/A2A/blob/3303592588e388e62e0f69f701af531d2f4e3991/docs/specification.md`

The prototype uses A2A **wire version `1.0`** (`Major.Minor`, not the `1.0.1` patch version). The code is **a deliberately narrow structural/behavioral subset, not a generated protobuf binding**; there has been no independent official TCK run. Pinning upstream prevents version drift in our analysis only.

## What actually works locally

- The operator explicitly starts the server; it binds **only IPv4 `127.0.0.1`** with a 3-second socket timeout and no redirect, proxy, Cloudflare, background service, or auto-start.
- `GET /.well-known/agent-card.json` returns a dynamically constructed Agent Card with exactly one **real local** JSON-RPC interface and one fixed-ack skill. It uses an HTTP loopback URL; public/production HTTP requires HTTPS and a separate deployment review. A hostile Host header does not alter the card.
- `POST /a2a` with `Content-Type: application/json`, `A2A-Version: 1.0`, JSON-RPC 2.0 method `SendMessage`, one bounded `ROLE_USER` text part, and a new `messageId` returns `{result: {message: {... role: ROLE_AGENT, contextId, messageId, parts...}}}`. The content is a hard-coded acknowledgment; there is **no model, agent, Lore Reader, MCP tool, user registration, or external API** behind it.
- Before the HTTP response, the local journal appends and fsyncs a hash-linked entry, containing an input hash and exact output, not the input text. Replay of an identical message ID/body returns the saved result; a conflicting replay is refused. On restart, journal integrity is checked and already-issued responses are recoverable. Single-writer lock and bounded journal protect against concurrent use and resource growth. Incomplete/corrupt logs, unsafe filesystem ownership/modes, and journal write errors fail closed.
- The journal is **not signed or tamper-proof** against its owning operator: a malicious writer who can recalculate the hash chain can rewrite it. It also does **not** reconstruct the original input transcript. That is a deliberate P0B-B limitation and prevents promotion into multi-turn governed A2A conversation without further work.

## Local development invocation — explicitly operator-initiated

From a local, checked-out repository, using a **temporary directory outside the repository**:

```bash
set -uo pipefail
journal_dir="$(mktemp -d)" || exit 1
chmod 700 "$journal_dir" || exit 1
python3 -m agent_web.local_probe --journal-dir "$journal_dir" --port 0
# Prints the local URL. Ctrl-C to stop. Remove private temporary journal separately,
# after inspection, under your own host authorization and retention rules.
```

Run tests without launching persistent services:

```bash
python3 -m unittest discover -s tests -v
```

Test scope: loopback socket bound, correct advertised URL, real JSON-RPC response shape, version and mode rejection, no write-oriented methods, bounds, duplicate JSON fields, replay, private permissions, fsync before delivery, failure refusal, restart and corruption handling. The tests use local ephemeral sockets only. Their passing result does not establish production safety or official full A2A conformance.

## Explicit exclusions and future gates

- No listening on `0.0.0.0`, IPv6 public interface, WAN, DNS, tunnel, reverse proxy, Portal, MCP, Agent0, cloud host, or production machine.
- No publication of production Agent Cards or issuance of registration/credentials.
- No task continuation, streaming, push notification, tools, wallet operations, approvals or execution authority. Arbitrary local users may reach the loopback endpoint: **do not run this as an elevated or privileged service.**
- A real agent must later use a principal-bound, privacy-aware full journal, owner admission, signed grants when applicable, revocation, and explicit human/operator authorization, as prescribed by the existing canonical A2A constitution.
- **P0B-C independent conformance gate (future):** run the official A2A TCK / compatible SDK at the pinned protocol release, resolve unsupported semantics or downgrade advertised capabilities honestly, test shutdown and restart under an operator-approved envelope, and obtain separate review before any public exposure. No automatic deployment follows from this cut.

**No speech grants. The model is not the authority. One cut · one proof · one Director ruling.**
