# A2A-UI-P1-R1 — Portal Linking and Navigation Instructions

**Cut:** CUT-A2A-UI-P1-R1-20261104
**Target Surface:** `https://portal.toadaid.org` -> `https://agent.toadaid.org/`
**Status:** PROPOSED INTEGRATION SPECIFICATION · **NOT DEPLOYED**
**Constitutional Invariant:** `A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY`

---

## 1. Objective

Provide clear, secure, and standardized instructions for linking from the ToadAid Portal (`https://portal.toadaid.org`) to the Agent Observatory preview (`https://agent.toadaid.org/`).

Because the Observatory operates as an offline, synthetic preview with zero execution authority, the link must clearly establish context so community members and developers understand they are navigating to an observational telemetry preview rather than an active wallet or execution environment.

---

## 2. Standardized Destination URL

Following Director review, the preview route is standardized strictly on the root URL:
```
https://agent.toadaid.org/
```
*(All subpath references such as `/dashboard/` are deprecated and removed).*

### Recommended UI Placements in Portal:
1. **Top Navigation Bar:**
   - Label: `Observatory` (with a subtle `Synthetic Preview` badge).
   - Placement: In the community / developer tools section alongside Deed Atlas.
2. **Deed Atlas Explorer Sidebar / Footer:**
   - Link text: `"Explore Agent Telemetry & Invariants"`
   - Subtitle: `"Sovereign A2A Seam Governance Dashboard"`
3. **Portal Developer / Docs Hub:**
   - Link text: `"ToadAid Agent Observatory (Public Preview)"`

---

## 3. Strict Security & Boundary Attributes

When linking from `portal.toadaid.org` to `agent.toadaid.org/`:

### Required HTML Anchor Syntax:
```html
<a
  href="https://agent.toadaid.org/"
  target="_blank"
  rel="noopener noreferrer"
  class="toadaid-observatory-link"
  aria-label="ToadAid Agent Observatory (opens in new tab)"
>
  <img src="/assets/blue-toby-icon.svg" alt="" width="20" height="20" aria-hidden="true" />
  <span>Agent Observatory</span>
  <span class="preview-badge">Synthetic Preview</span>
</a>
```

### Security Requirements:
1. **`rel="noopener noreferrer"`:** Mandatory. Prevents the target page from obtaining access to the `window.opener` object of the Portal session.
2. **Zero Credential Sharing:** The Portal must NEVER append session tokens, cookies, auth headers, private keys, or wallet addresses to the URL query parameters or hash.
3. **Mandatory Host-Only Cookie Scoping:** Portal authentication cookies MUST use **host-only** scope (omit the `Domain` attribute entirely) to prevent them from being transmitted to sibling subdomains such as `agent.toadaid.org`. Setting `HttpOnly` mitigates client-side script access via `document.cookie`, but it does NOT prevent the browser network layer from attaching parent-domain cookies to requests across subdomains. Merely not reading cookies in Observatory client-side JavaScript cannot prevent the browser from sending parent-domain cookies if Portal erroneously issues wildcard-domain cookies. Therefore, Portal authentication must strictly combine host-only scope (omitting `Domain`) with `Secure; HttpOnly; SameSite=Lax` (or `SameSite=Strict`) as appropriate.
4. **Cross-Origin Storage Isolation:** The Observatory runs in complete origin-bound storage isolation (`localStorage`, `sessionStorage`).

---

## 4. Visual Design Guidelines for Portal Integration

To maintain Tobyworld design harmony across both applications:

- **Accent Colors:** Use the shared Tobyworld palette:
  - Deep Forest-Teal: `#0C252B`
  - Technical Jade: `#14B8A6`
  - Soft Mint: `#B4E0C7`
  - Lantern Gold: `#F59E0B`
- **Mascot Presence:** The link or card should feature the authentic **Blue Toby** mascot, matching the Observatory header.
- **Microcopy / Tooltip:**
  > *"ToadAid Agent Observatory: Explore synthetic telemetry, evidence classification, and A2A participation gates under zero execution authority."*

---

## 5. Summary of Truthfulness Rules

When rendering the Observatory link anywhere on Portal:
- **Do not** describe the Observatory as an active agent control panel or live trading desk.
- **Do not** imply that registered agents in the preview represent live connected autonomous machines.
- **Do** emphasize transparency, truthful evidence classification, and constitutional invariants.

---
**HUMANS AUTHORIZE · AGENTS PROVE · AUTHORITY IS NEVER ASSUMED.**
