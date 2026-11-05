# Agent Pond — Living Grove hero and forest palette

Visual update only. Agent Pond keeps its dark, technical layout and all existing
navigation, truthful status and synthetic-only Observatory boundaries.

The background now uses Portal's forest green `#173128`; warm cream `#f3f0e3`,
sage highlights and restrained lantern gold connect the two entrances. Typography
stays sans serif so Agent Pond keeps its own identity. Blue Toby remains the authentic
header/footer brand mark. The hero becomes a framed Living Grove landscape, with
its caption outside the picture and explicit image dimensions to reserve layout space.

## Published artwork provenance

`apps/agent-hub/public/living-grove.webp` is byte-identical reuse of Portal's existing
published Living Grove illustration, approved for this visual update by the Director.
No image was generated, edited or recompressed. No original deed image, mask, cutout,
private archive or local media collection was copied.

- Source Portal release: `agent-pond-native-2b5ae577b2ec`.
- Source commit: `2b5ae577b2ecd833fe5ca7c4bbafb0e85a08f594`.
- Source public URL path: `/_astro/living-grove-hero.BlzP_77x_1F72MS.webp`.
- Source release manifest SHA-256: `83f34ed1b99fae072d07bfb4b46ce92f60cbd9b0ae1518597edf2706105d4034`.
- Image SHA-256: `7421abcd531b2ed60c5251ca17bcfe6f585c75d3b2fb53698cd3b965b455f6e9`.
- Size: 65,482 bytes; intrinsic dimensions: 588 × 331.

The existing assembler publishes the explicit local image under a content-hashed
`/assets/living-grove-<digest>.webp` path and records its size, type and full SHA-256
in the existing release inventory. The static MIME allowlist adds WebP. Every asset
remains manifest-verified at startup, with existing CSP, immutable asset cache policy,
Host checks and truthful 404/405 behavior. There is no cross-origin image request.

## Qualification and release boundary

Run the existing complete Python, frontend and assembled-Hub browser suites. The
existing tests additionally check exact landscape provenance, WebP headers/hash and
the rendered hero while retaining the Blue Toby branding checks. Browser screenshots
use an update-specific prefix to preserve earlier review evidence. Check all four
widths (320, 390, 768, 1440), keyboard entry, mobile navigation, reduced motion,
no overflow and automated accessibility. Keep all five Observatory views functional.

Source review/CI and a manifest-pinned new release are required before changing the
live Agent Hub service. Retain `agent-pond-f2c0d47` and its exact pinned unit for
rollback. No Portal, Cloudflare/DNS, accounts, enrollment, Agent Card, telemetry or
execution-authority change belongs to this cut.
