# A2A-UI-P1-R1 — Agent Observatory Public Preview Deployment and Rollback Guide

**Cut:** CUT-A2A-UI-P1-R1-20261104
**Status:** PROPOSED DEPLOYMENT SPECIFICATION · **NOT DEPLOYED**
**Repository:** `ToadAid/toadaid-a2a`
**Constitutional Invariant:** `A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY`

---

## 1. Overview & Standardized Root Route

This specification defines the static build, hosting architecture, verification gates, and rollback procedures for serving the read-only, synthetic ToadAid Agent Observatory preview at:

`https://agent.toadaid.org/`

### Routing Standardization (Root-Only Initial Preview)
Following Director review, the initial public preview is standardized strictly on the root route (`/`).
- **Single Entry Point:** `https://agent.toadaid.org/` serves `dist/index.html`.
- **No Unbuilt Subpath Promises:** Unqualified `/dashboard/` URLs are removed. Subpath routing is neither claimed nor advertised in this cut.
- **Client-Side Views:** Navigation across the five views (Overview, Directory, Activity, Communication, Security) is managed entirely client-side via state and search query parameters (e.g. `https://agent.toadaid.org/?view=activity`), ensuring zero dependency on server-side path rewrites.
- **Static 404 Routing:** The static fallback page `dist/404.html` is returned with HTTP status 404 by Cloudflare Pages for any unmatched static path. It provides a clear notice and an absolute return link to the root (`href="/"`), ensuring reliable navigation back to the root preview even when triggered from deeply nested nonexistent paths (e.g. `/missing/section/` or `/dashboard/`).
- **No Functions Routing:** The obsolete `_routes.json` file is removed. The preview is a 100% static asset deployment with zero Cloudflare Workers or Pages Functions dependencies.

---

## 2. Invariant Boundaries

- **Synthetic Local Foundation:** All telemetry records, agent cards, communication flows, and event logs are driven by offline synthetic fixtures (`contracts/examples/synthetic-observatory-feed.v0.json`).
- **Always-Truthful Display:** The visible interface displays **`SYNTHETIC PREVIEW — NO LIVE AGENTS`** before and after public deployment.
- **Zero Execution Authority:** All five authority flags are enforced `false` by construction (`executionAuthorized: false`, `publicationAuthorized: false`, `deploymentAuthorized: false`, `agentRegistrationActive: false`, `publicDirectoryExposed: false`).
- **Administrative Functions Disabled:** All future operational controls remain disabled and explicitly marked: `NOT IMPLEMENTED — DIRECTOR AUTHORIZATION REQUIRED`.
- **Zero Runtime Backend:** Standalone client-side Single Page Application with zero runtime databases, zero live agent transports, and zero server-side state.

---

## 3. Static Build & Verification Architecture

### Build Parameters
- **Source Root:** `apps/observatory-dashboard/`
- **Engine Requirements:** Node.js `>= 20.0.0` (Node.js 22 LTS recommended) / npm `>= 10.0.0`
- **Build Sequence:** `npm ci && npm run build && npm test`
- **Vite Base Configuration:** Configured with `base: "./"` for portable relative asset linking.
- **Output Directory:** `apps/observatory-dashboard/dist/`

### Verified Artifact Inventory
```
dist/
├── index.html                 # Minified entry point with relative asset references (./assets/...)
├── favicon.svg                # Tobyworld pond icon
├── icons.svg                  # SVG sprite sheet
├── 404.html                   # Static fallback route page with return link to root
├── _headers                   # Hardened Cloudflare Pages security & caching headers
└── assets/
    ├── blue-toby-[hash].png   # Bundled authentic Blue Toby mascot (SHA-256 verified)
    ├── index-[hash].css       # Compiled Tailwind v4 & Tobyworld design tokens
    └── index-[hash].js        # Compiled React application (zero external telemetry domains)
```

---

## 4. Hardened Security Headers (`_headers`)

Cloudflare Pages applies the committed static `_headers` file across all responses:
```http
/*
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()
  Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none';

/assets/*
  Cache-Control: public, max-age=31536000, immutable
```

### Verified Protections:
- `default-src 'self'`: Disallows third-party scripts, styles, or iframes.
- `connect-src 'self'`: Prevents client-side exfiltration or unsolicited outbound API requests.
- `frame-ancestors 'none'` & `X-Frame-Options: DENY`: Prevents unauthorized embedding or clickjacking.
- `X-Content-Type-Options: nosniff`: Prevents MIME-type sniffing attacks.

---

## 5. Domain & Cookie Security Boundaries

### Subdomain Storage vs. Cookie Scope Realities:
- **Client Storage Isolation:** Origin-bound storage (`localStorage`, `sessionStorage`, `IndexedDB`) is strictly isolated between origins. `agent.toadaid.org` cannot access `portal.toadaid.org` client storage.
- **Parent-Domain Cookie Transmission Risk:** Standard browser security models dictate that cookies issued with parent-domain scope (e.g., `Domain=.toadaid.org` or `Domain=toadaid.org`) are automatically sent by browsers to all subdomains on every HTTP request.
- **Enforced Security Policy:**
  1. **Host-Only Scope is Mandatory:** Portal authentication cookies must use **host-only** scope by omitting the `Domain` attribute entirely. This restricts them exclusively to `portal.toadaid.org`.
  2. **`HttpOnly` is Not an Alternative to Scope:** Setting `HttpOnly` mitigates client-side JavaScript access via `document.cookie` (XSS protection), but does NOT prevent the browser from transmitting parent-domain cookies over the network to sibling subdomains.
  3. **Client-Side Safeguard Limitation:** Merely not reading or referencing cookies in Agent Observatory client-side JavaScript cannot prevent the browser from transmitting parent-domain cookies if Portal misconfigures their scope.
  4. **Defense-in-Depth Configuration:** Portal authentication cookies must strictly combine host-only scope (omitting `Domain`) with `Secure; HttpOnly; SameSite=Lax` (or `SameSite=Strict`) as appropriate.
  5. **No Credential Leakage:** No authentication credentials, tokens, or private keys may be passed in URLs or query strings.

---

## 6. Cloudflare Pages Hosting Setup (For Human Operator)

To configure the project on Cloudflare Pages:
1. **Repository Connection:**
   - In Cloudflare Dashboard: **Compute (Workers & Pages)** > **Create application** > **Pages** > **Connect to Git**.
   - Select repository: `ToadAid/toadaid-a2a`.
2. **Build Settings:**
   - **Framework preset:** `Vite` (or `None`)
   - **Build command:** `cd apps/observatory-dashboard && npm ci && npm run build && npm test`
   - **Build output directory:** `apps/observatory-dashboard/dist`
   - **Root directory:** `/`
3. **Environment:**
   - `NODE_VERSION`: `22`
   - Zero secrets or API keys are required or permitted.
4. **Custom Domain:**
   - Bind custom domain `agent.toadaid.org`.

---

## 7. Operational Rollback Procedures

### Realistic Propagation Caveats
Rollbacks in distributed edge environments are **not instantaneous or risk-free**:
- **Edge Cache Propagation:** While Cloudflare deployment pointers update rapidly, edge cache TTLs and browser caches (`Cache-Control`) may continue serving cached responses.
- **DNS Caching:** Recursive DNS resolvers cache domain lookups until TTL expiration.
- **Human Approval:** All rollback actions require human operator authorization.

### Option A: Cloudflare Pages Deployment Rollback (Primary Procedure)
1. Navigate to **Cloudflare Dashboard** > **Workers & Pages** > `toadaid-agent-observatory` > **Deployments**.
2. Locate the previous known-good deployment record.
3. Click the three dots (`...`) > **Rollback to this deployment**.
4. Note the newly activated Deployment ID.

#### Mandatory Rollback Verification & Smoke Test:
1. Verify active deployment status in Cloudflare Pages dashboard.
2. Run cache-busting edge curl verification:
   ```bash
   curl -sI "https://agent.toadaid.org/?cb=12345678" | grep -E "HTTP/|cf-ray|x-content-type-options"
   ```
3. Inspect HTML payload to confirm asset hashes match the targeted release:
   ```bash
   curl -sL "https://agent.toadaid.org/?cb=12345678" | grep -o 'assets/index-[^"]*'
   ```
4. Verify HTTP 200 response and correct asset loading from an external browser.
5. Record rollback completion and verified Deployment ID.

### Option B: Guarded Git Pull-Request Rollback
Direct pushes to `main` are **strictly prohibited**. When rolling back source changes:
1. Create a dedicated rollback branch from current `main`:
   ```bash
   git checkout -b revert-observatory-preview origin/main
   ```
2. Create the revert commit using standard git syntax (do NOT use `-m` for single commits):
   ```bash
   git revert <commit-sha> --no-edit
   ```
3. Push the rollback branch to origin:
   ```bash
   git push origin revert-observatory-preview
   ```
4. Open a Pull Request targeting `main` titled: `revert: rollback observatory preview commit <sha>`.
5. Require full automated CI workflow qualification.
6. Await Director approval before squash-merging into `main`.

### Option C: Emergency Offline Kill-Switch
If a critical flaw requires taking the public preview offline immediately:
1. In Cloudflare Dashboard, go to **Manage Project** > **Settings** > **Manage Custom Domains**.
2. Remove or detach `agent.toadaid.org` (or pause the project in project settings).
3. **Limitation:** Clients with unexpired DNS records or browser connection pools may continue connecting until DNS TTLs expire.

---

## 8. Historical Hostname Reconciliation

### Architectural Context:
- **`docs/agent-web/foundation-v0.md` (P0A, October 2026):**
  Identifies `https://agent.toadaid.org` as reserved for:
  *"Future standards-compliant A2A discovery and bounded, authenticated agent conversation; not a human dashboard."*
- **`docs/agent-web/observatory-data-foundation-v0.md` (AO-P0A, November 2026):**
  Defines the read-only telemetry projection for the future Observatory.

### Reconciliation for Public Preview:
1. Serving the static preview at root `https://agent.toadaid.org/` is an authorized, temporary preview arrangement.
2. The preview displays **`SYNTHETIC PREVIEW — NO LIVE AGENTS`** to ensure human visitors never confuse synthetic telemetry with live agent execution.
3. When future machine A2A discovery is activated, standards-compliant machine discovery endpoints (`/.well-known/agent-card.json`) can be hosted alongside or repointed as authorized by the Director.

---
**HUMANS AUTHORIZE · AGENTS PROVE · AUTHORITY IS NEVER ASSUMED.**
