# Observatory theme applied before first paint

## Finding and scope

The PR26 reviewed head passed local and exact-head tests, but automatic frontend CI
on merged main e5c356cda2dc6f3dc7e73740bd83009589ed8523 failed its tablet dark Activity
contrast scan (run42035542370). It reported black text on #0c252b, ratio1.31, for five
navigation labels and the search input. That result is retained; no CI retry or
assertion/timeout change substitutes for it.

A single public targeted check after settled theme/panel readiness passed, so it
could not establish why the CI scan failed. A MutationObserver diagnostic then
captured the initial React control commit on the unchanged app: data-theme was
absent and both navigation and search computed rgb(0,0,0). The requested dark
attribute/colors appeared later. ThemeProvider used a passive useEffect, leaving
a committed unthemed DOM before theme application. This is a reproducible render-order
defect consistent with the CI symptom; the original runner trace was not uploaded,
so the exact interleaving inside that historical axe scan is not independently known.

The new tablet first-control regression fails on the old implementation with
theme:null and black control text, then passes with the fix. It is an intentional
pre-fix RED test, not a blind rerun of CI.

## Narrow fix

Apply the existing data-theme update in useLayoutEffect, before the committed UI
can paint. Retain localStorage persistence in useEffect. No color token, native
color scheme, theme precedence, palette, data adapter or layout changes. No inline
bootstrap script or CSP relaxation.

React documents the layout-effect phase before browser repaint:
https://react.dev/reference/react/useLayoutEffect .
Only the DOM attribute belongs in that phase; preference storage stays deferred.
This dashboard is a client-rendered Vite application, not an SSR/hydration interface.

## Qualification

- The existing both-theme/all-five-view axe loop and its zero serious/critical
  findings assertion remain. Existing timeouts and retry settings are unchanged.
- Its added first-control observer checks the initial committed theme on each
  navigation, rather than waiting away the unthemed state.
- A new conflicting-saved-light / requested-dark Activity regression runs at every
  existing viewport, including tablet768; it captures first navigation/input colors.
- Unit coverage checks URL preference before descendant passive work, interactive
  switching, saved preference and unavailable-storage/OS fallback.
- Full Python, frontend build/unit, and assembled browser suites remain required,
  followed by successful CI for the new exact head. Earlier green runs do not cover
  the repair. Screenshots use a separate prefix to preserve prior review evidence.

No live release, unit, Portal, Cloudflare/DNS, account/agent authority or Go Pond
change. The existing live release remains selected until separate Director approval
of the reviewed repair and its exact release artifact. Preserve the original red
post-merge result and the controlled red/green evidence in the delivery receipt.
