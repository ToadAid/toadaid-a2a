# Contributing to ToadAid A2A

Welcome. If you are new here, you are genuinely welcome — this document is written
so that someone who has never seen ToadAid can make a small, useful contribution
today without needing to understand the whole ecosystem first.

## What ToadAid A2A is, in one paragraph

ToadAid A2A is an architecture-first repository for sovereign agent-to-agent (A2A)
conversation, task, authority, and evidence handling: the goal is verifiable,
human-governed collaboration between independent agents, built denial-first so that no
component ever gains authority it was not explicitly granted. Everything today is a
small, local-only, deliberately synthetic prototype; no A2A gateway, public endpoint,
agent registry, lore publication or conformance claim is live. Read
[README.md](README.md) and the
[canonical architecture master note](docs/architecture/canonical-a2a-architecture-master-note-v0.md)
for the real status ledger — it is honest about what does not exist yet.

## Current status, plainly

- **Architecture-first**: most "cuts" are documents plus small local tools, not services.
- **Local-only**: anything runnable binds to `127.0.0.1` and must be started by hand.
- **Not deployed**: there is no production system, no public endpoint, and no
  authentication system yet.
- The official A2A TCK has **not** been run; no interoperability beyond a local
  independent-process smoke is claimed.

## Getting started

Clone and inspect:

```sh
git clone https://github.com/ToadAid/toadaid-a2a.git
cd toadaid-a2a
```

Run the full test suite (standard-library Python 3 only; no virtualenv, no dependency
install, no pip):

```sh
python3 -m unittest discover -s tests -v
```

That's the whole toolchain. Any Python 3 works: the suite is standard-library-only,
CI runs the same command on GitHub's `ubuntu-latest` runner without a version pin, and
the cut was locally verified on Python 3.12. There is intentionally no `requirements.txt`
and nothing to install.

## Proposing improvements

- **Open an issue first** for anything architectural: changes to contracts, schemas,
  trust boundaries, refusal semantics, or the A2A protocol pins.
- **Small fixes can go straight to PRs**: documentation corrections, typos, additional
  tests, and equally small developer-experience improvements. Fixing a doc typo should
  not require reading 1,300 lines of architecture note first.

## Pull-request expectations

- Branch from the **latest `main`**; keep one cut (one coherent change) per PR.
- All tests pass: `python3 -m unittest discover -s tests -v`.
- `git diff --check` is clean (no stray whitespace).
- No merge without review.

## What always needs Director review

- Trust boundaries, refusal/fail-closed logic, or anything touching admission or
  authentication authority.
- Architecture changes, protocol pins, or contract/schema changes
  (`contracts/**`, `docs/architecture/**`).
- New dependencies of any kind (the target is currently *zero*, stdlib only).
- Security-sensitive code: anything that could ever grant execution, publication,
  admission, wallet, payment or MCP authority.

## Coding conventions

- **Python 3 standard library only.** No pip installs, no third-party imports.
- **`unittest`** for tests; keep each new fact in a small, named test.
- **Deny-first refusal codes**: invalid input raises a descriptive code
  (`ObservatoryRefusal("SOMETHING_NOT_ADMITTED")`) rather than degrading silently.
- **Declare the cut**: every module starts with a docstring naming its cut ID and its
  boundaries (see `observatory/feed.py` for the pattern).
- **Canonical JSON**: emit comparable digests via `observatory.model.canonical_json`,
  never `json.dumps(...)` with ad-hoc flags.
- **Tenant/owner scoping**: records carry `tenantRef`/`ownerRef` and reads are
  scope-checked; never collapse scopes.
- **Fail closed**: absent configuration means refusal, never permissiveness — seams
  default to `None` and refuse everything until a trusted adapter is injected.
- **Authority flags are `False` by construction**: never introduce a code path that
  sets `executionAuthorized`, `publicationAuthorized` or `deploymentAuthorized` to `True`.

## Security boundaries contributors must respect

The following are settled decisions, not open invitations:

- **No production deployment** and no real authentication — do not wire one in.
- **No agent admission**, no agent registration, no public `Agent Card`.
- **No wallets, payments, or MCP tool-authority surfaces.**
- **No network calls in tests** — everything runs offline against localhost fixtures.
- Do not reuse loopback fixture URLs or synthetic examples as if they were real.

## Reporting security concerns privately

Do **not** open a public GitHub issue for security findings: this repository documents
trust boundaries before it deploys any, so a public issue about a boundary could cause
confusion about whether real systems are affected. Also note plainly: **nothing in this
repository is deployed**, so a reported "vulnerability" cannot affect real systems.

The designated disclosure channel is **[GitHub Private Vulnerability
Reporting (SECURITY.md)](SECURITY.md)**: the repository's Security tab →
**Advisories → Report a vulnerability**. (Verified ENABLED on this
repository on 2026-11-03.)

## License

This repository is licensed under the MIT License (see [LICENSE](LICENSE)).
The MIT license was approved by the ToadAid Director on 2026-11-03 for
ToadAid's original repository code and documentation; third-party
materials retain their own rights, and original Tobyworld lore is NOT
relicensed. See
[the license rights assessment](docs/agent-web/community-license-rights-assessment-v0.md)
for the evidence and scope record.