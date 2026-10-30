# P0B-C1 — independent-process interoperability and TCK readiness

**Status:** developer-only, **NOT DEPLOYED**. This cut qualifies a separately implemented localhost client and freezes an upstream TCK revision for a future independent compatibility run. **P0B is still incomplete; official TCK NOT RUN.**

## Why this is not certification

The P0B-B service is intentionally a single static acknowledgment over A2A 1.0 JSON-RPC. It has no task lifecycle, user identity, admission, cancellation, streaming, push notifications, or general response logic; it rejects many otherwise valid A2A requests. Running only our own in-repo tests cannot establish protocol conformance. The official upstream [A2A Technology Compatibility Kit](https://github.com/a2aproject/a2a-tck) has a separate implementation and MUST/SHOULD/MAY requirements. We have **not** executed it, and cannot call the P0B-B server broadly conformant.

## Evidence delivered by this cut

1. An independent client executable `python3 -m tools.a2a_interop_client --origin http://127.0.0.1:<port>` that **does not import the server**. It uses Python's stdlib HTTP and JSON implementation as a separate consumer, with no DNS lookup or remote-host option.
2. Cross-process CI test starts the P0B-B local probe explicitly at an ephemeral port; waits for its startup banner; then starts the independent client as a **second process**.
3. Client discovers `/.well-known/agent-card.json`, rejects dishonest interfaces, advertised skills and claims of unsupported advanced capabilities, sends a real v1.0 `SendMessage`, independently checks its JSON-RPC response, tests idempotent replay, and confirms unsupported `GetTask` is **refused**. It verifies the journal records a request hash, not raw text.
4. Negative tests refuse non-loopback URLs, embedded credentials, hostname aliases, unexpected binding, fake identity, unsupported tool/streaming claims, malformed, overlarge, duplicate-key or unexpected response payloads.
5. A separate **official TCK source pin**, not a checked-in or vendored dependency: [a2a-tck source record](../../contracts/agent-web/a2a-tck-pin-20261030.json).

**Important:** A separate process using a client written by the same project is a useful interoperability *smoke test*, **not** an independently maintained client SDK or an independent TCK pass. A green CI run means only these bounded tests passed.

## Official TCK pin (source verification performed 2026-10-30)

- Official upstream repository: `a2aproject/a2a-tck`.
- Reviewed source commit: `d4d6fae7887f88ef607fb461c13e3b0e1802f19b` (Oct 22, 2026).
- Immutable Git tree SHA-1: `8469eb8aa083c027aa00a3107972b1787dc6671a`.
- `run_tck.py` Git blob SHA-1: `06f70520f89c2bb60e1f752694781141568ad08b`.
- `uv.lock` Git blob SHA-1: `9c17390a1441fb70d798baa8f4e71bc24fe95cdb`.
- `pyproject.toml` Git blob SHA-1: `3bb6059dbd68d3ce9e2dd01776077adebc7c5577`.

These are **Git object identities**, not SHA-256 values or proof of a clean TCK run. The upstream TCK commit is pinned separately from our existing [A2A specification v1.0.1 pin](../../contracts/agent-web/a2a-upstream-v1.0.1.json). Test implementation and protocol spec do not automatically have identical release schedules.

The official TCK README describes:
```text
./run_tck.py --sut-host http://localhost:9999 --transport jsonrpc --level must
```

**Not authorized in this cut:** downloading and installing TCK dependencies, network-enabled test installations, starting public agents, CI credential exposure, or treating an expected test failure as a pass. Running TCK against the current narrow probe is likely to reveal missing operations; any such result must be recorded as **FAIL/HOLD**, never silently suppressed or represented as compliant.

A later Director-authorized TCK execution cut should use a disposable credential-free environment, fetch the exact pinned commit, verify the tree and lockfile, install reproducibly with review of code/dependencies and a controlled egress policy, start an **ephemeral loopback-only** server, run the required TCK levels, save unmodified raw compatibility JSON/HTML/logs, categorize every MUST failure, and STOP for Director review. No mandatory checks may be waived merely to get green CI.

## Operator test (no deployed services)

```bash
set -uo pipefail
python3 -m unittest discover -s tests -v
```

The cross-process test automatically starts and stops only a temporary local probe bound to 127.0.0.1 with an operator-owned mode-0700 journal directory. The client itself requires a known local-only origin; it will **not** resolve hostnames or contact remote addresses. Tests do not read developer credentials or modify repository-tracked files.

## Next Director gates

- **P0B-C2:** Independent upstream TCK run (raw results preserved), official SDK client probe, and source-pinned dependency chain; qualify all mandatory requirements or explicitly HOLD.
- **P0C:** Portal-owned agent registration, owner/controller verification, revocation, rate limiting, privacy/tenant boundaries in a separate repo/cut.
- **P0D:** Two real independently governed agents plus cited read-only lore receipt, governed journal and permission-filtered Observatory.
- **P0E:** Separate host, tunnel, DNS, production security, incident response and deployment authorization.

**No speech grants. Models cannot authorize work. One cut · one proof · one Director ruling.**
