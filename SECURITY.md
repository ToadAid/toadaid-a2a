# Security Policy

**Cut:** CUT-A2A-COMMUNITY-P0-20261103 ("Open the Forge") — implemented
with this cut, shipping together with CONTRIBUTING.md.
**Private Vulnerability Reporting:** verified ENABLED on this repository
(2026-11-03) — see below.

## Reporting a security concern

**Do not open a public GitHub issue for security findings.** This repository is an
architecture-first, local-only status ledger: nothing in it is deployed, executed as a
service, or connected to real systems, so a public issue cannot be triaged as a real
incident and may mislead readers into thinking a production boundary is exposed.

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

- **Welcome:** findings about trust-boundary logic, fail-closed seams, refusal
  semantics, contract/schema validation, admission or authority handling, and
  documentation that understates a boundary.
- **Not needed:** reports that assume this repository is a deployed service (it is
  not), or that rest on synthetic fixtures being treated as real systems. Loopback
  URLs and synthetic examples are intentionally fictional and labeled as such.