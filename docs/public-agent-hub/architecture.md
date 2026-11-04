# Agent Pond public entrance — A2A-P0C-DOOR-A1

Status: **release candidate; Director review required; no production activation**.

## Product and trust boundaries

`apps/agent-hub/public` owns a semantic HTML/CSS landing page and actual Markdown guide.
The assembler takes those explicit inputs and the existing React Observatory production
build. It publishes one immutable inventory: `/`, `/dashboard/`, `/pond/guide.md`, hashed
assets and a truthful 404. No files are copied from Portal. No agent registration,
Agent Card, localhost probe, private adapter, journal, notification or provider transport
is mounted. All five authority flags remain false. A visible card represents fictional
fixture data, never a connected real agent.

The existing Observatory keeps its five views and independently tested synthetic
adapter. Its relative Vite asset base also works when assembled at `/dashboard/`.
Validated `?view=` links survive refresh and browser history. The existing security
banner now appears on every view. The directory warning refers to unimplemented live
public discovery, not a claim that these synthetic cards are private telemetry.

HTML, CSS, JS, Markdown, PNG and SVG are served from the verified manifest only.
Missing assets, unknown dashboard subpaths, reserved discovery and protocol paths return
404. Mutation methods return 405; `/dashboard` redirects to `/dashboard/` preserving the
query. There is no HTML SPA fallback, directory listing, proxy, CORS or session issuer.
The runtime accepts only the public hostname and explicit local preview hosts. It binds
only IPv4 loopback, has a ten-second socket timeout and at most sixteen request threads.
It preloads verified public assets and never reads request-selected filesystem paths.

## Hosting decision and evidence

On 2026-11-04, the actual cloudflared management configuration at
`http://127.0.0.1:20241/config` was version 2 with only Portal → `127.0.0.1:4324` and
`http_status:404`. Portal is independently managed by `toadaid-portal.service`.
Port 4328 was unoccupied. Existing tunnel identity:
`471d83c2-2132-4bcc-8dae-e6ad6e0ad5ba`. No token was read or copied.

Recommended: **Option B**, a separate static-only user service at `127.0.0.1:4328`,
behind that existing tunnel. Reuse the approved host without a new paid VPS. Preserve
Portal ingress, service, releases and rollback. Stage immutable Hub releases and a
manifest-pinned service unit; no development server. The checked-in unit is a review
template, not an installed service. First-launch rollback removes only the newly
approved ingress/DNS and stops this new service; later upgrades restore the previous
pinned unit and retain both artifact directories.

Option A (Pages) offers managed static delivery and independent deployments, but no
Cloudflare control-plane session/API was available to inventory projects, DNS ownership
or bindings. Its routing/404/MIME/header behavior would need separate qualification;
this runtime-qualified artifact is not a Pages deployment. Option C offers no simpler
already-approved independent static host than the inspected tunnel. No Cloudflare
configuration was changed. Failed public DNS resolution is not evidence that a hostname
is available. **Read-only zone/project/hostname conflict inventory remains a release
prerequisite**, followed by approval of the exact ingress/DNS diff.

## Reproducible build and local qualification

```sh
npm --prefix apps/observatory-dashboard ci
npm --prefix apps/observatory-dashboard test
python3 -m unittest discover -s tests -v
(cd apps/observatory-dashboard && npx playwright install chromium)
npm --prefix apps/observatory-dashboard run test:hub
# Commit reviewed source first; production refuses a dirty-source manifest.
python3 -m agent_web.public_hub build --output /tmp/agent-pond-REVIEWED --release-id agent-pond-REVIEWED
sha256sum /tmp/agent-pond-REVIEWED/release-manifest.json
```

Use a real lowercase release identity, normally `agent-pond-<head12>`. The output must
not already exist. The manifest records source commit/dirty state, all public paths,
bytes, MIME types, SHA-256, runtime hash, authentic Blue Toby hash and synthetic flags.
The proposed unit clears its environment before startup. The standalone runtime contains no imports of application/private adapters. Its
manifest is an integrity receipt, not human release authorization. `--preview` is only
for disposable tests of uncommitted source; the proposed service never uses it.

The browser suite launches a fresh loopback server on 4389, four Chromium viewports,
reduced-motion mode and fresh contexts. It exercises actual compiled subpath assets,
Markdown, error/mutation responses, all views/refresh/navigation, keyboard entry,
responsive menus and axe. Existing unit assertions remain intact. CI installs Chromium
and runs the same tests without credentials or publishing. Host/CDN behavior still
requires independent post-approval external verification.

## Headers, privacy and future protocol reservation

All responses, including errors and redirects, carry CSP, nosniff, frame denial,
no-referrer, a restrictive Permissions Policy and same-origin resource policy. CSP
`connect-src 'none'` disallows live feeds. Existing React inline styles require
`style-src 'unsafe-inline'`; scripts remain self-only, no inline scripts. Hashed assets
are immutable; documents, Markdown and errors are no-store. No remote fonts, trackers,
service workers, credential APIs, private telemetry or runtime secrets are bundled.
Only the theme preference uses browser local storage. Cross-origin navigation uses
fixed URLs, no query/token forwarding, and `noopener noreferrer`.

Future Agent Card discovery and authenticated A2A endpoints remain unimplemented and
404. A future release must supply a genuine independently qualified communication
interface and exact allowlist routes. It cannot repurpose this static site as an
admission issuer, controller or execution authority. Public owner telemetry requires
its own authenticated application and release process.

## UX rationale

Installed `ui-ux-pro-max` guidance informed semantic hierarchy, Hero + Features + CTA,
Swiss-style spacing, native controls, visible focus, minimum touch targets and reduced
motion. The Director's forest-teal, jade, mint and lantern-gold palette takes precedence
over generic generated palette suggestions. System fonts avoid external requests.
Blue Toby is the existing authentic PNG, verified byte-for-byte and shared with the
Observatory bundle. CSS rings and small lantern accents provide atmosphere without
animation libraries or generated imitation branding. Portal keeps its light Living
Garden identity and existing A2A navigation placement.
