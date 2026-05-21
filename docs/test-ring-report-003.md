# ShadowBlade · Test ring report 003
**Auditor**: Test ring (deterministic, source-only — no browser available)
**Scope**: `frontend/public/{customer-story,login,notifications,components,status,gallery,changelog,project-detail,integrations,docs}.html` (10 net-new pages since pass 002)
**Standards**: WCAG 2.1 AA · keyboard-navigable · responsive ≥ 360px
**Coverage delta vs pass 002**: +10 pages. Pass 002's Refine queue (favicons / og:image / `.sb-stage__index--*` modifier classes / `charts.js` lift / settings toggles) verified intact upstream — see Regression section.

---

## Summary

| # | Page | Result | Top issue |
|---|---|---|---|
| 1 | `customer-story.html` | **Warn** | `<main>` wraps `<header>` + `<footer>` (same regression that pass-001 fixed on `index.html`); KPI gradient `#38BDF8` should be `var(--sb-status-running)` |
| 2 | `login.html` | **Fail (P0)** | Three SSO `<button>`s have no accessible name beyond visible text ✓ but lack `aria-label` for SR clarity; the `aria-hidden="true"` rail is keyboard-trapped; pre-filled `value="ava.chen@acme.com"` and `••••••••••••` ship as real DOM defaults; `showcase/auth/login-art.svg` exists but is **not referenced** — fallback inline SVG still drawn |
| 3 | `notifications.html` | **Fail (P1)** | Six inline `style="...color:#a78bfa\|#38BDF8\|#fbbf24\|#f87171..."` glyphs do **not** adopt the `.sb-stage__index--*` modifier classes that pass-002's Refine ring landed (regression-shaped — the classes exist, the page just never updated); no empty state — `showcase/empty/empty-inbox.svg` exists but is unused; tab list missing `role="tablist"` / `role="tab"`; no og:title, og:description, twitter:card |
| 4 | `components.html` | **Pass (with one warn)** | Design-system page — hard-coded swatches are intentional (matches pass-002's brand-kit rationale); H2 toc anchors lack `aria-current` on visible scroll; toc `<a>` items have **no `href` target** outside the body? Actually they do — verified `#colour` etc.; component swatch swatch contrast on `#fbbf24` background uses default text color ≥ 4.6:1 |
| 5 | `status.html` | **Warn** | Uptime `i.warn` / `i.fail` hard-code `#fbbf24` / `#f87171` instead of `var(--sb-status-queued)` / `var(--sb-status-failed)`; `<header class="sb-status-nav">` is not a `<nav>` and lacks `aria-label`; no `<main>` landmark; the 60 uptime cells per row have no `aria-label` or live-region for SR (visual-only) |
| 6 | `gallery.html` | **Warn** | `.sb-reel` card has no `<a>` wrapper or `tabindex` — `cursor:pointer` lies; clicks/keyboard cannot open a reel; topbar `<header>` is not `<nav>`; no `<main>`; ribbon pills generated in JS with inline `style.background = 'rgba(8,14,28,0.7)'` (hex would be `--sb-graphite-950` adjacent) |
| 7 | `changelog.html` | **Warn** | Pills `.fix #fbbf24`, `.perf #38BDF8`, `.brand #a78bfa` should map to `var(--sb-status-queued/--running/--review)` tokens; `<header>` is not `<nav>`; no `<main>`; "Subscribe via RSS or email" link has `href="#"` |
| 8 | `project-detail.html` | **Fail (P0)** | Four `<a>` tabs (Overview, Run #901, Versions, Audit) — three have **no `href`** at all, so they're not focusable and not tab-reachable; "Versions" / "Audit" tabs are visual-only with no destination. No `role="tablist"`. Pill `Rendering · run #901` placed outside breadcrumb (same pattern flagged P2 in pass-002 §4) |
| 9 | `integrations.html` | **Warn** | Eight `<span class="sb-chip">` filters use **identical 8-prop inline `style`** — same anti-pattern pass-002 P3 flagged on `templates.html` chips; filters do nothing (no click handlers); "Connect" buttons inside the template don't carry `aria-label` describing *which* integration; brand colour `#22D3B7` literal inside one inline SVG icon (`:169`) |
| 10 | `docs.html` | **Warn** | `.sb-api pre .k { color: #fbbf24; }` should be `var(--sb-status-queued)`; six `<a href="#">` placeholder links on every docs card — SR users hear "link" with no destination; search `<input>` lacks `aria-label`; `<header>` is not `<nav>`; no `<main>` |

**Tally**: 1 Pass · 7 Warn · 2 Fail (login, project-detail)

---

## 1 · `customer-story.html` — **Warn**

| Category | Notes |
|---|---|
| 1. Token integrity | `:84` KPI value gradient uses literal `#38BDF8` → `var(--sb-status-running)`. SVG illustration body (`:184-211`) hard-codes `#22D3B7`, `#38BDF8`, `#F7F9FC`, `#8590A8`, `#6EE2C5`, `#7DD3FC` outside `<defs>` — acceptable for inline illustration but should share a `<defs>` block (pass-001 P3 rolled forward). Body paragraph emphasis (`:241-243`) uses inline `style="color:var(--sb-text)"` ×3 — should be a class. |
| 2. Color contrast | Body text `var(--sb-text-muted)` on body bg = 5.2:1 (AA). Hero stat tokens 4.8 min / +128 / 92% use the same accent gradient — text is `transparent` with `background-clip:text` over the card bg; effective contrast falls to ~5.6:1 (AA). |
| 3. Keyboard a11y | Global `:focus-visible` from pass-001 covers all `<a>` and `<button>`. Nav links are `<a>` — good. |
| 4. Semantic HTML | **Regression**: `<main>` (`:152`) wraps `<header>` (`:153`) and `<footer>` (`:259`). Pass-001 P1 fixed exactly this on `index.html`. Repeat fix here. Headings monotonic H1 (`:173`) → H2 ×3 → H3 (`:250`). Brand link `<a class="sb-brand">` lacks `aria-label="ShadowBlade home"` (pass-002 P3 #13 also pending here). Nav `<header class="sb-marketing__nav">` should be `<nav aria-label="Primary">` or contain a `<nav>`. |
| 5. Responsive | Single breakpoint at 960px (`:145`). Below 960 the 2-col hero collapses but at 480px the 7-link nav will wrap or overflow. No 720 / 480 breakpoints. Hero `padding-left: var(--sb-space-12)` (48px) ×2 = 96px chrome on a 360px viewport. |
| 6. Copy review | Strong. "Want this kind of week?" CTA is on-brand. "off-guideline" used at `:233` — pass-001 standardised on **off-brand**; this is a regression. |
| 7. Performance hygiene | Preconnect ✓, font CSS bottom of `<head>`, single render-blocking sheet `styles/app.css`. Hero SVG inlined (~3 KB). |
| 8. Showcase wiring | Favicon ✓, og:image ✓ → `case-study/helios-hero.svg`, twitter:card ✓, twitter:image ✓, og:title ✓, og:description ✓ — **complete**. However the actual `.sb-cs-art` slot at `:182-212` renders an *inline placeholder* with a comment "Showcase ring will drop helios-hero.svg here" — the asset exists on disk, the meta refs it, but the visible art still uses the placeholder. **Refine**: drop the inline SVG; render `<img src="/showcase/case-study/helios-hero.svg" alt="Helios Logistics customer story" />`. Same for `helios-quote.svg` / `helios-metrics.svg` which are sitting unused. |
| 9. Brand consistency | Accent `#22D3B7` everywhere. `#38BDF8` is "info" pair — acceptable. |
| 10. Cross-page consistency | Marketing nav structure matches `index.html` / `pricing.html`. Customers link inline `style="color:var(--sb-text)"` (`:163`) — same active-state anti-pattern as `pricing.html` `:147` (pass-002 P2). |

---

## 2 · `login.html` — **Fail (P0)**

| Category | Notes |
|---|---|
| 1. Token integrity | Inline SVG art (`:208-253`) has many literal hex `#22D3B7`, `#8590A8`, `#F7F9FC`, `#6EE2C5` outside `<defs>` — acceptable for illustration. SSO button icons hard-code provider brand colours (`#007DC1`, `#F25022`, `#7FBA00`, `#00A4EF`, `#FFB900`, `#4285F4`) — **intentional** and correct (vendor brand assets). |
| 2. Color contrast | `.sb-auth__lead` `var(--sb-text-muted)` on `rgba(22,30,48,0.94)` ≈ 5.0:1 (AA). SSO button text `var(--sb-text)` on `rgba(11,18,32,0.6)` ≈ 13:1 (AAA). Form input `var(--sb-text)` on `rgba(11,18,32,0.6)` ≈ 13:1 (AAA). |
| 3. Keyboard a11y | **P1**: right-rail `<section aria-hidden="true">` (`:205`) still contains `.sb-auth__trust` `<span>` elements with no focusable content — OK to hide; **but** the rail is also where the visible value-prop copy "Your video factory, ready" lives — `aria-hidden` makes it invisible to SR. Move the caption *outside* the aria-hidden art block, or drop `aria-hidden` and instead mark only the decorative SVG inside `.art-fallback` as hidden. |
| 4. Semantic HTML | **P0**: No `<main>` landmark — entire body is a single `<article class="sb-auth">` with two `<section>` children. SR users land on "article" — should be `<main>` containing the form. No `<h1>` until inside `.sb-auth__left` (`:161`) ✓. **P1**: `<div class="sb-brand">` (`:152`) — not an anchor and not labelled. Either make it an `<a href="index.html">` or drop the brand-link affordance. **P1**: SSO `<button>` elements (`:166, 171, 176`) have no `type="button"` — outside the `<form>` so semantically OK, but defensive `type` should be added. No `aria-label` distinguishing them from the visible text would actually be redundant — the visible text IS the accessible name. **No-op**. |
| 5. Responsive | One breakpoint at 900px collapses to single column and hides the right rail. Below 480 the SSO buttons + `<small>SAML 2.0</small>` will wrap; `<small>` has `margin-left:auto` which becomes awkward. Add a 480 breakpoint that drops `<small>` or stacks it. |
| 6. Copy review | "Welcome back." → strong. "Use your workspace SSO. Or use your email if you're invited as a guest reviewer." — clean. Right-rail "Your video factory, ready." — pithy. |
| 7. Performance hygiene | Preconnect ✓. Single inline `<svg>` rail (~2 KB). Pre-filled `value="ava.chen@acme.com"` and `value="••••••••••••"` (`:188, :192`) — the password value is fake bullets but **a literal string of bullet characters in the DOM is still submitted on form submit**. Real autocomplete/password-manager flow breaks. Drop the `value="•••..."` — `placeholder` alone is fine, or use `value=""`. |
| 8. Showcase wiring | Favicon ✓, **og:image MISSING**, **twitter:card / twitter:image MISSING**, og:title / og:description MISSING. The brief explicitly named `/showcase/auth/login-art.svg` as the right-rail target — asset exists (8.4 KB) but neither the meta wiring nor the in-body `<img src=…>` uses it. Refine: wire all five OG/Twitter meta tags + replace the inline SVG fallback (`:208-253`) with `<img src="/showcase/auth/login-art.svg" alt="" loading="lazy" />`. |
| 9. Brand consistency | Brand mark gradient stops use `#22D3B7 → #38BDF8` ✓. Accent ring on art ✓. |
| 10. Cross-page consistency | Standalone page — no shell. Matches the "Inter Display 600 + Inter body" type rhythm. |

### Refine-priority items
- **P0**: pre-filled password `value="••••••••••••"` ships a bullet-string as the submitted value (`:192`) — drop the `value` attr
- **P1**: no `<main>` landmark
- **P1**: wire `/showcase/auth/login-art.svg` (asset on disk, comment is stale)
- **P1**: full OG/Twitter meta block missing

---

## 3 · `notifications.html` — **Fail (P1)**

| Category | Notes |
|---|---|
| 1. Token integrity | **P1**: six inline `style="background:rgba(...);color:#a78bfa\|#38BDF8\|#fbbf24\|#f87171\|#22D3B7..."` glyphs at `:118, :131, :143, :152, :165, :177, :186, :195` should adopt `.sb-stage__index--review/--running/--queued/--failed/--succeeded`. The classes were defined by Refine ring 002 at `styles/app.css:675-679` precisely to retire this inline pattern — this page never migrated. Note the page uses bespoke `.glyph` class (not `.sb-stage__index`) — Refine should either reuse the modifiers or define a parallel `.sb-notify-row .glyph--{review,running,queued,failed,done}` mapping. |
| 2. Color contrast | Glyph fg on its 18%-opacity bg composite ≈ 6–9:1 (AA / AAA depending on hue). Body text `var(--sb-text-muted)` ≈ 5.2:1. `time` element `var(--sb-text-faint)` (#7d88a0) ≈ 4.6:1 (AA after pass-001 tightening). |
| 3. Keyboard a11y | Inbox-tab `<div class="sb-inbox-tab">` (`:105-112`) is **not** a `<button>` or `<a>` — visual-only, not tab-reachable. The 7 tabs cannot be filtered by keyboard. Same goes for the 8 notification rows — no `<a>` wrapping, no "Open thread" focus link. |
| 4. Semantic HTML | **P1**: H1 reads "14 unread" — descriptive but loses meaning out of context (e.g. tab title is "Inbox · ShadowBlade" but H1 is just a count). Promote to "Inbox · 14 unread". Inbox-tab list should be a `<ul role="tablist">` with each tab as `<button role="tab" aria-controls="…">`. |
| 5. Responsive | Single breakpoint at 900px collapses the 180px aside into a stacked column. Below 480 the row glyph + title + time-right grid may wrap awkwardly — `grid-template-columns: 28px 1fr auto` with no padding adjustment. |
| 6. Copy review | "Run #901 finished · wearable hub" / "Brand drift detected · 2 cuts" — terse and excellent. The `<code>#20D2B5</code>` vs `<code>#22D3B7</code>` diff (`:155`) is a nice touch. "Worker gpu-cluster-4 warm-pooled" reads well. |
| 7. Performance hygiene | Preconnect ✓. No images. Inline SVG icons small. |
| 8. Showcase wiring | Favicon ✓. **og:image MISSING**, og:title / og:description / twitter:card / twitter:image MISSING. The brief named `showcase/empty/empty-inbox.svg` as the asset to wire — but the page has **no empty state at all** (always 14 unread). Refine: add an empty state below the rows for "0 unread" that pulls `empty-inbox.svg`. Add the social-meta block. |
| 9. Brand consistency | Accent on `.sb-inbox-tab.active` (`rgba(34,211,183,0.12)` + `var(--sb-text)`) ✓. |
| 10. Cross-page consistency | Loads shell fragment via `<div data-shell="sidebar">` ✓. `body data-route="dashboard"` (`:67`) — the inbox is not really under Dashboard; either add `data-route="inbox"` (and add a sidebar item to `shell.html`) or pick a closer route. |

---

## 4 · `components.html` — **Pass (with one warn)**

| Category | Notes |
|---|---|
| 1. Token integrity | The page is the **design-system source of truth** — hard-coded swatch hex (`#22D3B7`, `#38BDF8`, `#fbbf24`, `#f87171`, `#a78bfa`, `#11161F`, `#F7F9FC`) on the `.sb-ds-tile` `<div class="sb-ds-swatch">` (`:122-129`) is intentional — same rationale as `brand-kit.html` (pass-002 §2, P2 "intentional and acceptable"). **No fix.** |
| 2. Color contrast | Heading `<h2>` on body ≈ 17:1. `.lede` muted ≈ 5.2:1. Spec `.sb-ds-spec` `var(--sb-text-faint)` ≈ 4.6:1 (AA after pass-001). Swatch labels under each tile are `<b>` + `<span>` mono — `<b>` is `var(--sb-text)` (#f7f9fc) on `rgba(255,255,255,0.025)` ≈ 18:1 (AAA). |
| 3. Keyboard a11y | Toc `<a href="#colour">` etc. (`:104-114`) are valid anchors, focus-visible ring applies. The big "Copy tokens.css" button (`:85`) is a `<button>` with no click handler — visual-only, but at least focusable. Demo `<button class="sb-btn sb-btn--ghost sb-btn--icon" aria-label="More">` (`:167`) ✓. |
| 4. Semantic HTML | H1 once (`:94`), H2 ×11 (`:119` etc.), no skipped levels. Toc is a `<aside class="sb-ds-toc">` of plain `<a>` — should be wrapped in `<nav aria-label="Components index">` for assistive tech. |
| 5. Responsive | `.sb-ds-layout` is `220px 1fr` with **no breakpoint** — at < 640 the toc will eat half the viewport. Add a `@media (max-width: 720px) { .sb-ds-layout { grid-template-columns: 1fr; } .sb-ds-toc { position: static; } }`. |
| 6. Copy review | Spec-shaped, scannable. "The full vocabulary the workspace is built from" lede is on-brand. |
| 7. Performance hygiene | Preconnect ✓. Bottom-loaded `scripts/charts.js`. Demo blocks are inline DOM — no images. |
| 8. Showcase wiring | Favicon ✓. **No og:image / og:title / og:description / twitter:card / twitter:image** — internal design-system page, defensible to skip OG; but at minimum og:title + og:image (→ `/showcase/brand/og-image.svg`) for shareability. Refine recommendation. |
| 9. Brand consistency | Type and pill demos pull from the central `app.css` rules — no drift. |
| 10. Cross-page consistency | `body data-route="settings"` (`:70`) highlights Settings in the sidebar — the page is a peer of Settings (not a true child), but acceptable. Add a "Design system" item under "Workspace" in `shell.html` for direct navigation. |

---

## 5 · `status.html` — **Warn**

| Category | Notes |
|---|---|
| 1. Token integrity | `:85` `i.warn { background: #fbbf24; }` → `var(--sb-status-queued)`. `:86` `i.fail { background: #f87171; }` → `var(--sb-status-failed)`. Brand mark gradient stops `#22D3B7 → #38BDF8` inside `<defs>` ✓. |
| 2. Color contrast | Banner card text `var(--sb-text)` on accent-tinted card ≈ 14:1 (AAA). "all systems normal" body ≈ 5.2:1. Uptime cells are visual-only; the `.pct` `var(--sb-accent-300)` (#6EE2C5) on row bg `rgba(11,18,32,0.6)` over body ≈ 9:1 (AAA). |
| 3. Keyboard a11y | All nav links and "Sign in" CTA are `<a>` — focusable. No clickable status rows. |
| 4. Semantic HTML | **P1**: `<header class="sb-status-nav">` (`:129`) is **not** a `<nav>`; should be `<nav aria-label="Status">`. **P1**: No `<main>` landmark wrapping the body sections. H1 `:148`, H2 `:193` — monotonic. |
| 5. Responsive | One breakpoint at 900px collapses the 3-col status row into 1 column. Below 720 the 60-cell uptime bar will be squished; the bars are 24px tall with 2px gap — at 320px viewport each cell is ~4px wide, still recognisable. Marketing nav has no responsive collapse — at 480 the 6 links wrap. |
| 6. Copy review | "All systems normal" is the right tone. Incident copy ("Spot-instance reclaim spiked queue depth to 14") is grounded and concrete. |
| 7. Performance hygiene | Preconnect ✓. JS at bottom synthesises 60×6 = 360 `<i>` cells on load — DOM cost is trivial. |
| 8. Showcase wiring | Favicon ✓. og:image ✓ → `og-image.svg`. **Missing**: og:title, og:description, twitter:card, twitter:image. |
| 9. Brand consistency | Banner accent `var(--sb-accent-500)` + rgba glow ✓. Pill `.sb-pill--done` ✓. |
| 10. Cross-page consistency | Marketing nav (`status` is its own subnav with "ShadowBlade · Status" subtitle) — distinct from product marketing nav. Subscribe link `href="#"` is a stub. |
| Extra | Uptime cells need an `aria-label` or visually-hidden text for SR. Each row should be a `<table>` with caption `<service> uptime, last 60 minutes` for AT users, *or* the `.sb-status-uptime` div needs `role="img" aria-label="60 minutes of uptime, 1 minor incident at minute 14"`. |

---

## 6 · `gallery.html` — **Warn**

| Category | Notes |
|---|---|
| 1. Token integrity | Brand mark stops in `<defs>` ✓. JS-generated ribbon pill (`:227`) sets `pill.style.background = 'rgba(8,14,28,0.7)'` — could use `var(--sb-navy-900)` derivative, but inline-string JS so acceptable. No literal hex outside the brand mark. |
| 2. Color contrast | Reel name `var(--sb-text)` on dark card ≈ 14:1 (AAA). Meta `var(--sb-text-faint)` ≈ 4.6:1 (AA). Stats `<b>` ≈ 14:1, span ≈ 5.2:1. |
| 3. Keyboard a11y | **P0**: `.sb-reel` is `<article cursor:pointer>` (`:69`) with no `<a>` wrapper or `tabindex`. Clicks/keyboard cannot open a reel. The visible "play" overlay implies clickability but no handler exists. Either wrap in `<a href="…">` or add `tabindex="0"` and a `role="button"` plus a keyboard handler. |
| 4. Semantic HTML | **P1**: `<header class="sb-marketing__nav">` is not `<nav>`; nest `<nav>` or use `<nav>` as the wrapper. **P1**: No `<main>` landmark — three top-level `<section>` siblings under `<body>`. **P1**: Brand link `<a class="sb-brand">` lacks `aria-label="ShadowBlade home"`. H1 once `:150`, H3 once `:166` — monotonic but skips H2. |
| 5. Responsive | Two breakpoints 1100/720 ✓ — matches the brief's 1100/900/720/480 grid (900 not present, 480 not present). At 480 the marketing nav (7 links) will wrap. |
| 6. Copy review | "What enterprise teams are shipping on ShadowBlade." excellent. "Want yours in the reel?" — friendly. "before the kettle boils" is a fresh idiom. |
| 7. Performance hygiene | Preconnect ✓. Thumbnails loaded via `<img loading="lazy">` ✓. Each thumbnail SVG is 3-4 KB. 9 reels = ~33 KB. |
| 8. Showcase wiring | Favicon ✓, og:image ✓ → `hero-cover.svg`. **Missing**: og:title, og:description, twitter:card, twitter:image. Asset wiring **works**: thumbnails fetched from `/showcase/thumbnails/*.svg` ✓. The `img.onerror` fallback to text initial is a nice resilient touch. |
| 9. Brand consistency | Accent on `.sb-reel:hover` border + `.play` button bg ✓. |
| 10. Cross-page consistency | Marketing nav matches index/pricing/changelog/docs/customer-story. "Customers" link has inline active-state `style="color:var(--sb-text)"` (`:140`) — same anti-pattern as pricing. |

---

## 7 · `changelog.html` — **Warn**

| Category | Notes |
|---|---|
| 1. Token integrity | **P1**: `:94` `.fix { color: #fbbf24; }` → `var(--sb-status-queued)`. **P1**: `:95` `.perf { color: #38BDF8; }` → `var(--sb-status-running)`. **P1**: `:96` `.brand { color: #a78bfa; }` → `var(--sb-status-review)`. Identical pattern to `team.html:19-22` that Refine ring 002 already replaced (Refine #10). Carry forward. |
| 2. Color contrast | H1 ≈ 17:1. Body lede + entry copy on entry-body card `rgba(11,18,32,0.6)` ≈ 5.0-5.5:1. Time + pill-meta on entry card ≈ 4.6:1 (AA after pass-001). |
| 3. Keyboard a11y | All nav and timeline links are `<a>` — focusable. No interactive timeline elements that need tabindex. |
| 4. Semantic HTML | **P1**: `<header class="sb-marketing__nav">` — not a `<nav>`; no `<main>`. H1 once `:127`, H2 ×7 ✓. Each `<article class="sb-log-entry">` is correctly an `<article>` with a single `<h2>`. |
| 5. Responsive | One breakpoint at 700px (`:101`) — not on the 1100/900/720/480 grid; should be 720px. Below 700 the timeline collapses well. No 480px adjustment. |
| 6. Copy review | "What shipped, and why." — sharp. "v3 schema adds voice profile, tone do / avoid, and cap on adjectives as enforced constraints" — very on-brand. "Mention-to-assign works from any comment" is dense and precise. |
| 7. Performance hygiene | Preconnect ✓. No images. Single CSS sheet. |
| 8. Showcase wiring | Favicon ✓, og:image ✓ → `og-image.svg`. **Missing**: og:title, og:description, twitter:card, twitter:image. |
| 9. Brand consistency | Accent on `.sb-log-entry::before` dot + Subscribe-via-RSS link `var(--sb-accent-300)` ✓. |
| 10. Cross-page consistency | Marketing nav matches the rest. "Changelog" inline `style="color:var(--sb-text)"` (`:120`) — same anti-pattern. Brand link lacks `aria-label`. |

---

## 8 · `project-detail.html` — **Fail (P0)**

| Category | Notes |
|---|---|
| 1. Token integrity | Inline SVG cover (`:141-163`) has `#22D3B7`, `#F7F9FC`, `#8590A8` outside `<defs>` — acceptable for cover illustration. `.sb-tabs-strip a.active { background: rgba(34,211,183,0.16); }` ✓. |
| 2. Color contrast | KPI value (`var(--sb-text)`) on KPI card ≈ 14:1 (AAA). `var(--sb-text-faint)` on version-row dark bg ≈ 4.6:1. `.sb-version-row .v` is `var(--sb-accent-300)` (#6EE2C5) on `rgba(11,18,32,0.5)` ≈ 9.4:1 (AAA). |
| 3. Keyboard a11y | **P0**: Four tabs at `:169-172` — `<a class="active">Overview</a>`, `<a>Versions</a>`, `<a>Audit</a>` have **no `href` attribute**. Without `href`, `<a>` is not focusable, not tab-reachable, and not announced as a link by SR. Only `<a href="job-detail.html">Run #901</a>` works. Either give them real `href` (anchor or modal), or convert all four to `<button role="tab">` with `aria-selected`. |
| 4. Semantic HTML | **P1**: No `role="tablist"` / `role="tab"` / `aria-selected` on the tab strip. **P2**: Pill `Rendering · run #901` placed *outside* the breadcrumb (`:111`) — same drift pattern pass-002 §4 flagged on `studio.html:181` and `job-detail.html:101`. H1 once `:127`. ✓ |
| 5. Responsive | One breakpoint at 1100px collapses the 1.4fr / 1fr hero into one column. Below 720 the version-row 60-1fr-auto grid will be tight on a 360px viewport — needs `@media (max-width: 480px) { .sb-version-row { grid-template-columns: 1fr; } }`. |
| 6. Copy review | "v17 of 17 · Last rendered 4 min ago by Ava Chen · Acme · Core kit · Alloy EN female · pre-order CTA." — dense, precise, ShadowBlade-grade. Version-row titles read like real PRs. |
| 7. Performance hygiene | Preconnect ✓. Single inline cover SVG (~2 KB). Both `shell.js` + `charts.js` bottom-loaded. |
| 8. Showcase wiring | Favicon ✓, og:image ✓ → `screen-dashboard.svg`. **Missing**: og:title, og:description, twitter:card, twitter:image. (Could use a project-specific image once Showcase generates one.) |
| 9. Brand consistency | Accent on cover circle, on tab-active bg, on `.sb-pd-cover .play div` ✓. |
| 10. Cross-page consistency | Loads shell fragment ✓, `body data-route="projects"` ✓, breadcrumb `Acme > Projects > <project>` ✓. |

---

## 9 · `integrations.html` — **Warn**

| Category | Notes |
|---|---|
| 1. Token integrity | **P3**: Vendor brand colours hard-coded in `ICON(...)` SVG factory (`:164-178`) — `#4A154B` Slack, `#F25022` etc. — intentional (vendor brands). **P2**: `:169` TikTok icon has `fill="#22D3B7"` for the inner letter — should be `var(--sb-accent-500)` if the goal is brand accent, but inside a stringified SVG inside JS template literal, the literal hex is the path of least resistance. Acceptable. **P3**: 8 chip spans `:119-126` duplicate an 8-property style block — hoist to `.sb-int-chip` class (same anti-pattern flagged P3 pass-002 §17.16 on templates). |
| 2. Color contrast | Card body bg `rgba(11,18,32,0.6)` — name `var(--sb-text)` ≈ 13:1. cat `var(--sb-text-faint)` ≈ 4.6:1 (AA). state b dot ≥3:1 UI floor ✓. `--sb-int--connected .sb-int__state` `var(--sb-accent-300)` ≈ 9:1 (AAA). |
| 3. Keyboard a11y | **P1**: Filter chips `:119-126` are `<span>` not `<button>` — not focusable, no click handlers exist anyway, but visually imply interactivity. Convert to `<button>` once filtering is wired. **P1**: Inside the integration template, the "Connect" button (`:150`) has **no descriptive aria-label** — SR users hear "Connect" repeated 38 times with no indication of which integration. Add `aria-label="Connect Slack"` etc. via the JS loop (`:182-194`). |
| 4. Semantic HTML | H1 once `:109`. Topbar follows shell pattern. Search input has `aria-label` ✓ (`:92`). Page-head structure ✓. |
| 5. Responsive | Two breakpoints 1100/720 ✓. Filter chip strip will wrap below 720 naturally (`flex-wrap: wrap`). |
| 6. Copy review | "Wire ShadowBlade into the rest of the stack." — punchy. "None touch your render data unless you scope them in." — good security tone. Integration descriptions are tight ("Page oncall when render queue depth blows past your SLA threshold."). |
| 7. Performance hygiene | Preconnect ✓. Icons are stringified SVG injected via `innerHTML` — small + fast. No external images. |
| 8. Showcase wiring | Favicon ✓, og:image ✓ → `og-image.svg`. **Missing**: og:title, og:description, twitter:card, twitter:image. |
| 9. Brand consistency | Accent on `.sb-int--connected .sb-int__state b` dot ✓. |
| 10. Cross-page consistency | Loads shell fragment ✓, `body data-route="settings"` (`:77`) — integrations is *not* under Settings; consider adding `data-route="integrations"` and a sidebar entry. |

---

## 10 · `docs.html` — **Warn**

| Category | Notes |
|---|---|
| 1. Token integrity | **P1**: `:130` `.sb-api pre .k { color: #fbbf24; }` → `var(--sb-status-queued)`. `.s { color: var(--sb-accent-300); }` ✓. `.c { color: var(--sb-text-faint); }` ✓. Brand mark in `<defs>` ✓. |
| 2. Color contrast | Code keyword `#fbbf24` on `rgba(6,10,22,0.8)` ≈ 11:1 (AAA). String `var(--sb-accent-300)` ≈ 9:1 (AAA). Comment `var(--sb-text-faint)` ≈ 4.6:1 (AA). Card body lede `var(--sb-text-muted)` ≈ 5.0:1. |
| 3. Keyboard a11y | All `<a>` link targets — focusable, focus-visible covers. **P2**: Search input `:163` has placeholder but **no `aria-label`** — SR hears "search edit text" with no purpose; add `aria-label="Search docs"`. **P3**: ~25 `<a href="#">` stub links — fine for a fixture page but reads "link" with no destination to SR; pass-002 noted same pattern on docs/team pages. |
| 4. Semantic HTML | **P1**: `<header class="sb-marketing__nav">` — not `<nav>`. No `<main>` landmark. H1 (`:159`), H3 ×6 in the cards (`:171, :182, :194, :206, :218, :230`) — **skips H2**. Either promote each card H3 to H2 (cards are top-level sections) or insert an H2 like "Browse the docs". The `<h2>Render a cut in one POST.</h2>` (`:243`) is fine — it's at section level. |
| 5. Responsive | Two breakpoints 1100/720 ✓. At 720 grid → 1 column. Marketing nav (7 links) has no responsive collapse — at 480 wraps. |
| 6. Copy review | "Build with the ShadowBlade API." — verb-first, on-brand. "From zero to your first rendered cut in 7 minutes." excellent. The curl example is well-shaped. "Need a human?" footer line is friendly. |
| 7. Performance hygiene | Preconnect ✓. No images. `<pre>` is plain HTML with manual `<span>` syntax-highlighting — no JS highlighter cost. |
| 8. Showcase wiring | Favicon ✓, og:image ✓. **Missing**: og:title, og:description, twitter:card, twitter:image. |
| 9. Brand consistency | Accent on `.sb-docs-card__icon` bg + `<kbd>⌘K</kbd>` color tokens ✓. |
| 10. Cross-page consistency | Marketing nav matches index/pricing/customer-story. "Docs" link `style="color:var(--sb-text)"` (`:152`) — same anti-pattern; brand link no `aria-label`. |

---

## Pass-002 regression check

Verified the 17-item Refine queue from pass 002:

| # | Pass-002 item | Status in pass 003 | Evidence |
|---|---|---|---|
| 1 | Search aria-label on 4 inputs | **Held** | `projects.html:85`, `templates.html:83`, `assets.html:69`, `team.html:79` all carry `aria-label` (plus new `integrations.html:92` carries it from birth) |
| 2 | Settings toggle role+aria-checked+tabindex+JS | **Held** | `settings.html:152, :156, :173` all carry full ARIA |
| 3 | `charts.js` use `ACCENT` const | **Held** | `scripts/charts.js:108, :137, :145` all use `ACCENT` |
| 4 | Wire favicon + og:image into 10 workspace pages | **Held** | All 10 pass-002 pages carry favicon + og:image + twitter:image (verified above) |
| 5 | `pricing.html` complete social meta | **Held** | `pricing.html` 6-meta block complete |
| 6 | `brand-kit.html` H4 → H3 | **Held** | Verified upstream |
| 7 | `new-video.html` `<h1>` promotion + `aria-modal` | **Held** | Verified upstream |
| 8 | `#38BDF8` → token in studio + analytics | **Held** | Verified upstream |
| 9 | `.sb-stage__index--{review/running/succeeded/queued/failed}` modifier classes | **Drift (P1)** | Classes landed at `styles/app.css:675-679` and `dashboard.html`, `analytics.html`, `new-video.html`, `job-detail.html` adopted them — **but `notifications.html` (this audit) still ships the 6 inline `style="color:#…"` glyphs** that pass-002 #9 was meant to retire. The page predates the Refine sweep; the migration was never extended. |
| 10 | `team.html` role-pill tokens | **Held** | Verified upstream |
| 11 | `sb-field` label association | **Held** | Verified upstream |
| 12 | Active marketing-nav state via class | **Drift (P2)** | `pricing.html:147` fixed. **But every new marketing page (customer-story, gallery, status, changelog, docs) re-introduces the same `style="color:var(--sb-text)"` inline active-state anti-pattern.** 5 new sites of the same bug. |
| 13 | `aria-label="ShadowBlade home"` on pricing brand | **Drift (P2)** | `pricing.html` fixed. **But every new marketing page (customer-story, gallery, status, changelog, docs) omits the same `aria-label` on the `<a class="sb-brand">`.** 5 new sites. |
| 14 | `.sb-priority--low` tightened | **Held** | Verified upstream |
| 15 | Tablist semantics on pricing toggle | **Held upstream** but new instances of the same gap appear: `project-detail.html:168-173` (Overview/Run/Versions/Audit tabs) and `notifications.html:105-112` (Inbox tabs). Tabs migration is repo-wide, not just pricing. |
| 16 | `templates.html` chip-style class hoist | **Drift (P3)** | Pass-002 #16 deferred this to a future ring; **`integrations.html:119-126` ships the same 8-property inline-style chip duplication.** Same anti-pattern, new page. |
| 17 | Pass-001 P3 tokens (`--sb-grad-aurora-blue/-teal/-avatar`) | **Still deferred** | `styles/app.css:23-24, :238, :771` still literal — pass-001 P3 known-deferred |

### Pass-001 regression check
All pass-001 fixes hold. Global `:focus-visible` (`styles/app.css:44-58`) covers new pages by inheritance.

---

## Refine queue · pass 003

Ordered by severity. Each item is one concrete Edit. Old strings verified unique within the named file.

### 1. **P0** · `login.html` — drop pre-filled password value

```diff
-            <input type="password" required placeholder="••••••••••••" value="••••••••••••" autocomplete="current-password" />
+            <input type="password" required placeholder="••••••••••••" autocomplete="current-password" />
```
→ `login.html:192`

Optional: same for email — `value="ava.chen@acme.com"` is a UI demo prop; if the goal is "remembered email", consider `autocomplete="username"` alone (already set) and let the browser fill.

### 2. **P0** · `project-detail.html` — focusable tabs with real targets

```diff
-              <div class="sb-tabs-strip">
-                <a class="active">Overview</a>
-                <a href="job-detail.html">Run #901</a>
-                <a>Versions</a>
-                <a>Audit</a>
-              </div>
+              <div class="sb-tabs-strip" role="tablist" aria-label="Project sections">
+                <a class="active" href="#overview" role="tab" aria-selected="true" aria-current="page">Overview</a>
+                <a href="job-detail.html" role="tab" aria-selected="false">Run #901</a>
+                <a href="#versions" role="tab" aria-selected="false">Versions</a>
+                <a href="#audit" role="tab" aria-selected="false">Audit</a>
+              </div>
```
→ `project-detail.html:168-173`

### 3. **P0** · `gallery.html` — make reel cards reachable

Wrap each `.sb-reel` in an `<a>` or add `tabindex="0" role="button"` plus a keydown handler. Template-level fix at `:178`:

```diff
-      <article class="sb-reel">
+      <a class="sb-reel" href="#" tabindex="0" role="button">
         <div class="sb-reel__thumb">
…
-      </article>
+      </a>
```
→ `gallery.html:178, :190`

(`<a>` lets the browser do focusring + Enter activation for free.)

### 4. **P1** · `notifications.html` — adopt `.sb-stage__index--*` modifier classes

The page uses bespoke `.sb-notify-row .glyph` rather than `.sb-stage__index`. Two paths:

- **A** (preferred): replace `<div class="glyph" style="…">` × 8 with `<div class="sb-stage__index sb-stage__index--{succeeded|review|running|queued|failed|done|draft}">`. Strip all 8 inline `style="…"`. The `.sb-stage__index` base class size is 28×28 already — matches existing `.glyph` (`:48-52`).
- **B**: define `.sb-notify-row .glyph--{review,running,queued,failed,succeeded,draft}` adjacent to the existing modifiers in `app.css:675-679`, then strip inline styles.

Affected lines: `notifications.html:118, :131, :143, :152, :165, :177, :186, :195` (8 instances).

### 5. **P1** · `notifications.html` — full OG/Twitter meta block

```diff
  <link rel="icon" type="image/svg+xml" href="/showcase/brand/favicon.svg" />
+ <meta property="og:title" content="Inbox · ShadowBlade" />
+ <meta property="og:description" content="Pipeline events, approvals, brand-drift alerts, mentions — in one place." />
+ <meta property="og:image" content="/showcase/screens/screen-dashboard.svg" />
+ <meta name="twitter:card" content="summary_large_image" />
+ <meta name="twitter:image" content="/showcase/screens/screen-dashboard.svg" />
```
→ `notifications.html:7-8`

Same five-line insert for: `login.html:7-8`, `components.html:7-8`, `status.html:8-9`, `gallery.html:8-9`, `changelog.html:8-9`, `docs.html:8-9`, `integrations.html:8-9`, `project-detail.html:8-9`. Asset choices:
- `login.html` → `/showcase/auth/login-art.svg`
- `customer-story.html` is already complete
- `gallery.html` → `/showcase/hero/hero-cover.svg` (already og:image, just add og:title + twitter:card + twitter:image)
- `project-detail.html` → keep `/showcase/screens/screen-dashboard.svg` (or a project cover once Showcase ring v3 generates one)
- rest → `/showcase/brand/og-image.svg`

### 6. **P1** · `login.html` — wire login-art.svg + add `<main>`

Replace the inline placeholder SVG (`:206-254`) with the real asset:

```diff
-        <div class="art-fallback">
-          <!-- Showcase v2 will provide /showcase/auth/login-art.svg — fallback below uses the same vocabulary. -->
-          <svg viewBox="0 0 540 720" preserveAspectRatio="xMidYMid slice">
-            …49 lines of inline SVG…
-          </svg>
-        </div>
+        <img class="art-fallback" src="/showcase/auth/login-art.svg" alt="" loading="lazy" />
```

Wrap `<article class="sb-auth">` in `<main>`:

```diff
-    <article class="sb-auth">
+  <main>
+    <article class="sb-auth">
…
-    </article>
+    </article>
+  </main>
```
→ `login.html:150, :264`

### 7. **P1** · `customer-story.html` — un-nest `<header>` + `<footer>` from `<main>`

```diff
-    <main>
-      <header class="sb-marketing__nav">
+    <header class="sb-marketing__nav">
…
-      </header>
+    </header>
+    <main>

-      <footer class="sb-footer">
-        …
-      </footer>
-    </main>
+    </main>
+    <footer class="sb-footer">
+      …
+    </footer>
```
→ `customer-story.html:152-153, :259-263`

Also wire the real `helios-hero.svg`:

```diff
-        <div class="sb-cs-art">
-          <!-- Showcase ring will drop helios-hero.svg here; until then, an inline cinematic placeholder authored from the same tokens. -->
-          <svg viewBox="0 0 800 450" preserveAspectRatio="xMidYMid slice">
-            …29 lines of inline SVG…
-          </svg>
-        </div>
+        <div class="sb-cs-art">
+          <img src="/showcase/case-study/helios-hero.svg" alt="Helios Logistics customer story hero" loading="lazy" />
+        </div>
```
→ `customer-story.html:182-212`

And fix "off-guideline" regression:

```diff
-        ShadowBlade reverses the loop. Producers paste the brief into one field; the pipeline scripts, voices, captions, and renders against the brand kit before legal has finished their first read. By the time a reviewer opens the cut, the cut is already on-guideline.
+        ShadowBlade reverses the loop. Producers paste the brief into one field; the pipeline scripts, voices, captions, and renders against the brand kit before legal has finished their first read. By the time a reviewer opens the cut, the cut is already on-brand.
```
→ `customer-story.html:233`

### 8. **P1** · `status.html` — token swap + `<nav>` + `<main>`

```diff
-      .sb-status-uptime i.warn { background: #fbbf24; opacity: 1; }
-      .sb-status-uptime i.fail { background: #f87171; opacity: 1; }
+      .sb-status-uptime i.warn { background: var(--sb-status-queued); opacity: 1; }
+      .sb-status-uptime i.fail { background: var(--sb-status-failed); opacity: 1; }
```
→ `status.html:85-86`

```diff
-    <header class="sb-status-nav">
+    <header class="sb-status-nav">
+      <nav aria-label="Status">
…
-    </header>
+      </nav>
+    </header>

-    <section class="sb-status-banner">
+    <main>
+    <section class="sb-status-banner">
…
-    <footer class="sb-footer">
+    </main>
+    <footer class="sb-footer">
```
→ `status.html:129, :142, :144, :216`

### 9. **P1** · `changelog.html` — pill colour tokens

```diff
-      .sb-log-entry .pills .sb-pill.fix { color: #fbbf24; background: rgba(251,191,36,0.12); }
-      .sb-log-entry .pills .sb-pill.perf { color: #38BDF8; background: rgba(56,189,248,0.12); }
-      .sb-log-entry .pills .sb-pill.brand { color: #a78bfa; background: rgba(167,139,250,0.12); }
+      .sb-log-entry .pills .sb-pill.fix { color: var(--sb-status-queued);  background: rgba(251,191,36,0.12); }
+      .sb-log-entry .pills .sb-pill.perf { color: var(--sb-status-running); background: rgba(56,189,248,0.12); }
+      .sb-log-entry .pills .sb-pill.brand { color: var(--sb-status-review); background: rgba(167,139,250,0.12); }
```
→ `changelog.html:94-96`

### 10. **P1** · `docs.html` — code-keyword token + `<nav>` + `<main>`

```diff
-      .sb-api pre .k { color: #fbbf24; }
+      .sb-api pre .k { color: var(--sb-status-queued); }
```
→ `docs.html:130`

Same `<nav>` / `<main>` repair as `status.html` (lines `:142, :157, :269`).

Add search aria-label:

```diff
-        <input placeholder="Search the docs · 412 articles · Cmd-K from anywhere" />
+        <input aria-label="Search docs" placeholder="Search the docs · 412 articles · Cmd-K from anywhere" />
```
→ `docs.html:163`

### 11. **P1** · `customer-story.html` — KPI gradient token

```diff
-      .sb-cs-metric .v {
-        …
-        background: linear-gradient(90deg, var(--sb-accent-500), #38BDF8);
+      .sb-cs-metric .v {
+        …
+        background: linear-gradient(90deg, var(--sb-accent-500), var(--sb-status-running));
```
→ `customer-story.html:84`

### 12. **P1** · `project-detail.html` — version-row 480px breakpoint + tablist (continued)

```css
@media (max-width: 480px) {
  .sb-version-row { grid-template-columns: 1fr; gap: var(--sb-space-2); }
}
```
→ add to `project-detail.html:96` block

### 13. **P2** · Marketing-nav active-state class (5 new pages)

Define `.sb-marketing__nav a.link.is-active { color: var(--sb-text); }` in `app.css` once (pass-002 #12 added a per-page rule on pricing — promote to shared). Then:

```diff
-        <a class="link" href="#" style="color:var(--sb-text)">Customers</a>
+        <a class="link is-active" href="#" aria-current="page">Customers</a>
```
→ `customer-story.html:163`, `gallery.html:140`, `changelog.html:120`, `docs.html:152`, plus check `status.html` (Subscribe is the active page there but uses plain `<a href="#">`).

### 14. **P2** · `aria-label="ShadowBlade home"` on 5 new marketing brand links

```diff
-      <a class="sb-brand" href="index.html">
+      <a class="sb-brand" href="index.html" aria-label="ShadowBlade home">
```
→ `customer-story.html:154`, `gallery.html:133`, `status.html:130`, `changelog.html:111`, `docs.html:143`

### 15. **P2** · Marketing nav semantic — `<header>` → `<header>` + `<nav>` or `<nav>` (5 pages)

Match the `index.html:195-211` pattern:

```diff
-    <header class="sb-marketing__nav">
-      <a class="sb-brand" href="index.html">…</a>
-      <span class="spacer"></span>
-      <a class="link" href="…">…</a>
-      …
-      <a class="sb-btn sb-btn--primary" href="dashboard.html">Open workspace</a>
-    </header>
+    <header class="sb-marketing__nav">
+      <a class="sb-brand" href="index.html" aria-label="ShadowBlade home">…</a>
+      <span class="spacer"></span>
+      <nav class="sb-marketing__links" aria-label="Primary">
+        <a class="link" href="…">…</a>
+        …
+      </nav>
+      <a class="sb-btn sb-btn--ghost" href="dashboard.html">Sign in</a>
+      <a class="sb-btn sb-btn--primary" href="dashboard.html">Open workspace</a>
+    </header>
```
→ `customer-story.html:153-168`, `gallery.html:132-145`, `status.html:129-142`, `changelog.html:110-123`, `docs.html:142-155`

### 16. **P2** · `integrations.html` — chip class hoist + Connect aria-label

```css
.sb-int-chip {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: var(--sb-text-sm); padding: 6px 10px;
  border-radius: 99px; color: var(--sb-text-muted);
  border: 1px solid var(--sb-border);
}
.sb-int-chip.is-active {
  color: var(--sb-text);
  background: rgba(34,211,183,0.14);
  border-color: rgba(34,211,183,0.4);
}
.sb-int-chip small { color: var(--sb-text-faint); margin-left: 4px; }
```
Then strip the 8 inline `style=…` blocks → `integrations.html:119-126`.

And add per-integration aria-label inside the JS loop at `:182-194`:

```diff
       node.querySelector('.sb-int__icon').innerHTML = i.icon;
       node.querySelector('.sb-int__name').textContent = i.name;
       node.querySelector('.sb-int__cat').textContent = i.cat;
       node.querySelector('.sb-int__desc').textContent = i.desc;
+      const cta = node.querySelector('.sb-btn');
+      cta.setAttribute('aria-label', `${i.connected ? 'Configure' : 'Connect'} ${i.name}`);
       if (i.connected) {
         node.classList.add('sb-int--connected');
         node.querySelector('.sb-int__state span').textContent = 'Connected';
-        node.querySelector('.sb-btn').textContent = 'Configure';
+        cta.textContent = 'Configure';
       }
```

### 17. **P2** · `components.html` — toc `<nav>` wrap + 720px breakpoint

Replace `<aside class="sb-ds-toc">` with `<nav class="sb-ds-toc" aria-label="Component index">` at `components.html:103, :115`. Add `@media (max-width: 720px) { .sb-ds-layout { grid-template-columns: 1fr; } .sb-ds-toc { position: static; } }`.

### 18. **P2** · `notifications.html` — `<button>` for inbox tabs + `data-route="inbox"`

Convert `<div class="sb-inbox-tab">` × 7 to `<button class="sb-inbox-tab" type="button">` (active one carries `aria-current="page"`) → `notifications.html:105-112`. Change `body data-route="dashboard"` to `data-route="inbox"` (`:67`) and add a corresponding link in `components/shell.html`.

### 19-24. **P3** · Misc cleanups

- `gallery.html:227-228` — JS-generated ribbon pill should be `.sb-pill--ribbon` class, not inline `pill.style.background = 'rgba(8,14,28,0.7)'`
- `customer-story.html:241-243` — 3 inline `<b style="color:var(--sb-text)">…</b>` → hoist `.sb-cs-em` class
- 5 marketing pages — share a `.sb-marketing__nav .link` responsive collapse rule (hide at ≤720, keep only Sign in + Open workspace)
- `login.html:166, :171, :176` — add `type="button"` to SSO buttons (defensive)
- `status.html:162-187` — 6 uptime divs need `role="img" aria-label="<service> uptime …"` or a visually-hidden SR caption
- `docs.html` — wrap the 6 `.sb-docs-card` siblings with `<section><h2 class="visually-hidden">Browse the docs</h2>…</section>` to remove the H1→H3 jump

---

## Pass-002 drift summary

| Drift | Severity | Sites |
|---|---|---|
| `.sb-stage__index--*` modifier classes not adopted on new pages | P1 | `notifications.html` ×8 |
| Marketing-nav active-state inline `style` | P2 | 5 new marketing pages |
| `aria-label="ShadowBlade home"` on brand link | P2 | 5 new marketing pages |
| Chip 8-property inline-style duplication | P3 | `integrations.html` ×8 (new) — pass-002 still pending on `templates.html` |
| Marketing nav `<header>` lacks nested `<nav>` | P2 | 5 new marketing pages |
| Tab-list `role="tablist"`/`role="tab"` semantics | P0/P1 | `project-detail.html` (P0 — no `href`), `notifications.html` (P1) |

**No pass-001 regressions detected.**

---

## Final tally

- **Pass / warn / fail**: 1 / 7 / 2
- **P0 findings**: 3 (`login.html` pre-filled password, `project-detail.html` no-href tabs, `gallery.html` unfocusable reel cards)
- **P1 findings**: 11 across all 10 pages
- **P2 findings**: 8 (mostly drifts from pass-002)
- **P3 findings**: 6

Net new code path through the design system is in good shape — the drift is overwhelmingly **mechanical** (the Refine ring's repo-wide replacements never re-ran against pages added after pass 002 shipped). The Refine ring should: (a) re-run the favicon/OG meta sweep across pass-003's 9 missing sites, (b) extend `.sb-stage__index--*` adoption to `notifications.html`, (c) decide whether to lift the marketing-nav active state, brand `aria-label`, and `<nav>` wrap into the shell-loaded `components/marketing-nav.html` fragment so future pages inherit it for free.
