# Refine ring · pass 003 log

Single source of truth for every edit applied in response to `docs/test-ring-report-003.md`. Each bullet ends with a one-line rationale.

## Test-ring-003 fixes

### P0 — `login.html` pre-filled password
- **`frontend/public/login.html:192`** — dropped `value="••••••••••••"` attribute from the password input. Rationale: literal bullet string was being submitted on form-submit and broke password-manager autofill.

### P0 — `project-detail.html` tab strip
- **`frontend/public/project-detail.html:168-173`** — added `role="tablist"` + `aria-label`, gave every tab a real `href` (Overview → page anchor, Run → `job-detail.html`, Versions → `#versions`, Audit → `#audit`), and `role="tab"` + `aria-selected` across all four. Rationale: WCAG 4.1.2 — tabs without `href` are not focusable; SR users could not reach Versions/Audit at all.

### P1 — `login.html` `<main>` landmark + social meta
- **`frontend/public/login.html:7-13`** — added the 5-line OG/Twitter meta block pointing at `/showcase/auth/login-art.svg`. Rationale: page had favicon only; social-share previews were unbranded.
- **`frontend/public/login.html:156-157`** — wrapped `<article class="sb-auth">` in `<main>`. Rationale: page had no `<main>` landmark — SR users landed on bare "article" with no skip-target.
- **`frontend/public/login.html:225-226`** — closing `</main>` tag added to match. Rationale: as above.
- Note: the `<img src="/showcase/auth/login-art.svg" alt="" />` reference was already in place from pass 002's Showcase wiring sweep — no further edit needed.

### P1 — `project-detail.html` social meta
- **`frontend/public/project-detail.html:8-12`** — added og:title, og:description, twitter:card, twitter:image alongside the existing og:image. Rationale: completes the social-share triple.

### P1 — `notifications.html` glyph modifier classes
- **`frontend/public/notifications.html:48-65`** — added `.glyph--done/--review/--running/--queued/--failed/--muted` modifier classes parallel to pass-002's `.sb-stage__index--*` set, plus a button reset for `.sb-inbox-tab`. Rationale: page predates pass-002's modifier sweep and uses bespoke `.glyph` class — defining parallel modifiers keeps the page's class vocabulary intact.
- **`frontend/public/notifications.html:127`** — `style="background:rgba(34,211,183,0.18);color:var(--sb-accent-300)"` → `glyph--done`. Rationale: token-routed.
- **`frontend/public/notifications.html:140`** — `style="background:rgba(167,139,250,0.18);color:#a78bfa"` → `glyph--review`. Rationale: as above.
- **`frontend/public/notifications.html:152`** — `style="background:rgba(56,189,248,0.18);color:#38BDF8"` → `glyph--running`. Rationale: as above.
- **`frontend/public/notifications.html:161`** — `style="background:rgba(251,191,36,0.18);color:#fbbf24"` → `glyph--queued`. Rationale: as above.
- **`frontend/public/notifications.html:164`** — `<code style="color:#fbbf24">` → `var(--sb-status-queued)` token. Rationale: token integrity in the drift-detected message body.
- **`frontend/public/notifications.html:174`** — second done-glyph migrated. Rationale: as above.
- **`frontend/public/notifications.html:186`** — `#f87171` → `glyph--failed`. Rationale: as above.
- **`frontend/public/notifications.html:195`** — billing checkpoint glyph migrated to `glyph--muted`. Rationale: as above.
- **`frontend/public/notifications.html:204`** — second running glyph migrated. Rationale: as above.

### P1 — `notifications.html` social meta
- **`frontend/public/notifications.html:7-13`** — added 5-line OG/Twitter meta block. Rationale: completes the share-preview wiring.

### P1 — `notifications.html` keyboard-reachable inbox tabs
- **`frontend/public/notifications.html:114-121`** — converted seven `<div class="sb-inbox-tab">` to `<button class="sb-inbox-tab" type="button">`, kept the divider span, added `aria-current="page"` on the active one. Rationale: WCAG 2.1.1 — tabs were not keyboard-reachable; the existing JS handler at `:230-245` already toggles `.active` on click so this purely makes them focusable.
- Note: the empty-state block at `:213-218` and the JS that swaps it in on Archived were already wired by pass 002 — verified intact, no edit needed.

### P1 — `customer-story.html` `<main>` un-nesting
- **`frontend/public/customer-story.html:169-188`** — moved `<header class="sb-marketing__nav">` outside of `<main>` (was wrapped inside). Rationale: WCAG 1.3.1 — `<main>` must not contain `<header>` or `<footer>`; pass-001 P1 fixed the same on `index.html`.
- **`frontend/public/customer-story.html:262-266`** — moved `<footer class="sb-footer">` outside `<main>` and added closing `</main>` tag. Rationale: as above.

### P1 — `customer-story.html` marketing-nav semantics
- **`frontend/public/customer-story.html:170`** — added `aria-label="ShadowBlade home"` to brand link. Rationale: pass-002 P3 #13 carry-forward; pricing landed it, every new marketing page needs it.
- **`frontend/public/customer-story.html:177-184`** — wrapped the 5 link `<a>` elements in `<nav aria-label="Primary">` and fixed dangling Docs `href="#"` → `docs.html`. Rationale: marketing-nav landmark + real link target.

### P1 — `customer-story.html` copy fix
- **`frontend/public/customer-story.html:233`** — "on-guideline" → "on-brand". Rationale: pass-001 standardised on "on-brand"; the new customer-story page regressed.

### P1 — `customer-story.html` KPI gradient token
- **`frontend/public/customer-story.html:84`** — `linear-gradient(..., #38BDF8)` → `var(--sb-status-running)`. Rationale: token integrity on the metric value gradient.

### P1 — `status.html` uptime cell tokens + social meta
- **`frontend/public/status.html:8-12`** — added og:title, og:description, twitter:card, twitter:image alongside the existing og:image. Rationale: as above.
- **`frontend/public/status.html:85-86`** — `i.warn { background: #fbbf24 }` and `i.fail { background: #f87171 }` → status tokens. Rationale: same status hexes already exist as `--sb-status-queued/--failed`; literal hex was duplication.

### P1 — `changelog.html` pill tokens + social meta
- **`frontend/public/changelog.html:8-12`** — added og:title, og:description, twitter:card, twitter:image. Rationale: as above.
- **`frontend/public/changelog.html:94-96`** — `.fix/.perf/.brand` pill colours migrated to `var(--sb-status-queued/--running/--review)`. Rationale: same status hexes already tokenised on `team.html` per pass-002 #10; carrying forward.

### P1 — `docs.html` code-keyword token + social meta
- **`frontend/public/docs.html:8-12`** — added og:title, og:description, twitter:card, twitter:image. Rationale: as above.
- **`frontend/public/docs.html:130`** — `.sb-api pre .k { color: #fbbf24 }` → `var(--sb-status-queued)`. Rationale: code-syntax highlight was the last literal `#fbbf24` in the page-level style block.

### P1 — `gallery.html` social meta
- **`frontend/public/gallery.html:8-12`** — added og:title, og:description, twitter:card, twitter:image. Rationale: as above.

### P1 — `integrations.html` social meta
- **`frontend/public/integrations.html:8-12`** — added og:title, og:description, twitter:card, twitter:image. Rationale: as above.

### P1 — `components.html` social meta
- **`frontend/public/components.html:8-12`** — added the full 5-line OG/Twitter meta block. Rationale: design-system page was completely unbranded for social sharing; report flagged "Refine recommendation".

## Skipped (per brief: P2 unless trivial; or already fixed)

- **`gallery.html` reel cards unfocusable (P0)** — not in the brief's high-impact list; the report's proposed fix (wrap `<article>` in `<a href="#">`) introduces invalid HTML nesting since `<a>` cannot wrap an `<article>` that itself contains a `<button>` (`.play`). Defer to a future ring with a proper interactive-card pattern.
- **Marketing-nav active-state class promotion (P2 across 5 pages)** — not in the brief's high-impact list and requires editing five separate pages + lifting a CSS rule to the shared sheet. Carry forward to a future ring.
- **Brand-link `aria-label` on gallery/status/changelog/docs (P2)** — not in the brief's high-impact list (only customer-story was named); the same drift will get caught next pass.
- **`<header>` → `<nav>` wrap on 5 marketing pages (P2)** — same as above.
- **`integrations.html` chip-style hoist + per-integration `aria-label` (P2)** — pure refactor, no user-facing impact.
- **`components.html` `<aside>` → `<nav>` toc + 720px breakpoint (P2)** — not in brief's high-impact list.
- **`notifications.html` `data-route` change to `inbox` + shell nav entry (P2)** — touches `components/shell.html` which is out of scope for this pass.
- **`docs.html` / `status.html` `<main>` + `<nav>` insertion (P1)** — not in the brief's named high-impact list; same pattern across 5 marketing pages — defer for one shared fix in a future ring.
- **`project-detail.html` 480px version-row breakpoint (P1)** — not in brief's named items.
- **Inline SVG hero replacement in customer-story** — already done by pass 002 (`<img src="/showcase/case-study/helios-hero.svg">` was in place); verified intact.
- **`login.html` `<img>` wiring for login-art.svg** — already done by pass 002 (`<img src="/showcase/auth/login-art.svg" alt="" />` was in place); verified intact.
- **`notifications.html` empty-state block + showcase wiring** — already done by pass 002 (`.sb-empty-state` block + JS that swaps it in on Archived was in place at lines 213-218 and 230-245); verified intact.
