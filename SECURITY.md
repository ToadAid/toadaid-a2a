# Security Policy

**Cut:** CUT-A2A-COMMUNITY-P0-20261103 ("Open the Forge") — implemented
with this cut, shipping together with CONTRIBUTING.md.
**Private Vulnerability Reporting:** verified ENABLED on this repository
(2026-11-03) — see below.

## Reporting a security concern

**Do not open a public GitHub issue for security findings.** Stating the boundary
accurately:

- **No production A2A gateway, public endpoint, or hosted service is deployed.** This
  repository is architecture-first; nothing connects to real systems in production.
- **The repository is not inert.** It contains locally executed tools (CLI utilities,
  offline classifiers) and explicitly started loopback `127.0.0.1` test fixtures.
  Locally executed code like that can present genuine security findings — for example
  a fail-closed seam that fails open, a fixture binding or accepting more than it
  should, or a boundary documented weaker than implemented.
- A public issue conflates a code-level finding with a production incident and cannot
  be triaged as it deserves, so findings go through the private channel below.

## Designated channel: GitHub Private Vulnerability Reporting

The supported disclosure channel is GitHub's built-in **Private Vulnerability
Reporting** feature:

1. Go to the repository's **Security** tab.
2. Choose **Advisories → Report a vulnerability** (verified ENABLED on
   this repository, 2026-11-03).
3. Describe the finding, the affected file(s), and any reproduction steps. Private
   Vulnerability Reporting keeps the entire exchange out of public view.

## Enablement status (verified 2026-11-03)

Private Vulnerability Reporting is **ENABLED** on this repository — verified
by the repository owner against GitHub's settings API, which returned
`{"enabled": true}`. Anyone signed in to GitHub can privately report a
vulnerability through the Security tab even without write access.

No email address is published or invented in this repository (the
`ToadaidDAO@gmail.com` address appearing in commit metadata is not a
designated security contact). Do not disclose findings publicly.

## Scope guidance

- **Welcome:** findings about locally executed tools, loopback fixture behavior
  (binding, scope, lifetime, input handling), trust-boundary logic, fail-closed seams,
  refusal semantics, contract/schema validation, admission or authority handling, and
  documentation that overstates or understates a boundary.
- **No production exposure as claimed by this repository today:** no A2A gateway,
  public endpoint, or hosted service is deployed, and no production system is affected.
  A report describing a production-side exploit path against this repository does not
  apply as stated — but locally executable findings remain fully in scope, as listed
  above.
- Synthetic example records and fixtures are intentionally fictional and labeled as
  such; reports consisting solely of an example being fictional are unnecessary.