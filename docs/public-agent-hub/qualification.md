# Local qualification receipt — 2026-11-04

Base: `377cfb477ed948a0bfffdc7222a593ca639c1d08` (merged PR #24).
Feature branch: `feature/a2a-p0c-door-a1-public-agent-hub-20261104`.
Exact final head, CI runs and artifact hashes are supplied in the Draft PR/release packet.

| Command | Local result |
| --- | --- |
| `npm --prefix apps/observatory-dashboard ci` | Passed, existing locked runtime dependencies |
| `python3 -m unittest discover -s tests -v` | 438 passed; no skips (431 baseline + 7 static HTTP/refusal tests) |
| `npm --prefix apps/observatory-dashboard test` | Build passed; 53 tests passed (51 preserved + 2 navigation tests) |
| `npm --prefix apps/observatory-dashboard run test:hub` | 16 passed, four widths (320, 390, 768, 1440); all five views/refresh and both themes |
| `python3 -m unittest discover -s tests -p test_public_hub.py -v` | 7 passed after standalone formatting/integrity check |
| `systemd-analyze --user verify /tmp/toadaid-agent-pond-review.service` | Rendered review template syntax passed; service not installed or started |

The existing root-only production output tests and their assertions are preserved.
New tests independently qualify the assembled release; they do not infer subpath
correctness from a green root-only build. Actual compiled assets load, direct query
links survive refresh, browser history updates correctly, return links are static,
Markdown is Markdown, protocol/private/unknown paths return 404 and mutation methods
return 405. Python tests qualify headers on HTML, Markdown, JS, CSS, SVG, PNG, errors
and redirects, manifest/runtime/file tampering, HEAD and Host refusal.

The browser tests use fresh isolated Chromium contexts. Installed in-app browser
bootstrap reported no available browser, so repository Playwright supplied browser
qualification; no signed-in profile or existing session was inspected. Screenshots:
`/tmp/agent-door-home-{desktop,tablet,mobile-390,mobile-320}.png`, corresponding
`observatory` files and mobile menu files. The release packet preserves these review
artifacts. Home makes no external resource requests; no fonts or trackers are loaded.
The standalone final artifact verifier additionally checks every actual assembled
asset's bytes, MIME, headers, absence of Set-Cookie/CORS and private-key/token patterns.
Pattern scanning is bounded evidence, not a universal proof of no sensitive content.

## Failures and corrections, not skips

Initial sandboxed Python/browser attempts failed socket creation (`Operation not
permitted`); rerun with loopback permission passed. An initial standalone builder
replaced its import literal twice and produced invalid runtime source; restricting the
replacement to one occurrence plus a compile regression check fixed it. Browser testing
identified that the synthetic banner was Overview-only; the existing banner now sits
in the shared shell. Expanded axe checks found missing labels on activity filters,
low contrast in both theme palettes, opacity-dimmed chart percentages and simulated
admin-card copy. Labels/colors were corrected and whole-card/text opacity removed;
controls remain disabled and all authority flags remain false. All findings were
rechecked without weakening axe or existing regression assertions. An initial systemd
syntax check used the `.service.in` template suffix; rendering it to `.service` passed.

## Remaining release gates

No production URL, Cloudflare edge policy, TLS deployment, DNS change or managed
service activation is qualified by these local passes. Control-plane hostname/DNS/
Pages conflict inventory is unavailable and remains required. Exact Director release
approval, reviewed installation and external HTTPS/content/header/cookie/routing
checks are outstanding. Full owner telemetry, live Agent Card, enrollment and execution
remain separately unauthorized and absent.
