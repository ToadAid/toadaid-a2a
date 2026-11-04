# A2A-UI-P1 — Agent Observatory Public Preview Deployment and Rollback Guide

**Cut:** CUT-A2A-UI-P1-20261104
**Status:** PROPOSED DEPLOYMENT SPECIFICATION · **NOT DEPLOYED**
**Repository:** `ToadAid/toadaid-a2a`
**Constitutional Invariant:** `A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY`

---

## 1. Overview & Scope

This specification defines the static build, hosting architecture, verification gates, and rollback procedures for serving the read-only, synthetic ToadAid Agent Observatory dashboard at:

`https://agent.toadaid.org` (or subpath `https://agent.toadaid.org/dashboard/`)

### Invariant Boundaries
- **Synthetic Local Foundation:** All metrics, agent directory cards, communication pipelines, and activity logs operate entirely from bounded local synthetic fixtures (`contracts/examples/synthetic-observatory-feed.v0.json`).
- **Zero Live Execution:** The application confers no wallet execution, payment capabilities, MCP tool execution, or production administrative permissions.
- **Fail-Closed Security:** All five authority flags are enforced `false` by construction.
- **Isolated Static Frontend:** The dashboard is a standalone client-side Single Page Application (SPA). It requires zero backend servers, zero runtime databases, and makes zero outbound external network requests.

---

## 2. Static Build Architecture

The application is compiled using Vite with relative asset resolution (`base: "./"`), allowing it to be hosted at root or under any subpath without path modification.

### Build Configuration Parameters
- **Source Root:** `apps/observatory-dashboard/`
- **Engine Requirements:** Node.js `>= 20.0.0` (Node.js 22 LTS recommended) / npm `>= 10.0.0`
- **Dependency Install Command:** `npm ci`
- **Build Command:** `npm run build` (`tsc -b && vite build`)
- **Output Directory:** `apps/observatory-dashboard/dist/`

### Artifact Verification Inventory
A compliant production build produces:
```
dist/
├── index.html                 # Minified entry point with relative asset references
├── favicon.svg                # Tobyworld pond icon
├── icons.svg                  # SVG sprite sheet
├── 404.html                   # Static fallback route page
├── _headers                   # Cloudflare Pages security & caching headers
├── _routes.json               # Cloudflare Pages SPA routing rules
└── assets/
    ├── blue-toby-[hash].png   # Bundled original Blue Toby artwork
    ├── index-[hash].css       # Compiled Tailwind v4 & Tobyworld design tokens
    └── index-[hash].js        # Bundled React application
```

---

## 3. Cloudflare Pages Hosting Setup (For Human Operator)

To deploy the static preview to `agent.toadaid.org`:

### Step-by-Step Configuration:
1. **Repository Connection:**
   - In Cloudflare Dashboard, navigate to **Compute (Workers & Pages)** > **Create application** > **Pages** > **Connect to Git**.
   - Select repository: `ToadAid/toadaid-a2a`.
2. **Build Settings:**
   - **Framework preset:** `Vite` (or `None`)
   - **Build command:** `cd apps/observatory-dashboard && npm ci && npm run build`
   - **Build output directory:** `apps/observatory-dashboard/dist`
   - **Root directory:** `/` (or `apps/observatory-dashboard`)
3. **Environment Variables:**
   - `NODE_VERSION`: `22`
   - Zero secrets or API keys are required or permitted.
4. **Custom Domain:**
   - Under project settings > **Custom domains**, bind `agent.toadaid.org`.
   - Cloudflare automatically applies the committed `_headers` and `_routes.json`.

---

## 4. Hardened Security Headers (`_headers`)

The build bundles a hardened `_headers` file applied automatically by Cloudflare Pages:
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

### Security Guarantees:
1. `frame-ancestors none` & `X-Frame-Options: DENY` prevent clickjacking or embedding in unauthorized iframes.
2. `connect-src self` prevents client-side exfiltration or unsolicited outbound API requests.
3. `script-src self` prevents third-party script injection or unapproved tracking pixels.
4. `Cache-Control: immutable` ensures hashed assets are cached efficiently without cache poisoning.

---

## 5. Rollback Procedures

Because the deployment is 100% static with zero stateful databases or serverless functions, rollbacks are deterministic, instant, and risk-free.

### Option A: Instant 1-Click Cloudflare Pages Rollback (Recommended)
1. Navigate to **Cloudflare Dashboard** > **Workers & Pages** > `toadaid-agent-observatory` > **Deployments**.
2. Locate the previous known-good deployment.
3. Click the three dots (`...`) > **Rollback to this deployment**.
4. Propagation is instantaneous across the Cloudflare global edge network (< 30 seconds).

### Option B: Git Revert Rollback
1. Revert the offending commit on branch `main`:
   ```bash
   git revert <commit-sha> -m "revert: rollback observatory deployment"
   git push origin main
   ```
2. Cloudflare Pages detects the new commit on `main`, runs `npm run build`, and redeploys the prior stable state.

### Option C: Emergency Kill-Switch (Take Offline)
If an emergency requires taking `agent.toadaid.org` offline immediately:
1. In Cloudflare Dashboard, go to **Manage Project** > **Settings** > **Pause Project** (or delete custom domain binding).
2. The endpoint immediately returns HTTP 404 or falls back to an offline holding page.

---

## 6. Historical Hostname Precedence Analysis

### Documented Finding:
- In `docs/agent-web/foundation-v0.md` (P0A, October 2026):
  `https://agent.toadaid.org` is described as reserved for:
  *"Future standards-compliant A2A discovery and bounded, authenticated agent conversation; not a human dashboard."*
- In `docs/agent-web/observatory-data-foundation-v0.md` (AO-P0A, November 2026) and `contracts/agent-web/observatory-feed.v0.schema.json`:
  The feed contract describes `agent.toadaid.org/dashboard/` as the human dashboard preview projection.

### Architectural Reconciliation:
For this Public Preview phase:
1. `agent.toadaid.org` serves this client-side static dashboard as a read-only human preview.
2. When future machine A2A discovery is activated, machine discovery endpoints (`/.well-known/agent-card.json` and JSON-RPC message endpoints) will coexist under the same origin or subdomains as authorized by the Director.
3. The dashboard clearly identifies itself as `SYNTHETIC PREVIEW` to eliminate any possible confusion.

---
**HUMANS AUTHORIZE · AGENTS PROVE · AUTHORITY IS NEVER ASSUMED.**
