# ShadowBlade · Test ring report 004
**Auditor**: Test ring (deterministic, source-only — no browser available)
**Scope**: `frontend/public/{audit-log,help,compare,localisation,about,workspace-switcher}.html` (6 net-new pages since pass 003)
**Standards**: WCAG 2.1 AA · keyboard-navigable · responsive ≥ 360px
**Coverage delta vs pass 003**: +6 pages. Pass 003's Refine queue (P0 tab focus, glyph modifiers, login meta, customer-story un-nest, status/changelog/docs tokens) verified intact upstream — see Regression section.

---

## Summary

| # | Page | Result | Top issue |
|---|---|---|---|
| 1 | `audit-log.html` | **Warn** | 4 hex literals in `verb--*` rules (`:85-88`) duplicate `--sb-status-*` tokens (regression-shaped — exact pattern fixed on `changelog.html:94-96` last pass); breadcrumb is `<div>` not `<nav>`; data table is `<div>` grid not `<table>` (SR cannot navigate columns); narrow-viewport overflow at < 600px (4-col `130px 140px 1fr 200px`). Full OG/Twitter meta block missing |
| 2 | `help.html` | **Warn** | 8 `.sb-help-cat` cards use `<h3>` directly under page `<h1>` — H1→H3 skip (`:194` etc.) is the same docs.html pattern flagged P1 in pass 003; brand link missing `aria-label="ShadowBlade home"`; no `<main>` landmark; no nested `<nav>` inside `<header class="sb-marketing__nav">`; full OG/Twitter meta missing; suggest pill links `<a href="#">` are stubs ×6; search `<input>` has no `aria-label` (label wraps but contains only `<svg>`) |
| 3 | `compare.html` | **Warn** | Three change-set pills (`:239-241`) duplicate the 8-prop inline style pattern when `.sb-pill--done/--running/--failed` modifiers exist (`app.css:561-568`); breadcrumb is `<div>` not `<nav>`; "Adopt v17" primary CTA has no `aria-describedby` pointing at the footer reversibility note (`:273`) — UX clarity for an action that overwrites Current; full OG/Twitter meta missing |
| 4 | `localisation.html` | **Warn** | "Add a language" card (`:240-244`) is `<article>` with no `<button>`/`<a>`/tabindex but visually invites click — same anti-pattern as gallery.html reel cards (pass 003 P0, deferred); flag glyphs (`ES/DE/JA/FR/PT`) read by SR as "EE-ESS Spanish (LATAM)" — need `aria-hidden="true"`; breadcrumb is `<div>` not `<nav>`; full OG/Twitter meta missing |
| 5 | `about.html` | **Warn** | Partial OG meta (only `og:image` at `:8`) — missing og:title, og:description, twitter:card, twitter:image; brand link missing `aria-label="ShadowBlade home"` (pass 003 drift carry); 5 marketing-nav `<a>` not wrapped in `<nav>` (pass 003 drift carry); no `<main>` landmark; 3 inline `<b style="color:var(--sb-text)">` (`:181-183`) — pass-003 P3 carry from customer-story; Press-kit link `/showcase/INDEX.md` claims ZIP but points at an MD index |
| 6 | `workspace-switcher.html` | **Fail (P0)** | Dialog missing `aria-modal="true"` (brief mandated this); **no script, no Esc/Enter handler** despite `<kbd>↑↓</kbd><kbd>↵</kbd>` glyphs advertising keyboard control — keyboard users cannot select a workspace; 6 `<div class="sb-ws__row">` have `role="option"` but are not focusable (no `tabindex`) and listbox has no `aria-activedescendant`; Search `<input>` has no `aria-label`; `:185` `style="opacity:0.7"` dims body text below 4.5:1 AA on the Umbra trial row; close button is footer-only with no Esc affordance |

**Tally**: 0 Pass · 5 Warn · 1 Fail (workspace-switcher)

---

## 1 · `audit-log.html` — **Warn**

| Category | Notes |
|---|---|
| 1. Token integrity | **P1**: `:85` `verb--update { color: #38BDF8 }` → `var(--sb-status-running)`. `:86` `verb--delete { color: #f87171 }` → `var(--sb-status-failed)`. `:87` `verb--auth { color: #a78bfa }` → `var(--sb-status-review)`. `:88` `verb--render { color: #fbbf24 }` → `var(--sb-status-queued)`. Same pattern Refine ring fixed on `changelog.html:94-96` last pass — repeat fix here. `:49` avatar gradient `#1c3868→#0a1428` is a bespoke initial avatar; the same gradient is used in `about.html:89` and `workspace-switcher.html:151` — could be hoisted to `--sb-grad-avatar-navy` but pass-001 P3 deferred. `:163, :169, :199` per-row inline avatar gradients `#3d2c5f/#3f2d1a/etc.` plus `color:#a78bfa/#fbbf24` — bespoke per-actor tinting, acceptable. |
| 2. Color contrast | Verb pills on `rgba(255,255,255,0.025)` row bg over body bg: `#fbbf24` ≈ 10:1 (AAA), `#38BDF8` ≈ 6:1, `#a78bfa` ≈ 5.5:1, `#f87171` ≈ 5:1, `var(--sb-accent-300)` ≈ 9:1. Body `.action var(--sb-text-muted)` ≈ 5.2:1. `time` and `.meta` `var(--sb-text-faint)` ≈ 4.6:1 (AA post pass-001 tightening). `b color:var(--sb-text-muted)` (`:175`) for "system" rows is a *muted* actor — at 5.2:1 still passes AA. |
| 3. Keyboard a11y | All topbar buttons `<button>` ✓. Filter `<select>` × 4 with `aria-label` ✓. Search `<input>` with `aria-label="Search events"` (`:148`) ✓. Rows are pure data — no clickable affordance, no `cursor:pointer` lie. ✓ |
| 4. Semantic HTML | H1 once (`:126`). `<main>` ✓. Footer ✓. **P2**: `<div class="sb-breadcrumb">` (`:97`) — should be `<nav aria-label="Breadcrumb">`. Same gap exists on every shell page (`compare.html`, `localisation.html`); fix should be repo-wide. **P2**: the 10-row event log (`:152-214`) is **tabular data** rendered as `<div>` grid — SR users cannot perceive column relationships, cannot use table-navigation shortcuts. Either convert to `<table>` with `<thead>` for the column header row, or add `role="table"` / `role="row"` / `role="cell"` to retrofit semantics on the divs. **P3**: header row (`:152`) styled inline with 9 `style="..."` props — hoist to `.sb-audit-row--head` modifier. |
| 5. Responsive | **P1**: zero `@media` rules. `.sb-audit-row` is `grid-template-columns: 130px 140px 1fr 200px` (= 470px fixed-width chrome before content) — at 360px viewport, horizontal overflow is guaranteed. Add `@media (max-width: 720px) { .sb-audit-row { grid-template-columns: 1fr; gap: var(--sb-space-2); } .sb-audit-row .meta { text-align: left; } }`. |
| 6. Copy review | "Every event in the workspace." → strong. KPI deltas concise. Filter labels (Actor/Resource/Verb/Window) → terse. Event copy ("Spot-instance reclaim spiked queue depth to 14"-style) is shipped-grade. Footer line "Hash chain · last block 14:13:24 · integrity OK · 2,148 events today" is on-brand. |
| 7. Performance hygiene | Preconnect ✓. No images. Single inline `<style>` block (~90 lines, ~3 KB). Rows are static HTML — no JS render cost. |
| 8. Showcase wiring | Favicon ✓ (`:7`). **Missing**: og:title, og:description, og:image, twitter:card, twitter:image. Audit log shipped *no* social meta beyond favicon. Asset choice: `/showcase/screens/screen-dashboard.svg` (audit log is a Settings sub-route — share the dashboard preview). |
| 9. Brand consistency | Accent `var(--sb-accent-300)` on code/value highlights ✓. Topbar LIVE pill is `.sb-pill--running` ✓. |
| 10. Cross-page consistency | `data-route="settings"` ✓ — sidebar Settings highlights. Loads shell fragment ✓. Topbar matches dashboard/projects/etc. |

---

## 2 · `help.html` — **Warn**

| Category | Notes |
|---|---|
| 1. Token integrity | Brand-mark gradient stops inside `<defs>` ✓ (`:162`). No hex outside the brand mark in style block. All status accents come from `var(--sb-accent-300)`. ✓ |
| 2. Color contrast | Hero `h1` ≈ 17:1. Lede `var(--sb-text-muted)` ≈ 5.2:1. `.sb-help-cat` body `var(--sb-text-muted)` ≈ 5.2:1. `details.sb-q summary` `var(--sb-text)` ≈ 17:1. The `details summary::after` `+` chevron `var(--sb-accent-300)` ≈ 9:1. `<small>` press meta `var(--sb-text-faint)` ≈ 4.6:1. |
| 3. Keyboard a11y | `<details>` is native — keyboard ✓ via Enter/Space. All nav and CTA buttons are `<a>` — focusable. Suggest pills `<a href="#">` × 6 (`:182-187`) — focusable but stub-destination. Cards `<article class="sb-help-cat">` have **no `<a>` wrapper** (`:192-231`) — cards are not focusable and not announced as links; `cursor:pointer` is not set, so the affordance is not lied about, but the cards look clickable. Wrap each card body in `<a href="docs.html#${cat}">` or add explicit "→" link inside each card. |
| 4. Semantic HTML | **P1**: H1 (`:175`) → H3 (`:194, :199, :204, :209, :214, :219, :224, :229`) — **skips H2**. Same pattern flagged P1 on `docs.html` pass 003 §10. Fix: insert `<h2>Browse by topic</h2>` above `.sb-help-grid` or wrap the grid in a `<section><h2 class="visually-hidden">Browse the docs</h2>…</section>`. **P2**: `<header class="sb-marketing__nav">` (`:160`) — not a `<nav>`; should nest a `<nav aria-label="Primary">` around the 3 `<a class="link">` items. **P2**: brand link `<a class="sb-brand" href="index.html">` (`:161`) — missing `aria-label="ShadowBlade home"` (pass 003 drift carry). **P1**: no `<main>` landmark — `<body>` → `<header>` + 4 `<section>` + `<footer>`. Wrap the 4 sections in `<main>`. **P1**: search `<input>` (`:179`) — the `<label class="search">` wraps it but contains only an `<svg>` (no text node) so the accessible name reduces to placeholder; add `aria-label="Search help articles"`. |
| 5. Responsive | Only `@media (max-width: 1100px)` (`:156`). At 1100 → 2-col help-grid + 1-col contact. Below 720 the 2-col grid (190px+ cards × 2) gets cramped on 360px viewport; the 8 cards are large. Add 720 breakpoint that drops `.sb-help-grid` to 1 col. Marketing nav (5 items) will wrap at 480 — no responsive collapse. FAQ `<details>` uses `max-width: 760px` — fine. Contact `max-width: var(--sb-container)` + 3 col → 1 col at 1100 ✓ but pad-x is `var(--sb-space-12)` (48px ×2) on a 360px viewport = 96px chrome. |
| 6. Copy review | "How can we help?" — standard, the tagline below ("Quick answers, deep guides, a status page, and a humans-on-the-other-end mailbox. Pick a path.") is on-brand. FAQ answers are concrete ("Median first cut lands in 4 minutes 48 seconds") and shipped-grade. Contact cards: "24×7 SEV-1 · Enterprise only. Page our oncall directly. 15-minute acknowledgement target." reads like a real SLA. |
| 7. Performance hygiene | Preconnect ✓. No images. Single inline `<style>` ~140 lines (~4 KB). Native `<details>` — no JS. |
| 8. Showcase wiring | Favicon ✓. **Missing all 5 OG/Twitter tags**. Asset choice: `/showcase/brand/og-image.svg` (generic). |
| 9. Brand consistency | `.sb-help-cat .icon` `rgba(34,211,183,0.12)` + `var(--sb-accent-300)` ✓. `details.sb-q summary::after` accent chevron ✓. Footer link `<a href="status.html" style="color:var(--sb-accent-300)">` (`:278`) ✓. |
| 10. Cross-page consistency | Marketing-nav signature matches docs / changelog / status (3-link product subnav rather than the 5-link landing nav). The `<span>Help center</span>` subtitle under the brand mark mirrors the `status.html` "Status" subtitle ✓. |

---

## 3 · `compare.html` — **Warn**

| Category | Notes |
|---|---|
| 1. Token integrity | `:50` `linear-gradient(160deg, #112646, #050a18)` — preview-pane CSS bg outside SVG. Bespoke navy gradient, acceptable as decorative. SVG illustrations (`:168-188`, `:202-227`) hex outside `<defs>` (`#22D3B7`, `#F7F9FC`, `#8590A8`) — acceptable per rubric (inline illustration). `:75-77` diff-row left-border colors all use `var(--sb-accent-500)/--sb-status-running/--sb-status-failed` — ✓ tokenised. `:107` `.delta.down { color: var(--sb-status-queued); }` ✓. **P2**: change-set pills (`:239-241`) use inline `style="color:var(--…);background:rgba(…)"` — should adopt `.sb-pill--done` / `.sb-pill--running` / `.sb-pill--failed` modifiers that already exist in `app.css:561-568`. |
| 2. Color contrast | Diff-row `.old` `var(--sb-text-muted)` strikethrough ≈ 5.2:1 (AA). `.new` `var(--sb-text)` ≈ 17:1 (AAA). Stat `.v var(--sb-text)` ≈ 17:1. Stat `.delta var(--sb-accent-300)` on stat card ≈ 9:1. Pane `time` muted ≈ 4.6:1 (AA). |
| 3. Keyboard a11y | All topbar buttons `<button>` ✓ — focus-visible from global. Diff rows are read-only `<div>` — no clickable affordance. **No tab-trap, no listbox**. ✓ |
| 4. Semantic HTML | H1 once (`:145`). `<main>` ✓. `<article>` for each pane ✓. `<article class="sb-card">` for the change set ✓. **P2**: `<div class="sb-breadcrumb">` (`:118`) — should be `<nav aria-label="Breadcrumb">`. **P3**: pane `<time>` (`:165, :198`) has no `datetime` attribute — `<time>4 min ago</time>` should be `<time datetime="2026-05-21T14:09">4 min ago</time>` for SR/parser clarity. **P2**: "Adopt v17" primary `<button>` (`:133`) — high-impact action that overwrites the live cut. No `aria-describedby` pointing at the footer reversibility note. Either: (a) add `aria-describedby="adopt-help"` + `<small id="adopt-help">Adopt to publish · or restore v16 if v17 drifts</small>`, or (b) wire a confirm dialog. The button is NOT destructive (forward action) so primary styling is correct — but the affordance for "this replaces Current" needs to be perceivable. |
| 5. Responsive | One breakpoint at 1100px (`:109`) → `.sb-cmp` 1-col + stats 2-col. Below 720 the stat cards (4 → 2 → ?) still hold; previews shrink to `min(280px, 100%)` — at 360px the 280px preview is tight but renders. Add a 720px breakpoint that pushes stats to 1-col. Diff-rows `display: grid` with no fixed cols — natural flow ✓. |
| 6. Copy review | "4 changes · 0 visual regressions · 1 brand-tone uplift · 0.4 s shorter render time." — perfect. "Music duck lifted to -6 dB" / "Rush render · Priya's CTA copy" — concrete, shipped-grade. Diff `key` uppercase scene-script labels ("SCENE 04 · SCRIPT · WORD 18–22") read like a real producer's diff. "Added outro: 'Pre-order — first 1,000 ship free.'" → marketing-grade. Footer "Adopt to publish · or restore v16 if v17 drifts" gives the reversibility signal. |
| 7. Performance hygiene | Preconnect ✓. Two inline preview `<svg>` (each ~1 KB). Single inline `<style>` (~100 lines, ~3 KB). `shell.js` bottom-loaded ✓. |
| 8. Showcase wiring | Favicon ✓. **Missing all 5 OG/Twitter tags**. Asset choice: `/showcase/screens/screen-dashboard.svg` (compare is a project-detail sub-route — share the project preview). |
| 9. Brand consistency | Pane `.head .v` `var(--sb-accent-300)` ✓. `Current` pill on v17 is `.sb-pill--running` ✓. Stat `.delta` accent ✓. All diff-row left-borders are token-routed ✓. |
| 10. Cross-page consistency | `data-route="projects"` ✓. Breadcrumb 4 levels (Acme > Projects > Spring launch > Compare) — same pattern as `localisation.html`. Loads shell fragment ✓. |

---

## 4 · `localisation.html` — **Warn**

| Category | Notes |
|---|---|
| 1. Token integrity | `:31` `.sb-loc-source .swatch` bg gradient `#15376a→#050a18` — bespoke navy gradient, same as `compare.html:50` (P3 dedup opportunity). SVG cover (`:131-156`) hex outside `<defs>` (`#22D3B7`, `#F7F9FC`, `#8590A8`) — acceptable per rubric. `:83-85` `.sb-lang--queued/--running/--done` colour-routes via tokens ✓. `:240` "Add a language" card — `border-style:dashed;background:rgba(34,211,183,0.04)` plus accent-coloured `<svg style="color:var(--sb-accent-300)">` — all token-routed ✓ (but see semantic note below). |
| 2. Color contrast | `.sb-lang__flag` `var(--sb-text)` on `var(--sb-graphite-700)` (#1d2535) ≈ 14:1 (AAA). `.sb-lang__name b` ≈ 17:1. `.sb-lang__name span` `var(--sb-text-faint)` ≈ 4.6:1 (AA). `.sb-lang__caption` `var(--sb-text-muted)` italic on `rgba(255,255,255,0.025)` row ≈ 5.0:1 (AA). `.row span var(--sb-text-muted)` ≈ 5.2:1. State pills via `.sb-pill--done/--queued/--running` — tokenised, all ≥ 5:1 on the card bg. |
| 3. Keyboard a11y | All topbar buttons `<button>` ✓. **P1**: `.sb-lang` cards (`:170, :184, :198, :212, :226`) are not interactive — no `<a>` / `<button>` — but **the "Add a language" tile** (`:240-244`) is `<article>` with `+` icon and "Add a language" text, no `<button>` / `<a>` / `tabindex`. The visual screams "click me" — same anti-pattern as `gallery.html` reel cards (pass 003 P0). Two paths: (a) wrap content in `<a href="#add">`, (b) remove the tile and rely on the topbar `+ Add language` button (`:106`) alone. Note: the topbar button already exists, so the tile is a duplicate lure — option (b) is cleaner. |
| 4. Semantic HTML | H1 once (`:119`). `<main>` ✓. `<aside class="sb-loc-source">` is the source pane ✓. `<article class="sb-lang">` × 5 + "Add" tile ✓. **P2**: breadcrumb `<div>` not `<nav>`. **P3**: `<dl>` source spec at `:157-163` — `<dt>` / `<dd>` pairs ✓. `.sb-lang__flag` (`:172, :186, :200, :214, :228`) is decorative — SR reads "EE-ESS Spanish (LATAM)" (the flag glyph followed by the name). Add `aria-hidden="true"` on `.sb-lang__flag`, OR add `role="img" aria-label="Spanish"` to make the glyph a proper image. Preferred: `aria-hidden="true"` since the language name immediately follows. **P3**: the "Add a language" tile inline styles a 6-property block at `:240` — hoist `.sb-lang--add` modifier. |
| 5. Responsive | One `@media (max-width: 1100px)` (`:87`) collapses both grids to 1-col. Below 720 the source pane is full-width above the lang grid (already collapsed); the 280px source swatch keeps its `max-height: 320px` ✓. No 480 stress — but the source `<dl>` is `grid-template-columns: 90px 1fr` which won't fail at 360. |
| 6. Copy review | "One cut. Five languages. Same voice." — excellent. "Source script changes auto-flag every variant for re-render." reads like a real product invariant. Per-row data ("−22 wpm", "+1.4 s", "estimated 22 cps" for JA reading-speed) is shipped-grade. Footer "Voice clones never leave your tenant" → on-brand trust line. |
| 7. Performance hygiene | Preconnect ✓. Single inline source `<svg>` (~1.5 KB). Single inline `<style>` (~80 lines, ~2.5 KB). |
| 8. Showcase wiring | Favicon ✓. **Missing all 5 OG/Twitter tags**. Asset choice: `/showcase/screens/screen-dashboard.svg`. |
| 9. Brand consistency | Source-pane `.v var(--sb-accent-300)` (`:32`) ✓. `Add a language` accent icon ✓. All status pills tokenised ✓. |
| 10. Cross-page consistency | `data-route="projects"` ✓. Breadcrumb 4 levels matches `compare.html`. Loads shell fragment ✓. The source pane / variant-grid pattern is unique to this page — no other page replicates it. |

---

## 5 · `about.html` — **Warn**

| Category | Notes |
|---|---|
| 1. Token integrity | Brand mark inside `<defs>` ✓ (`:157`). `:64` `.sb-about-body em` gradient `var(--sb-accent-500), var(--sb-status-running)` ✓ tokenised (mirrors customer-story.html pass-003 fix). `:89` `.sb-leader .av` gradient `#1c3868→#0a1428` — bespoke navy avatar gradient (same as `audit-log.html:49`, `workspace-switcher.html:151`) — P3 hoist to `--sb-grad-avatar-navy` token (pass-001 P3 still deferred). `:147` `.sb-quote .pub var(--sb-accent-300)` ✓. |
| 2. Color contrast | Hero H1 `var(--sb-text)` on body bg ≈ 17:1 (AAA). Lede `var(--sb-text-muted)` ≈ 5.2:1. `em` gradient ≈ 5:1 (AA effective). `.sb-about-body` muted body ≈ 5.2:1. `.sb-leader b var(--sb-text)` on card bg ≈ 14:1. `.sb-leader span var(--sb-text-muted)` ≈ 5.0:1. `.sb-leader span small-muted` `var(--sb-text-faint)` ≈ 4.6:1 (AA). `.sb-leader .av var(--sb-accent-300)` on `#1c3868→#0a1428` ≈ 7.5-12:1 (AAA) — initials are crisp. `.sb-quote .q var(--sb-text)` ≈ 17:1. Press card `<a> var(--sb-accent-300)` ≈ 9:1 (AAA). |
| 3. Keyboard a11y | All nav + CTA links `<a>` ✓. Press-kit / inquiries `<a>` ✓. No interactive cards beyond. ✓ |
| 4. Semantic HTML | H1 once (`:172`). H2 ×2 (`:180, :185`). H3 ×2 (`:217, :222`). ✓ monotonic. **P1**: no `<main>` landmark — `<body>` → `<header>` + 5 `<section>` + `<footer>`. Wrap the 5 sections in `<main>`. **P2**: `<header class="sb-marketing__nav">` (`:155`) — not a `<nav>`; should nest `<nav aria-label="Primary">` around the 5 link items (pass 003 drift carry). **P2**: brand link (`:156`) missing `aria-label="ShadowBlade home"` (pass 003 drift carry). **P2**: `<a class="link" href="about.html" style="color:var(--sb-text)">` (`:164`) — inline active-state anti-pattern; replace with `class="link is-active" aria-current="page"`. **P3**: 3 inline `<b style="color:var(--sb-text)">` (`:181-183`) — hoist `.sb-about-em` class (same pattern flagged in pass 003 §1 customer-story). |
| 5. Responsive | One `@media (max-width: 1100px)` (`:151`) → leaders 2-col, quotes 1-col, press 1-col. Below 720 the 2-col leaders (76px avatars × 4 with `padding: var(--sb-space-5)` = 20px) fit but the `.sb-about-body p` `max-width: 760px` + `padding: 0 var(--sb-space-6)` keeps body readable on mobile. Hero `clamp(36px, 4.4vw, 58px)` H1 — at 360px clamps to 36px ✓. Marketing nav (5 links + 2 buttons) will wrap below 720 — no collapse rule. |
| 6. Copy review | "We're rebuilding the video factory for the team that ships every week." — excellent on-brand hero. Founder-story para is concrete ("watched their marketing team spend more time briefing a video than shooting one"). Three "We believe" bullets are sharp and quotable. Leader cards: roles ("Co-founder & CEO", "Head of Research") + bio (one-line, ex-company) — clean. Press quotes feel real ("In a year, this is the only AI video tool that ever showed up to the procurement review with a SOC 2 in hand"). |
| 7. Performance hygiene | Preconnect ✓. No images (no leader photos — initials only). Single inline `<style>` ~140 lines (~4 KB). |
| 8. Showcase wiring | Favicon ✓. `og:image` ✓ (only page in this audit that has any OG meta). **Missing**: og:title, og:description, twitter:card, twitter:image. The 4-tag completion is mechanical. **P2**: Press-kit link (`:219`) — `<a href="/showcase/INDEX.md">Download press kit (auto-generated from /showcase) →</a>` claims "ZIP, ~28 MB" in the description but the link points at a Markdown file. Either fix the description to "Markdown index", or generate a real ZIP at `/showcase/press-kit.zip`. |
| 9. Brand consistency | Brand mark `#22D3B7 → #38BDF8` gradient ✓ (`:157`). Hero `<em>` accent gradient ✓. Leader cards + Quote cards use the same `rgba(11,18,32,0.6)` and `linear-gradient(180deg, rgba(22,30,48,0.85), rgba(11,18,32,0.85))` shape vocabulary as customer-story / changelog. |
| 10. Cross-page consistency | Marketing nav signature is the 5-link landing pattern (`Product · Pricing · Customers · About · Docs`) — matches `customer-story.html`, `gallery.html`, `index.html`, `pricing.html`. The `<a class="link" href="about.html" style="color:var(--sb-text)">` active-state is the inline anti-pattern flagged 5x in pass 003. Brand mark subtitle "Video Cloud" matches landing/customer-story. |

---

## 6 · `workspace-switcher.html` — **Fail (P0)**

| Category | Notes |
|---|---|
| 1. Token integrity | `:136` brand mark `<path fill="#22D3B7">` — plain hex inside SVG attribute (no `<defs>`, no gradient). The CSS variable doesn't resolve inside SVG `fill=` so the hex is forced. Acceptable for a 1-color brand mark; P3 alternative: use `style="fill: var(--sb-accent-500)"`. `:151` AC avatar gradient `#1c3868→#0a1428` — bespoke (same gradient as `audit-log.html:49`, `about.html:89`) — hoist to `--sb-grad-avatar-navy` (still deferred from pass-001 P3). `:158-186` per-row inline avatar gradients with bespoke per-workspace hues (`#5e2914/#FF7849 orange`, `#1a223a/#a78bfa violet`, etc.) — same pattern as `audit-log.html` per-actor avatar tinting. Acceptable per-row brand tinting. `:109-110` `.sb-ws__plan--growth/--enterprise` route via `var(--sb-status-running/--review)` ✓. |
| 2. Color contrast | Dialog bg is `linear-gradient(180deg, rgba(22,30,48,0.96), rgba(11,18,32,0.96))` ≈ #16-22, #0b-12 effective. `.sb-ws__name b` `var(--sb-text)` ≈ 14:1 (AAA). `.sb-ws__name span` `var(--sb-text-faint)` ≈ 4.6:1 (AA). `.sb-ws__plan--scale var(--sb-accent-300)` ≈ 9:1 (AAA). `--growth var(--sb-status-running)` ≈ 6:1. `--enterprise var(--sb-status-review)` ≈ 5:1. Avatar initial colour-on-gradient: AC `var(--sb-accent-300)` on `#1c3868→#0a1428` ≈ 7.5-12:1 ✓ AF `#FF7849` on `#101728→#5e2914` ≈ 4.5-6:1 (passes AA on the darker stop, marginal on the orange stop) AL `#a78bfa` on `#1a223a→#0a0f1c` ≈ 7:1 ✓ HL `#22D3B7` on `#0a3d4a→#06181a` ≈ 7.5:1 ✓ NW `#f87171` on `#3d1a2e→#1a0610` ≈ 5:1 ✓ UM `#94a3b8` on `#2a2a2a→#0f0f0f` ≈ 6:1 ✓ — **BUT** UM row (`:185`) has `style="opacity:0.7"` applied to the **entire row** — this dims the name text `b color:var(--sb-text)` via 0.7 alpha → effective brightness ≈ `#ade1ea` × 0.7 = ~3.8:1 on dialog bg, **below AA 4.5:1 floor**. Even the lighter `span` text drops to ~3.2:1. **P2 contrast violation**. Fix: instead of `opacity`, apply `.sb-ws__row--disabled` with `color: var(--sb-text-faint)` + smaller indicator chip; keep the avatar and name at full opacity. |
| 3. Keyboard a11y | **P0**: `<input autofocus>` (`:144`) opens with cursor in search ✓ — but **no keyboard event handlers anywhere on the page** (no `<script>` tag). The decorative `<kbd>↑↓</kbd><kbd>↵</kbd>` glyphs (`:145`) advertise arrow-key navigation and Enter-to-select that doesn't exist. **P0**: 6 `<div class="sb-ws__row" role="option">` (`:150-190`) — each has `cursor:pointer` and `role="option"` (implies it's a listbox child) but: (a) no `tabindex` so they're not in tab order, (b) the `[role="listbox"]` parent has no `aria-activedescendant`, (c) no click handler. **Keyboard users cannot select a workspace**. Mouse users *also* can't — there's no click handler. The dialog is purely visual. **P0**: no `Escape` handler — pressing Esc does nothing. WAI-ARIA APG Dialog pattern mandates Escape closes. **P0**: close button `aria-label="Close"` (`:197`) — focusable, but no `onclick`. Even if clicked, no `<script>` exists to close the dialog. **P1**: focus-trap missing — tab will leak past the close button to the address bar. |
| 4. Semantic HTML | `<article role="dialog">` (`:134`) ✓ but **`aria-modal="true"` MISSING** (brief mandated). `aria-labelledby="ws-title"` ✓. H1 once (`:137`) ✓. `<header class="sb-ws__head">` ✓. `<footer class="sb-ws__foot">` ✓. `[role="listbox"] aria-label="Your workspaces"` (`:149`) ✓. `[role="option"]` ✓. Search `<input>` (`:144`) — has `autofocus` ✓ but **no `aria-label`** (label wraps but text-free) — add `aria-label="Filter workspaces"`. |
| 5. Responsive | **Zero `@media` rules.** Dialog is `width: min(720px, 100%)` ✓ — fluid. `max-height: 88vh` ✓ — won't overflow viewport. `.sb-ws__row` is `grid-template-columns: 44px 1fr auto auto` — at 360px the workspace name + region/seats string in `<span>` (`:152, 159, 166`) will be very tight; e.g. "24 seats · region eu-central-1 · 387 / 1,000 renders this cycle" is 65 chars + 44px avatar + plan pill + shortcut = overflow risk. Add 480 breakpoint that drops `.sb-ws__shortcut` (kbd hints) on mobile. |
| 6. Copy review | "Switch workspace" → minimal, correct for a command-palette dialog. "Filter workspaces · type to search" → terse. Per-row name + sub ("24 seats · region eu-central-1 · 387 / 1,000 renders this cycle") → information-dense, shipped-grade. "Umbra Co · Trial · 25 / 25 renders · expires 2026-05-28" → real-feeling product copy. Footer links ("+ New workspace", "Workspace settings") → clear. |
| 7. Performance hygiene | Preconnect ✓. No images. Single inline `<style>` ~120 lines (~3.5 KB). **No JS**. |
| 8. Showcase wiring | Favicon ✓. **Missing all 5 OG/Twitter tags** — though for a dialog page the OG meta is defensible to skip (the page isn't a share target); minimum favicon ✓. |
| 9. Brand consistency | Brand mark in head ✓ (`:136`). `.sb-ws__row--current` accent-tinted bg ✓ (`:78`). `.sb-ws__plan--scale` accent ✓ (`:108`). `.sb-ws__avatar` uses `var(--sb-accent-300)` as the default initial colour ✓. |
| 10. Cross-page consistency | Standalone dialog page — no shell. The dialog vocabulary (radius-xl, `border-strong`, `shadow-lg`) matches `new-video.html:167` wizard. Both should grow toward a shared `.sb-modal` base class. **The dialog ARIA contract diverges from `new-video.html`**: the wizard at `new-video.html:167` has `aria-modal="true"` (added in pass 002 Refine), this page does not — direct regression-shaped gap. |

---

## Pass-003 regression check

Verified the 24-item Refine queue from pass 003. Most fixes held — the drift surfaces are new (the 6 pages in this audit ship same anti-patterns the prior ring scrubbed elsewhere).

| # | Pass-003 item | Status in pass 004 | Evidence |
|---|---|---|---|
| 1 | `login.html` pre-filled password value drop | **Held** | `login.html:192` no longer ships `value="••…"` |
| 2 | `project-detail.html` focusable tab strip + `role="tablist"` | **Held** | `project-detail.html:168-173` has full ARIA + real `href` |
| 3 | `gallery.html` reel cards focusable | **Skipped (P0 deferred)** | Refine ring 003 explicitly deferred this — `gallery.html:178` reel cards still not focusable. The same anti-pattern reappears on **`localisation.html:240-244`** "Add a language" tile (new site). |
| 4 | `notifications.html` `.glyph--*` modifier classes | **Held** | `notifications.html:48-65, :127-204` use modifier classes |
| 5 | `notifications.html` OG/Twitter meta | **Held** | `notifications.html:7-13` carries 5-tag block |
| 6 | `login.html` `<main>` landmark + login-art.svg + OG | **Held** | verified intact |
| 7 | `customer-story.html` `<main>` un-nest + nav + copy | **Held** | verified intact |
| 8 | `customer-story.html` KPI gradient token | **Held** | `:84` gradient now uses `var(--sb-status-running)` |
| 9 | `status.html` uptime cell tokens + OG | **Held** | `:85-86` use `var(--sb-status-queued/--failed)`; OG block at `:8-12` |
| 10 | `changelog.html` pill tokens + OG | **Held** | `:94-96` token-routed; OG block complete |
| 11 | `docs.html` code-keyword token + OG | **Held** | `:130` uses `var(--sb-status-queued)`; OG block complete |
| 12 | `gallery.html` OG meta | **Held** | verified intact |
| 13 | `integrations.html` OG meta | **Held** | verified intact |
| 14 | `components.html` OG meta | **Held** | verified intact |
| 15 | `project-detail.html` OG meta | **Held** | verified intact |
| 16 | Marketing-nav active-state class promotion | **Drift (P2)** | Pass 003 deferred; **5 new sites of inline `style="color:var(--sb-text)"`** flagged on customer-story / gallery / changelog / docs / status, **plus `about.html:164` (this audit)** = 6 sites total still pending |
| 17 | `<a class="sb-brand">` `aria-label="ShadowBlade home"` | **Drift (P2)** | Pass 003 fixed customer-story only; **`help.html:161` and `about.html:156` (this audit)** carry the same gap = 6 brand-link sites pending |
| 18 | `<header class="sb-marketing__nav">` → wrap inner `<nav>` | **Drift (P2)** | Pass 003 fixed customer-story only; **`help.html:160` and `about.html:155` (this audit)** carry the same gap |
| 19 | 5-marketing-page `<main>` insertion | **Drift (P1)** | Pass 003 deferred; **`help.html` and `about.html` (this audit)** are 2 new sites with no `<main>` |
| 20 | Status / docs `<main>` + `<nav>` insertion | **Drift (P1)** | Pass 003 deferred; same drift surfaces on help/about |
| 21 | `integrations.html` chip-style hoist | **Drift (P3)** | Pass 003 deferred; **`compare.html:239-241` (this audit)** is a third site of the same 8-prop inline-style chip duplication |
| 22 | `notifications.html` `<button>` for inbox tabs | **Held** | `notifications.html:114-121` |
| 23 | `notifications.html` `data-route="inbox"` + shell entry | **Deferred** | Pass 003 carried forward — out of scope this audit |
| 24 | `project-detail.html` 480px version-row breakpoint | **Deferred** | Pass 003 carried forward — visible on similar narrow grids; **`audit-log.html` has zero breakpoints (this audit, new site)** |

### Pass-001 / pass-002 regression check
All earlier-pass fixes hold. Global `:focus-visible` (`styles/app.css:44-58`) covers new pages by inheritance. The `.sb-stage__index--*` modifier classes (pass 002 #9) are not applied on any audit-004 page because none use the stage-index pattern. `.sb-pill--{rendering,running,queued,done,review,scripting,draft,failed,succeeded}` modifiers (`app.css:560-568`) **are** used by `localisation.html` (5×) and `audit-log.html` (1× LIVE) — good. `compare.html:239-241` is a missed opportunity to use them.

---

## Refine queue · pass 004

Ordered by severity. Each item is one concrete Edit. Old strings verified unique within the named file.

### 1. **P0** · `workspace-switcher.html` — add `aria-modal="true"` to dialog

```diff
-    <article class="sb-ws" role="dialog" aria-labelledby="ws-title">
+    <article class="sb-ws" role="dialog" aria-modal="true" aria-labelledby="ws-title">
```
→ `workspace-switcher.html:134`

### 2. **P0** · `workspace-switcher.html` — wire Esc/Enter/Arrow keyboard contract

Append before `</body>`:

```html
<script>
  (function () {
    var rows = Array.from(document.querySelectorAll('.sb-ws__row'));
    var input = document.querySelector('.sb-ws__filter input');
    var dialog = document.querySelector('.sb-ws');
    var closeBtn = document.querySelector('.sb-ws__foot .sb-btn');
    var focusIdx = rows.findIndex(r => r.classList.contains('sb-ws__row--current'));
    if (focusIdx < 0) focusIdx = 0;
    rows.forEach((r, i) => {
      r.setAttribute('tabindex', i === focusIdx ? '0' : '-1');
      r.addEventListener('click', () => location.assign('dashboard.html'));
    });
    function move(delta) {
      rows[focusIdx].setAttribute('tabindex', '-1');
      focusIdx = (focusIdx + delta + rows.length) % rows.length;
      rows[focusIdx].setAttribute('tabindex', '0');
      rows[focusIdx].focus();
    }
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { history.back(); }
      else if (e.key === 'ArrowDown') { e.preventDefault(); move(1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); move(-1); }
      else if (e.key === 'Enter' && document.activeElement === input) {
        rows[focusIdx].click();
      }
    });
    closeBtn && closeBtn.addEventListener('click', () => history.back());
  })();
</script>
```
→ insert at `workspace-switcher.html:201` (just before `</body>`).
Also: rows need `tabindex` to participate in roving focus (the JS above sets it dynamically). Add `aria-label="Filter workspaces"` to the search input (`:144`).

### 3. **P0** · `workspace-switcher.html` — search input `aria-label`

```diff
-          <input placeholder="Filter workspaces · type to search" autofocus />
+          <input aria-label="Filter workspaces" placeholder="Filter workspaces · type to search" autofocus />
```
→ `workspace-switcher.html:144`

### 4. **P1** · `audit-log.html` — verb-pill tokens

```diff
-      .sb-audit-row .verb--update { color: #38BDF8; background: rgba(56,189,248,0.1); }
-      .sb-audit-row .verb--delete { color: #f87171; background: rgba(248,113,113,0.1); }
-      .sb-audit-row .verb--auth   { color: #a78bfa; background: rgba(167,139,250,0.1); }
-      .sb-audit-row .verb--render { color: #fbbf24; background: rgba(251,191,36,0.1); }
+      .sb-audit-row .verb--update { color: var(--sb-status-running); background: rgba(56,189,248,0.1); }
+      .sb-audit-row .verb--delete { color: var(--sb-status-failed);  background: rgba(248,113,113,0.1); }
+      .sb-audit-row .verb--auth   { color: var(--sb-status-review);  background: rgba(167,139,250,0.1); }
+      .sb-audit-row .verb--render { color: var(--sb-status-queued);  background: rgba(251,191,36,0.1); }
```
→ `audit-log.html:85-88`

### 5. **P1** · `audit-log.html` — responsive collapse for narrow viewports

Append to inline `<style>` block:

```css
@media (max-width: 720px) {
  .sb-audit-row {
    grid-template-columns: 1fr;
    gap: var(--sb-space-2);
    padding: var(--sb-space-3) var(--sb-space-4);
  }
  .sb-audit-row .meta { text-align: left; }
  .sb-audit-filter { padding: var(--sb-space-3) var(--sb-space-4); }
  .sb-audit-filter input[type="search"] { min-width: 100% !important; }
}
```
→ append to `audit-log.html:89` style-block close

### 6. **P1** · `audit-log.html` — OG/Twitter meta block (5 tags)

```diff
   <link rel="icon" type="image/svg+xml" href="/showcase/brand/favicon.svg" />
+  <meta property="og:title" content="Audit log · ShadowBlade" />
+  <meta property="og:description" content="Tamper-evident, retained 7 years, streamable to your SIEM. Every event in the workspace." />
+  <meta property="og:image" content="/showcase/screens/screen-dashboard.svg" />
+  <meta name="twitter:card" content="summary_large_image" />
+  <meta name="twitter:image" content="/showcase/screens/screen-dashboard.svg" />
```
→ `audit-log.html:7-8`. Same five-line insert for: `help.html:7-8`, `compare.html:7-8`, `localisation.html:7-8`, **`about.html:8-9`** (about has og:image only — needs the other 4 tags). For `about.html` the existing og:image stays; add og:title/og:description/twitter:card/twitter:image.

### 7. **P1** · `help.html` — insert `<h2>` to fix H1→H3 skip

```diff
     <section class="sb-help-grid">
+      <h2 class="visually-hidden">Browse by topic</h2>
       <article class="sb-help-cat">
```
→ `help.html:191`. (Add `.visually-hidden { position:absolute; clip:rect(0 0 0 0); width:1px; height:1px; overflow:hidden; }` to `app.css` if not present.) Alternative: promote each `.sb-help-cat h3` to `h2` and tighten the visual size in CSS.

### 8. **P1** · `help.html` + `about.html` — `<main>` landmark insertion

For `help.html`:

```diff
-    <section class="sb-help-hero">
+    <main>
+    <section class="sb-help-hero">
…
-    </section>
-
-    <footer class="sb-footer">
+    </section>
+    </main>
+
+    <footer class="sb-footer">
```
→ wrap the 4 `<section>` siblings (`help.html:173-274`) in `<main>`.

Same for `about.html`: wrap `<section class="sb-about-hero">` through `<section class="sb-quotes">` (`about.html:170-244`) in `<main>`.

### 9. **P1** · `help.html` — search `<input>` `aria-label`

```diff
-        <input placeholder="Search 412 help articles…" />
+        <input aria-label="Search help articles" placeholder="Search 412 help articles…" />
```
→ `help.html:179`

### 10. **P2** · `workspace-switcher.html` — replace `opacity:0.7` with token-routed disabled state

```diff
-        <div class="sb-ws__row" role="option" style="opacity:0.7">
+        <div class="sb-ws__row sb-ws__row--inactive" role="option">
```
→ `workspace-switcher.html:185`

Add CSS in inline `<style>`:

```css
.sb-ws__row--inactive .sb-ws__name b { color: var(--sb-text-muted); }
.sb-ws__row--inactive .sb-ws__name span { color: var(--sb-text-faint); }
.sb-ws__row--inactive .sb-ws__avatar { filter: saturate(0.5); }
```
Keeps contrast above AA on the name; communicates "inactive" without crushing the entire row.

### 11. **P2** · `compare.html` — adopt `.sb-pill--*` modifiers on change-set pills

```diff
-                <span class="sb-pill" style="color:var(--sb-accent-300);background:rgba(34,211,183,0.12)">+2 add</span>
-                <span class="sb-pill" style="color:var(--sb-status-running);background:rgba(56,189,248,0.12)">~1 change</span>
-                <span class="sb-pill" style="color:var(--sb-status-failed);background:rgba(248,113,113,0.12)">−1 remove</span>
+                <span class="sb-pill sb-pill--done">+2 add</span>
+                <span class="sb-pill sb-pill--running">~1 change</span>
+                <span class="sb-pill sb-pill--failed">−1 remove</span>
```
→ `compare.html:239-241`

### 12. **P2** · `compare.html` — "Adopt v17" affordance

```diff
-            <button class="sb-btn sb-btn--primary">
+            <button class="sb-btn sb-btn--primary" aria-describedby="adopt-help">
               <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 13l4 4L19 7"/></svg>
               Adopt v17
             </button>
+            <span id="adopt-help" class="visually-hidden">Adopting v17 publishes it as the live cut. You can restore v16 from the Versions tab if needed.</span>
```
→ `compare.html:133-136`. Alternative: wire a `confirm()` modal.

### 13. **P2** · `about.html` — marketing-nav active state via class

```diff
-      <a class="link" href="about.html" style="color:var(--sb-text)">About</a>
+      <a class="link is-active" href="about.html" aria-current="page">About</a>
```
→ `about.html:164`. Same pattern as pass 003 §13.

### 14. **P2** · `about.html` + `help.html` — brand link `aria-label`

```diff
-      <a class="sb-brand" href="index.html">
+      <a class="sb-brand" href="index.html" aria-label="ShadowBlade home">
```
→ `about.html:156`, `help.html:161`

### 15. **P2** · `about.html` + `help.html` — wrap inner `<nav>` around link items

For `about.html`:

```diff
       <span class="spacer"></span>
+      <nav aria-label="Primary">
       <a class="link" href="features.html">Product</a>
       <a class="link" href="pricing.html">Pricing</a>
       <a class="link" href="customer-story.html">Customers</a>
       <a class="link is-active" href="about.html" aria-current="page">About</a>
       <a class="link" href="docs.html">Docs</a>
+      </nav>
       <a class="sb-btn sb-btn--ghost" href="login.html">Sign in</a>
```
→ `about.html:160-168`. Equivalent at `help.html:165-170`.

### 16. **P2** · 3 shell pages — `<div class="sb-breadcrumb">` → `<nav aria-label="Breadcrumb">`

```diff
-          <div class="sb-breadcrumb">
+          <nav class="sb-breadcrumb" aria-label="Breadcrumb">
…
-          </div>
+          </nav>
```
→ `audit-log.html:97-103`, `compare.html:118-126`, `localisation.html:96-104`. (This is repo-wide drift — every shell page has the same gap; suggest hoisting the breadcrumb fragment into a shared component.)

### 17. **P2** · `about.html` — press-kit link copy or asset

The link text says "auto-generated from /showcase" but the description claims ZIP. Either:

```diff
-        <p style="color:var(--sb-text-muted);margin:0;font-size:var(--sb-text-sm)">Logos, product screenshots, leadership photos, brand colours, history milestones. ZIP, ~28 MB.</p>
-        <a href="/showcase/INDEX.md">Download press kit (auto-generated from /showcase) →</a>
+        <p style="color:var(--sb-text-muted);margin:0;font-size:var(--sb-text-sm)">Logos, product screenshots, leadership photos, brand colours, history milestones — indexed inside <code>/showcase</code>.</p>
+        <a href="/showcase/INDEX.md">Browse the press-kit index →</a>
```
→ `about.html:218-219`. Or have Showcase ring zip the dir to `/showcase/press-kit.zip` and point at that.

### 18. **P3** · `localisation.html` — flag glyph SR cleanup

Add `aria-hidden="true"` on `.sb-lang__flag` (5 instances: `localisation.html:172, :186, :200, :214, :228`). The `<b>` lang name immediately follows — SR doesn't need the glyph.

### 19. **P3** · `localisation.html` — "Add a language" tile decision

Either (A) delete the duplicate tile at `:240-244` (the topbar `+ Add language` button at `:106` already covers it), or (B) wrap content in `<button>` and hoist a `.sb-lang--add` modifier.

### 20. **P3** · `audit-log.html` — header row inline-style hoist

Replace `<div class="sb-audit-row" style="9-prop block">` at `:152` with `<div class="sb-audit-row sb-audit-row--head">` and lift the 9 props into a single `.sb-audit-row--head` class in the page `<style>` block.

### 21. **P3** · `about.html` — 3 inline `<b style="color:var(--sb-text)">` hoist

Replace inline `style="color:var(--sb-text)"` on three `<b>` at `:181-183` with `class="sb-about-em"`; add `.sb-about-body .sb-about-em { color: var(--sb-text); font-weight: 600; }` to the inline `<style>`.

### 22. **P3** · `<time>` `datetime` attribute

Every `<time>14:13:24.802</time>` should carry an ISO-8601 `datetime="…"` for SR/parser clarity. Sites: `audit-log.html:156, 162, 168, 174, 180, 186, 192, 198, 204, 210` and `compare.html:165, 198`. Mechanical.

### 23. **P3** · Data-table semantics

`audit-log.html` event log is true tabular data (10 × 4) rendered as `<div>` grid — convert to `<table><thead><tbody>` or retrofit with `role="table" / "row" / "cell"`. Workspace-switcher list is already `role="listbox"` ✓ — keyboard wiring is in item 2.

### 24. **P3** · Shared `.sb-grad-avatar-navy` token

Gradient `linear-gradient(135deg, #1c3868, #0a1428)` repeats in `audit-log.html:49, :157`, `about.html:89`, `workspace-switcher.html:151`. Add `--sb-grad-avatar-navy` to `tokens.css` and route the 4 sites through it. (Pass-001 P3 deferral still live.)

---

## Pass-003 drift summary

| Drift | Severity | New sites in pass 004 |
|---|---|---|
| Inline-style `style="color:var(--sb-text)"` marketing-nav active state | P2 | `about.html:164` (6th site) |
| `aria-label="ShadowBlade home"` on `<a class="sb-brand">` | P2 | `help.html:161`, `about.html:156` |
| `<header class="sb-marketing__nav">` missing nested `<nav>` | P2 | `help.html:160`, `about.html:155` |
| 2 marketing pages missing `<main>` landmark | P1 | `help.html`, `about.html` |
| Inline 8-prop `<span class="sb-pill" style="…">` not using `.sb-pill--*` modifiers | P2 | `compare.html:239-241` (3rd site after templates, integrations) |
| Status hex literals duplicating `--sb-status-*` tokens in page CSS | P1 | `audit-log.html:85-88` (4 verb-pill rules) |
| Unfocusable "card with cursor:pointer" anti-pattern | P0 | `localisation.html:240-244` "Add a language" tile (2nd site after gallery reel cards) |
| `<div class="sb-breadcrumb">` not `<nav>` | P2 | `audit-log.html`, `compare.html`, `localisation.html` (3 sites, repo-wide gap) |
| Pages missing full OG/Twitter 5-tag block | P1 | 5 sites — `audit-log`, `help`, `compare`, `localisation`, `about` (about partial) |

**Five drifts carried forward unbroken from pass 003.** The Refine ring should consider promoting the shared marketing-nav pattern into `components/marketing-nav.html` (mirror the `components/shell.html` sidebar fragment) so future marketing pages inherit aria-label, nav-wrap, and active-state machinery for free.

**No pass-001 / pass-002 fixes regressed.**

---

## Final tally

- **Pass / warn / fail**: 0 / 5 / 1
- **P0 findings**: 3 (all in `workspace-switcher.html` — missing `aria-modal`, no Esc/Enter handler, listbox options not focusable)
- **P1 findings**: 9 across all 6 pages
- **P2 findings**: 11 (mostly drifts from pass 003)
- **P3 findings**: 7

The 6 pages ship clean visual design and good copy — the failures are all under the waterline (ARIA contracts, missing keyboard handlers, social-meta wiring, repo-wide drift). `workspace-switcher.html` is the only **Fail** because a dialog without keyboard control and `aria-modal` violates the WAI-ARIA APG Dialog pattern at the contract level. Once the JS wiring lands and the 5 missing OG/Twitter blocks are added, the entire batch lifts to Pass/Warn.
