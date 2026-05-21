# Refine ring · pass 004 log

Single source of truth for every edit applied in response to `docs/test-ring-report-004.md`. Each bullet ends with a one-line rationale.

Pass 004 also wired four new Showcase-ring-003 asset families (flags, leaders, compare banner, help banner) into the audited pages.

## Test-ring-004 fixes

### P0 — `workspace-switcher.html` dialog contract
- **`frontend/public/workspace-switcher.html:134`** — added `aria-modal="true"` to the `<article role="dialog">`. Rationale: WAI-ARIA APG Dialog pattern is mandatory for modal dialogs; the brief originally specified this and pass-003 missed it.
- **`frontend/public/workspace-switcher.html:144`** — added `aria-label="Filter workspaces"` to the search input. Rationale: the `<label>` wrapper contains only an `<svg>`, so the accessible name was reduced to placeholder text.
- **`frontend/public/workspace-switcher.html:201-228`** — appended a `<script>` block that wires roving-`tabindex` on the 6 listbox rows, ArrowUp/ArrowDown to move focus, Enter (when in search) to invoke the focused row, Escape to close, and click→`history.back()` on the close button. Rationale: keyboard users could not navigate or select a workspace despite the `<kbd>↑↓</kbd><kbd>↵</kbd>` glyphs advertising it; WAI-ARIA APG mandates Escape closes modals.

### P1 — `audit-log.html` verb-pill tokens
- **`frontend/public/audit-log.html:85-88`** — migrated four `verb--update/--delete/--auth/--render` rules from literal `#38BDF8/#f87171/#a78bfa/#fbbf24` to `var(--sb-status-running/--failed/--review/--queued)`. Rationale: same status hexes already tokenised on `changelog.html:94-96` last pass — pattern-repeat fix.

### P1 — `audit-log.html` 720px responsive collapse
- **`frontend/public/audit-log.html:94-103`** — appended a `@media (max-width: 720px)` block that collapses `.sb-audit-row` to single-column, left-aligns `.meta`, tightens `.sb-audit-filter` padding, and lets the search input span 100%. Rationale: page had zero `@media` rules and the 470px fixed-chrome grid (`130 140 1fr 200`) overflowed at 360px.

### P1 — OG/Twitter meta block on 5 pages
- **`frontend/public/audit-log.html:8-12`** — added 5-tag OG/Twitter block, image `/showcase/screens/screen-dashboard.svg`. Rationale: page shipped favicon-only social-share preview.
- **`frontend/public/help.html:8-12`** — added 5-tag block, image `/showcase/brand/og-image.svg`. Rationale: as above.
- **`frontend/public/compare.html:8-12`** — added 5-tag block, image `/showcase/compare/diff-art.svg`. Rationale: as above, also reuses the new pass-003 Showcase asset.
- **`frontend/public/localisation.html:8-12`** — added 5-tag block, image `/showcase/screens/screen-dashboard.svg`. Rationale: as above.
- **`frontend/public/about.html:8-12`** — page had `og:image` only; added the missing `og:title`, `og:description`, `twitter:card`, `twitter:image`. Rationale: completes the share-preview wiring.

### P1 — `help.html` heading + `<main>` + search a11y
- **`frontend/public/help.html:192`** — inserted `<h2 class="visually-hidden">Browse by topic</h2>` above the 8-cat grid. Rationale: H1→H3 skip violated WCAG 1.3.1; `app.css:1070` already defines `.visually-hidden`.
- **`frontend/public/help.html:179`** — added `aria-label="Search help articles"` to the search input. Rationale: the wrapping `<label>` contained only an `<svg>`, dropping accessible name to placeholder.
- **`frontend/public/help.html:191`/`298`** — wrapped the 4 `<section>` siblings in `<main>`. Rationale: page had no `<main>` landmark; SR users landed on bare `<header>`/`<section>` with no skip-target.

### P1 — `about.html` `<main>` landmark
- **`frontend/public/about.html:180`/`256`** — wrapped the 5 `<section>` siblings in `<main>`. Rationale: as above.

### P2 — `workspace-switcher.html` `opacity:0.7` → token-routed disabled state
- **`frontend/public/workspace-switcher.html:111-113`** — added `.sb-ws__row--inactive` rule set that dims name to `--sb-text-muted` and avatar to `saturate(0.5)`, keeping body text above AA contrast.
- **`frontend/public/workspace-switcher.html:188`** — UM Umbra-trial row migrated from `style="opacity:0.7"` to `class="sb-ws__row sb-ws__row--inactive"`. Rationale: blanket 0.7 alpha dropped `--sb-text` to ~3.8:1 on the dialog bg (sub-AA 4.5:1).

### P2 — `compare.html` change-set pill modifiers
- **`frontend/public/compare.html:239-241`** — migrated three `<span class="sb-pill" style="…">` to `.sb-pill--done/--running/--failed`. Rationale: 8-property inline-style duplicated existing modifier classes (`app.css:561-568`); third repeat after templates / integrations.

### P2 — `compare.html` "Adopt v17" affordance
- **`frontend/public/compare.html:133`** — added `aria-describedby="adopt-help"` to the primary button + adjacent `<span class="visually-hidden">` describing reversibility. Rationale: high-impact action that overwrites Current needs the perceivable affordance for "this replaces v16".

### P2 — `about.html` marketing-nav active-state class promotion
- **`frontend/public/about.html:27-28`** — added `.sb-marketing__nav a.link.is-active { color: var(--sb-text); }` and `.sb-marketing__nav nav { display: contents; }` to keep the flex layout after wrapping the link group. Rationale: pricing.html already established the `.is-active` token-route; replaces the inline-style anti-pattern.
- **`frontend/public/about.html:166`** — `<a class="link" href="about.html" style="color:var(--sb-text)">` → `<a class="link is-active" href="about.html" aria-current="page">`. Rationale: 6th drift site since pass-003; class-based active state + `aria-current` for SR.

### P2 — Brand link `aria-label` on 2 marketing pages
- **`frontend/public/about.html:158`** — added `aria-label="ShadowBlade home"` to the brand link. Rationale: pass-003 drift carry; SR users heard "link image" only.
- **`frontend/public/help.html:163`** — same fix. Rationale: as above.

### P2 — Marketing-nav `<nav>` wrap on 2 pages
- **`frontend/public/about.html:167-173`** — wrapped the 5 product/pricing/customers/about/docs links in `<nav aria-label="Primary">`. Rationale: pass-003 drift carry; `<header>` is not a navigation landmark.
- **`frontend/public/help.html:169-173`** — wrapped the 3 docs/changelog/status links in `<nav aria-label="Primary">`. Same rationale.
- **`frontend/public/help.html:21-22`** — mirrored the `.is-active` + `nav { display: contents }` rules in help.html style block for future-proofing. Rationale: keeps marketing-nav style vocabulary consistent across the 6 sites that ship it.

### P2 — Breadcrumb `<div>` → `<nav>` on 3 shell pages
- **`frontend/public/audit-log.html:97-103`** — `<div class="sb-breadcrumb">` → `<nav class="sb-breadcrumb" aria-label="Breadcrumb">`. Rationale: breadcrumbs are a navigation landmark by definition.
- **`frontend/public/compare.html:118-126`** — same fix.
- **`frontend/public/localisation.html:96-104`** — same fix.

### P2 — `about.html` press-kit link copy
- **`frontend/public/about.html:218-219`** — replaced "ZIP, ~28 MB" / "Download press kit" copy with "indexed inside `/showcase`" / "Browse the press-kit index". Rationale: link pointed at `/showcase/INDEX.md` (Markdown), not a ZIP — text now matches reality.

### P3 — `localisation.html` flag glyph SR cleanup
- **`frontend/public/localisation.html:172, 186, 200, 214, 228`** — added `aria-hidden="true"` to all 5 `.sb-lang__flag` divs. Rationale: SR was reading the 2-letter glyph (e.g. "EE-ESS") right before the language name; the name already conveys the data.

## Pass-003 showcase wiring (Refine ring brief steps 2–5)

### Step 2 — `localisation.html` flag pills
- **`frontend/public/localisation.html:52-62`** — added `overflow: hidden` to `.sb-lang__flag` and an `img { width:100%; height:100%; display:block }` rule so the new SVG fills the existing 36×26 pill.
- **`frontend/public/localisation.html:172, 186, 200, 214, 228`** — replaced text-content (`ES/DE/JA/FR/PT`) with `<img src="/showcase/flags/{locale}.svg" alt="" />`, where locale matches the row's `xx-xx` code (es-419, de-de, ja-jp, fr-fr, pt-br). Rationale: ships the pass-003 flag pill assets; SR-safe via `aria-hidden` on the wrapper (lang name follows).

### Step 3 — `about.html` leader portraits
- **`frontend/public/about.html:97-99`** — added `overflow: hidden` to `.sb-leader .av` and an `img { width:100%; height:100%; display:block; border-radius:50% }` rule.
- **`frontend/public/about.html:201, 207, 213, 219`** — replaced 2-letter initials with `<img src="/showcase/leaders/{as|lm|jr|dm}.svg" alt="" />`. Rationale: each portrait SVG already embeds the same monogram glyph, so visual identity is preserved; SVGs include their own `aria-label`.

### Step 4 — `compare.html` diff-art banner
- **`frontend/public/compare.html:114-121`** — added `.sb-cmp-banner` figure styling (radius-lg + border + dark-bg shell).
- **`frontend/public/compare.html:175-177`** — inserted `<figure class="sb-cmp-banner" aria-hidden="true"><img src="/showcase/compare/diff-art.svg" alt="" /></figure>` above the `.sb-cmp` pane grid. Rationale: decorative header per brief; sets the BEFORE / AFTER visual register for the side-by-side compare.

### Step 5 — `help.html` hero banner
- **`frontend/public/help.html:44-52`** — added `.sb-help-hero__banner` figure styling (radius-lg shell, max-width 720, full-width img).
- **`frontend/public/help.html:196-198`** — inserted `<figure class="sb-help-hero__banner" aria-hidden="true"><img src="/showcase/help/help-hero.svg" alt="" /></figure>` above the search input. Rationale: brand-anchored hero asset wired per brief; decorative `aria-hidden` since the headline + search input already carry intent.

## Skipped (per brief: P2 unless trivial; or already fixed)

- **P3 datetime attribute on every `<time>` on audit-log + compare** (item 22) — pure SR/parser polish; 12 sites, mechanical but voluminous. Defer to a future ring.
- **P3 audit-log + workspace-switcher data-table semantics** (item 23) — workspace-switcher already has `role="listbox"`; audit-log conversion to `<table>` is a larger refactor of the diff-row pattern. Defer.
- **P3 `--sb-grad-avatar-navy` token hoist** (item 24) — pass-001 P3 deferred since the same gradient now appears in 4 sites; about.html no longer uses it (replaced by leader portraits) so the deferral is less acute. Defer.
- **P3 audit-log header row style hoist** (item 20) — pure refactor, no user-facing impact.
- **P3 about.html `<b style="color:var(--sb-text)">` hoist to `.sb-about-em`** (item 21) — pure refactor.
- **P3 localisation "Add a language" tile decision** (item 19) — the inline `<article>` is visually inviting but the topbar `+ Add language` button already handles the action; the duplicate-lure question is a design call rather than an a11y blocker. Defer.
