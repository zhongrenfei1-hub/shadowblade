# Refine ring · pass 002 log

Single source of truth for every edit applied in response to `docs/test-ring-report-002.md` and the pass-002 Showcase assets. Ordered as applied. Each bullet ends with a one-line rationale.

## Test-ring-002 fixes

### P0 — `scripts/charts.js` regression
- **`frontend/public/scripts/charts.js:108`** — swapped literal `'#22D3B7'` for `ACCENT`. Rationale: pass-001 declared the constant but never used it, leaving a brand-drift hazard.
- **`frontend/public/scripts/charts.js:137`** — same swap on line-chart `stroke`. Rationale: as above.
- **`frontend/public/scripts/charts.js:145`** — same swap on sparkline `dot` fill. Rationale: as above.

### P0 — search-input `aria-label`
- **`frontend/public/projects.html:85`** — added `aria-label="Filter projects"`. Rationale: WCAG 4.1.2 — screen readers need a programmatic name.
- **`frontend/public/templates.html:83`** — added `aria-label="Search templates"`. Rationale: as above.
- **`frontend/public/assets.html:69`** — added `aria-label="Search assets"`. Rationale: as above.
- **`frontend/public/team.html:79`** — added `aria-label="Find teammate"`. Rationale: as above.

### P0 — settings toggles + JS
- **`frontend/public/settings.html:146`** — added `role="switch" aria-checked="true" tabindex="0" aria-label="Auto-render on approval"`. Rationale: the toggle was visually a switch but had no SR or keyboard story.
- **`frontend/public/settings.html:150`** — same treatment with `aria-checked="false"` + `aria-label="Watermark drafts"`. Rationale: as above.
- **`frontend/public/settings.html:167`** — same treatment with `aria-checked="true"` + `aria-label="Require MFA"`. Rationale: as above.
- **`frontend/public/settings.html:240-242`** — rewrote toggle JS to flip `aria-checked` and respond to `Space` / `Enter`. Rationale: the visual `on` class was not mirrored in the AT tree, and there was no keyboard interaction at all.

### P1 — Showcase wiring (favicon + og + twitter)
- **`frontend/public/studio.html:6`** — added favicon + og:title/description/image (`screen-studio.svg`) + twitter:card/image. Rationale: page was completely unbranded for social sharing.
- **`frontend/public/projects.html:6`** — same block, og:image = `screen-dashboard.svg`. Rationale: as above.
- **`frontend/public/templates.html:6`** — same block. Rationale: as above.
- **`frontend/public/assets.html:6`** — same block. Rationale: as above.
- **`frontend/public/render-queue.html:6`** — same block, og:image = `screen-queue.svg`. Rationale: as above.
- **`frontend/public/analytics.html:6`** — same block. Rationale: as above.
- **`frontend/public/brand-kit.html:6`** — same block. Rationale: as above.
- **`frontend/public/team.html:6`** — same block. Rationale: as above.
- **`frontend/public/settings.html:6`** — same block. Rationale: as above.
- **`frontend/public/new-video.html:6`** — same block. Rationale: as above.
- **`frontend/public/job-detail.html:7`** — added og:title/description/image (`screen-queue.svg`) + twitter:card/image (favicon already present). Rationale: completes the social-share triple.
- **`frontend/public/pricing.html:8`** — added og:title, og:description, twitter:card, twitter:image (favicon + og:image already present). Rationale: pass-001 had only partial wiring.

### P1 — `brand-kit.html` heading hierarchy
- **`frontend/public/brand-kit.html:111-115`** — renamed CSS selectors `.sb-tone .col h4` → `.sb-tone .col h3` (and `.col--do/--avoid` variants). Rationale: necessary to keep visual styling after the markup demotion.
- **`frontend/public/brand-kit.html:239`** — promoted `<h4>Do</h4>` → `<h3>Do</h3>`. Rationale: H1 → H4 was a 3-level skip; `<h3>` makes the outline monotonic.
- **`frontend/public/brand-kit.html:248`** — promoted `<h4>Avoid</h4>` → `<h3>Avoid</h3>`. Rationale: as above.

### P1 — `new-video.html` H1 + aria-modal
- **`frontend/public/new-video.html:167`** — added `aria-modal="true"` on the wizard root. Rationale: completes the dialog ARIA contract.
- **`frontend/public/new-video.html:172`** — promoted `<div id="wiz-title" class="title">` → `<h1 id="wiz-title" class="title" style="margin:0">`. Rationale: page had no `<h1>` at all; Lighthouse/SR users had no document outline.

### P1 — `#38BDF8` → `var(--sb-status-running)` in style blocks
- **`frontend/public/studio.html:92`** — `.sb-transport__bar i` gradient stop. Rationale: hex value was already exposed as a token.
- **`frontend/public/analytics.html:25`** — `.sb-distribution__row .meter i` gradient stop. Rationale: as above.

### P1 — `.sb-stage__index--*` modifier classes
- **`frontend/public/styles/app.css:674`** — added five modifier classes (`--review/--running/--succeeded/--queued/--failed`). Rationale: lets pages reference status tokens via a class instead of duplicating inline RGBA + hex.
- **`frontend/public/dashboard.html:188`** — `style=...purple...` → `class="sb-stage__index sb-stage__index--review"`. Rationale: token-routed colour.
- **`frontend/public/dashboard.html:198`** — same, `--running`. Rationale: as above.
- **`frontend/public/dashboard.html:208`** — same, `--succeeded`. Rationale: as above.
- **`frontend/public/analytics.html:197`** — same, `--queued` (warn glyph). Rationale: as above.
- **`frontend/public/analytics.html:205`** — same, `--failed`. Rationale: as above.
- **`frontend/public/analytics.html:213`** — same, `--succeeded`. Rationale: as above.
- **`frontend/public/analytics.html:120`** — pill `style="color:#fbbf24..."` → `var(--sb-status-queued)`. Rationale: token integrity on the rejected-pill.
- **`frontend/public/new-video.html:241`** — same, `--running`. Rationale: as above.
- **`frontend/public/new-video.html:249`** — same, `--review`. Rationale: as above.
- **`frontend/public/new-video.html:257`** — same, `--succeeded`. Rationale: as above.
- **`frontend/public/job-detail.html:253`** — same, `--succeeded`. Rationale: as above.
- **`frontend/public/job-detail.html:260`** — same, `--running`. Rationale: as above.
- **`frontend/public/job-detail.html:267`** — same, `--review`. Rationale: as above.
- **`frontend/public/studio.html:440`** — replaced inline `color:#a78bfa` with `color:var(--sb-status-review)`. Rationale: the workspace-card avatar doesn't get the new modifier class but the token swap still applies.

### P1 — `team.html` role-pill tokens
- **`frontend/public/team.html:25-27`** — three role-pill colours moved to `var(--sb-status-running/-review/-queued)`. Rationale: same status tokens already exist; the literal hex was duplicated for no reason.

### P1 — Form-label association
- **`frontend/public/studio.html:238-266`** — added `id=`/`for=` to 6 brief fields (Goal, Audience, Ratio, Length, Tone, CTA). Rationale: WCAG 1.3.1 / 4.1.2 — sibling `<label>` doesn't bind without `for=`.
- **`frontend/public/studio.html:389-414`** — same pattern on 4 inspector fields (Scene script, Visual style, Pace, On-screen caption); B-roll wrapped in a `<div role="group" aria-labelledby="...">` since its content is a row of chips. Rationale: as above.
- **`frontend/public/studio.html:450`** — added `aria-label="Reply to review thread"` to the orphan reply textarea. Rationale: no `<label>` available; aria-label is the next-best SR name.
- **`frontend/public/new-video.html:187-221`** — added `id=`/`for=` to 5 wizard fields; Picked template wrapped in `<div role="group" aria-labelledby="...">`. Rationale: as above.
- **`frontend/public/settings.html:112-122, 137-142, 170-171`** — added `id=` to 6 `.sb-row__title` divs and `aria-labelledby=...` to the matching input/select. Rationale: `<label>` not present; `aria-labelledby` is the canonical recourse.

### P2 — Active marketing-nav state + brand link aria-label
- **`frontend/public/pricing.html:25`** — added `.sb-marketing__nav a.link.is-active { color: var(--sb-text); }` rule. Rationale: class-driven active state instead of inline.
- **`frontend/public/pricing.html:142`** — added `aria-label="ShadowBlade home"` to brand link. Rationale: matches landing-page pattern.
- **`frontend/public/pricing.html:152`** — `style="color:..."` → `class="link is-active" aria-current="page"`. Rationale: semantic active state.

### P2 — Pricing tablist semantics
- **`frontend/public/pricing.html:162-164`** — added `aria-label="Billing cycle"` on `[role=tablist]`, `role="tab"` + `aria-selected` on each button. Rationale: tablist needs an accessible name and `aria-selected` per WAI-ARIA APG.
- **`frontend/public/pricing.html:260-269`** — extended toggle JS to flip `aria-selected` alongside the `active` class. Rationale: keeps ARIA in sync with visual state.

### P2 — `.sb-priority--low` contrast
- **`frontend/public/render-queue.html:78`** — bumped `#64748b` → `#7d88a0` and tightened bg alpha. Rationale: prior pair scored ~3.0:1 on body, below WCAG 4.5:1 for body text.

## Showcase-asset wiring

- **`frontend/public/customer-story.html:182-184`** — replaced 30-line inline SVG placeholder in `.sb-cs-art` with `<img src="/showcase/case-study/helios-hero.svg" alt="..." />`. Rationale: hooks the Showcase ring's canonical asset.
- **`frontend/public/customer-story.html:200-203`** — added `<figure class="sb-cs-figure">` with `helios-metrics.svg` directly after the textual metrics row. Rationale: surfaces the metrics illustration without losing screen-reader access to the numbers.
- **`frontend/public/customer-story.html:207-213`** — wrapped the textual quote in `<figure class="sb-cs-pullquote">` paired with `helios-quote.svg`. Rationale: keeps the textual quote for SEO/SR while wiring the asset.
- **`frontend/public/customer-story.html:109-122`** — added supporting CSS for the two new figure wrappers. Rationale: visual rhythm with the asset.
- **`frontend/public/login.html:206-208`** — replaced 47-line inline SVG fallback with `<img src="/showcase/auth/login-art.svg" alt="" />`. Rationale: hooks the Showcase asset.
- **`frontend/public/login.html:119`** — extended `.art-fallback` CSS to cover `img` as well as `svg` with `object-fit: cover`. Rationale: required so the `<img>` fills the right rail the same way the inline SVG did.
- **`frontend/public/notifications.html:64-71`** — added `.sb-empty-state` CSS (centred figure + heading + body). Rationale: shared shape that can later move into `app.css` when a second route uses it.
- **`frontend/public/notifications.html:203-208`** — appended an Archived empty-state surface using `empty-inbox.svg` (initially hidden). Rationale: gives the asset a real home in the product.
- **`frontend/public/notifications.html:229-244`** — wired a small JS handler that swaps the list ↔ empty-state when the user clicks the Archived tab. Rationale: makes the asset reachable without inventing a new route.
- **`docs/showcase-empty-states.md`** — new note cataloguing every empty-* asset, what is wired, and how to slot in the rest. Rationale: per the brief, surface the others in a docs note so future empty-state work can pull them in.

## Skipped

- **Pass-001 P3 deferred items** (`app.css:23-24` aurora gradient tokens, `app.css:238/771` avatar gradient token, three cover-SVG dictionaries) — explicitly carried over by the report as low-impact; defer to a later ring to avoid drift in this commit.
- **`render-queue.html` `--sb-status-low` token** — applied the colour fix in-place but did not introduce a new `--sb-status-low` token; matches Test-ring-002's preferred alternative ("or — preferred — add token") only if low-priority pills become a system-wide need.
- **`templates.html` chip-style hoist (P3, item 16)** — pure refactor with no UX impact; skipped per brief rule ("Skip P2 unless trivial").
- **`brand-kit.html` swatch hex literals** — Test-ring-002 explicitly marked these "intentional and acceptable" (the page is the brand kit source of truth); no change needed.
- **`notifications.html` inline `color:#…` patterns** — page is out-of-scope per the report; carry over to pass 003.
