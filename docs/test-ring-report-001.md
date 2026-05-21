# ShadowBlade · Test ring report 001
**Auditor**: Test ring (deterministic, source-only — no browser available)
**Scope**: `frontend/public/{index.html, dashboard.html, components/shell.html, scripts/{shell,charts}.js, styles/{tokens,app}.css}`
**Standards**: WCAG 2.1 AA · keyboard-navigable · responsive ≥ 360px

---

## Summary

| # | Category | Result | Top issue |
|---|---|---|---|
| 1 | Token integrity | **Warn** | 16+ hardcoded hex values in CSS/HTML/JS not sourced from `tokens.css` |
| 2 | Color contrast | **Fail** | `--sb-text-faint` (#5A667F) drops below 3:1 on dark surfaces (8+ call sites) |
| 3 | Keyboard a11y | **Fail (P0)** | Zero `:focus-visible` styles anywhere — entire keyboard nav is invisible |
| 4 | Semantic HTML | **Warn** | `<main>` wraps `<header>` + `<footer>` on landing; H2 skipped on landing |
| 5 | Responsive | **Warn** | Sidebar disappears < 860px with no replacement nav; marketing nav overflows < 720px |
| 6 | Copy review | **Warn** | Hero verb list reads awkwardly; "Watch tour" link goes to app, not video |
| 7 | Performance hygiene | **Pass** | Preconnect + bottom-loaded scripts; one minor opportunity |
| 8 | API contract sync | **Pass** | Shape matches; two fixture fields (`purpose`, `tags`) unused by dashboard |
| 9 | Brand consistency | **Warn** | `#2EE2C4` (off-brand teal) and `#0b3d36` used in gradients; not in tokens |
| 10 | Cross-page consistency | **Pass** | Brand mark + type scale identical between landing + dashboard |

---

## 1 · Token integrity — **Warn**

Hex values used inline that are not exposed as tokens. SVG illustrations get a pass when they need gradient stops, but the same colour repeated in CSS *and* multiple SVGs is a token-shaped need.

| Sev | Location | Current | Recommended fix |
|---|---|---|---|
| P1 | `frontend/public/styles/app.css:23` | `radial-gradient(... #102447 ...)` in `body` background | Add `--sb-grad-aurora-blue: #102447` token, reference here |
| P1 | `frontend/public/styles/app.css:24` | `radial-gradient(... #0b3d36 ...)` in `body` background | Add `--sb-grad-aurora-teal: #0b3d36` token (off-brand otherwise) |
| P1 | `frontend/public/styles/app.css:255` | `linear-gradient(... var(--sb-accent-500), #38bdf8)` on workspace progress | Use `var(--sb-status-running)` (#38bdf8 is already that token) |
| P1 | `frontend/public/styles/app.css:565` | `linear-gradient(... var(--sb-accent-500), #38bdf8)` on `.sb-meter > i` | Same fix — replace with `var(--sb-status-running)` |
| P1 | `frontend/public/styles/app.css:347` | `linear-gradient(180deg, #2ee2c4 0%, var(--sb-accent-500) 100%)` on primary btn | Introduce `--sb-accent-400: #2ee2c4` token, reference here |
| P1 | `frontend/public/styles/app.css:513` | `color: #fbbf24` on `.sb-kpi__delta--down` | Use `var(--sb-status-queued)` — same value, already a token |
| P2 | `frontend/public/styles/app.css:222,755` | `linear-gradient(135deg, #1c3868, #0a1428)` (×2: workspace avatar, project avatar) | Token: `--sb-grad-avatar` or use existing `--sb-navy-700/900` pair |
| P1 | `frontend/public/index.html:59` | `linear-gradient(90deg, #22d3b7 0%, #38bdf8 100%)` for hero title accent | Use `var(--sb-accent-500)` / `var(--sb-status-running)` |
| P2 | `frontend/public/scripts/charts.js:101,130,138` | `'#22D3B7'` hard-coded for line / dot / sparkline strokes | Read from `getComputedStyle(document.documentElement).getPropertyValue('--sb-accent-500')` once, cache |
| P2 | `frontend/public/dashboard.html:182,192,202` | Inline `style="background:rgba(...);color:#a78bfa"` on `.sb-stage__index` | Replace with modifier classes (e.g. `.sb-stage__index--review`) bound to status tokens |
| P3 | `frontend/public/dashboard.html:275-285` | Six inline cover-SVG strings with `#22D3B7`, `#F7F9FC`, `#8590A8` etc. | Extract to `scripts/covers.js`; reference tokens via `currentColor` where possible |
| P3 | `frontend/public/index.html:185,242,267,310` SVG stops | `#22D3B7`, `#38BDF8` repeated 4+ times in inline SVG | Inline SVG must hardcode; acceptable, but extract gradients to a shared `<defs>` block |

---

## 2 · Color contrast — **Fail**

Computed with WCAG 2.1 relative-luminance formula (sRGB → linear → `0.2126R + 0.7152G + 0.0722B`); contrast = `(L_lighter + 0.05) / (L_darker + 0.05)`. Threshold: **4.5:1** for body text, **3:1** for ≥18.66px bold or ≥24px, and **3:1** for UI components / icons.

### Failing pairs

| Sev | Location | Pair | Ratio | Verdict |
|---|---|---|---|---|
| **P0** | `styles/app.css:314` (`.sb-topbar__search kbd`) | `#5A667F` (--sb-text-faint) on rgba(255,255,255,0.06) over #0F1626 over body | **2.79** | Fails 3:1 UI |
| **P0** | `styles/app.css:1038` (`.sb-footer`) | `#5A667F` on body `#060c1a` | **3.39** | Fails 4.5:1 body text |
| **P0** | `styles/app.css:493` (`.sb-kpi__value small`) | `#5A667F` on KPI gradient `~#161e30` | **2.88** | Fails 3:1 even as UI; reads "/ 1,000", "min", "%", "/qtr" — meaningful |
| **P0** | `styles/app.css:238` (`.sb-workspace-card__meta span`) | `#5A667F` on `rgba(11,20,40,0.55)` over sidebar `~#0b1428` | **3.18** | Fails 4.5:1 body text — reads "24 seats · Workspace admin" |
| **P0** | `styles/app.css:671` (`.sb-stage__log`) | `#5A667F` on `rgba(11,18,32,0.5)` over body | **3.32** | Fails 4.5:1 body — affects every stage row + approval row |
| **P1** | `styles/app.css:494` (`.sb-kpi__value small`) | `#5A667F` on KPI bg | 2.88 | Same as above; "/ 1,000" suffix |
| **P1** | `styles/app.css:749` (`.sb-project__meta`) | `#5A667F` on project body bg | **2.92** (vs #161e30) | Fails 3:1 even relaxed |
| **P1** | `styles/app.css:999,1008` (`.sb-queue-row__name span` / `__eta`) | `#5A667F` on body | 3.39 | Fails body 4.5:1 (queue page) |
| **P1** | `styles/app.css:967` (`.sb-asset__meta`) | `#5A667F` on `--sb-surface` #11161f | **3.12** | Fails body 4.5:1 |
| **P1** | `dashboard.html:230` inline `color:var(--sb-text-muted)` is OK (5.19), but `font-size:var(--sb-text-sm)` (12px) — `--sb-text-muted` PASSES at 5.19, leave alone | 5.19 | Pass |

### Recommended remedy

Tighten `--sb-text-faint` from `#5a667f` (luminance 0.118) to something like `#7d88a0` (luminance 0.235) — gives ~5.0:1 on the body background and 4.3:1 on KPI cards (acceptable for muted labels at ≥14px). Alternative: introduce a new token `--sb-text-faint-strong: #8590a8` and remap all the listed call sites; reserve the existing `--sb-text-faint` for ≥18px large text only and document the constraint in `tokens.css`.

### Passing pairs verified (no change)

- Body text `#f7f9fc` on body / surface / KPI: 17–18:1 (AAA)
- `--sb-text-muted` `#8590a8` everywhere: 5.2–6.1:1 (AA)
- Primary btn navy text on accent: 10.3:1 (AAA)
- All status pill colours over both bg and over `rgba(255,255,255,0.05)`: ≥6.9:1 (AA)
- Accent-300 eyebrow on bg: 12.4:1 (AAA)

---

## 3 · Keyboard a11y — **Fail (P0)**

Zero `:focus-visible` or `:focus` rules anywhere in `tokens.css`, `app.css`, or component HTML. Confirmed by `grep -rn focus frontend/public/` — only two hits: a comment in `tokens.css:3` and `shell.js:25` (programmatic `.focus()` call for ⌘K).

Consequence: every interactive element (`.sb-btn`, `.sb-nav__item`, `<input>`, the `.sb-topbar__search` `<label>`, project cards, marketing nav anchors, footer links) is keyboard-traversable but visually un-indicated. Tab user is lost. Hard-fails WCAG 2.4.7 Focus Visible.

Plus: `<button>` reset on `app.css:36-42` strips browser default focus ring with no replacement.

| Sev | Location | Recommended fix |
|---|---|---|
| **P0** | `styles/app.css:36-42` (`button` reset) | Add `:focus-visible { outline: 2px solid var(--sb-accent-500); outline-offset: 2px; border-radius: inherit; }` to a global rule |
| **P0** | `styles/app.css:325` (`.sb-btn`) | Add `.sb-btn:focus-visible { outline: 2px solid var(--sb-accent-500); outline-offset: 2px; }` |
| **P0** | `styles/app.css:159` (`.sb-nav__item`) | `.sb-nav__item:focus-visible { outline: 2px solid var(--sb-accent-500); outline-offset: -2px; }` (inset so it doesn't clip past the sidebar edge) |
| **P0** | `styles/app.css:287` (`.sb-topbar__search`) + `:focus-within` | Add `.sb-topbar__search:focus-within { border-color: var(--sb-accent-500); box-shadow: 0 0 0 3px rgba(34,211,183,0.15); }` and remove `outline:none` on `:301-305` (or rely on `:focus-within` of the parent) |
| **P0** | All `<a>` in marketing nav (`index.html:194-203`) and shell links | Covered by global `:focus-visible` rule |
| **P1** | `styles/app.css:687` (`.sb-project`) | Project card is non-interactive in DOM (no `<a>` wrapper) — once it becomes clickable, ensure focus ring is visible against the dark cover image |

---

## 4 · Semantic HTML — **Warn**

| Sev | Location | Issue | Recommended fix |
|---|---|---|---|
| **P1** | `index.html:177-354` | `<main class="sb-marketing">` wraps both the page `<header>` (L178) and the page `<footer>` (L350). Spec: `<main>` excludes site-wide header/footer/nav | Move `<header>` and `<footer>` to be siblings of `<main>`. `<main>` should wrap `.sb-hero` + `.sb-logos` + `.sb-features` only |
| **P1** | `index.html:178` | Marketing-nav links are inside `<header>` but not wrapped in `<nav>` | Add `<nav aria-label="Primary">` around the 5 anchor links (or all elements after `.sb-brand`) |
| **P1** | `index.html:209` → `:331,338,345` | `<h1>` then `<h3>` — `<h2>` skipped | Change feature headings to `<h2>` (or add a section heading like `<h2>Why ShadowBlade</h2>` above `.sb-features`) |
| **P2** | `index.html:6` `<title>` | `"ShadowBlade · Enterprise AI Video Cloud"` — fine | OK |
| **P2** | `dashboard.html:6` `<title>` | `"Dashboard · ShadowBlade"` — fine | OK |
| **P2** | `dashboard.html:25` | `<input type="search">` has no associated `aria-label` (relies on `<label>` parent wrapping). Some screen-reader / older AT may miss it. The `<label>` parent has `aria-label="Search"`, which overrides label text | Add `aria-label="Search projects, assets, templates"` directly on the `<input>` (placeholder is not a label) |
| **P2** | `dashboard.html:65` | `<section aria-label="Key results">` — has accessible name. Good |  |
| **P2** | `dashboard.html:227` | `<header class="sb-page-head__row">` used as a sub-section heading — fine but the `<h2>` inside has `style=` overrides; would be cleaner as a class | Add `.sb-page-head__h2` class instead of inline style |
| **P2** | `dashboard.html:213` (stage with `📌`) | Emoji used as standalone glyph in `<span class="sb-stage__index">` — screen readers read "pushpin" | Wrap in `<span aria-hidden="true">📌</span><span class="visually-hidden">Pinned</span>` or use an SVG icon |
| **P2** | `dashboard.html:182,192,202` (`SE`, `CP`, `SR` initials) | Visually meaningful initials. Screen reader will spell them out. Acceptable but adding `aria-label="Marcus Lee"` etc. would be friendlier |  |
| **P3** | `components/shell.html:8,16` | `<linearGradient id="sb-mark-grad">` defined inside a fragment that may be loaded after the brand mark in `index.html:184` (id `m-grad`). Two different IDs to avoid clash. Good |  |
| **P3** | `index.html:234` | `<div class="sb-hero__art" aria-hidden="true">` — decorative, hidden from AT. Good |  |
| **P3** | `index.html:201-202` etc. | Several inline `<svg>` lack `aria-hidden="true"` but they're inside a labelled button/link — screen reader skips them. Acceptable |  |

---

## 5 · Responsive — **Warn**

Breakpoints found:

- `app.css:1062` — `max-width: 1100px` → KPI grid 4→2 col, two-col grids collapse
- `app.css:1067` — `max-width: 860px` → shell collapses to 1 col, sidebar `display:none`, padding tightens
- `index.html:169` — `max-width: 920px` → hero single column, logos 6→3 col

| Sev | Location | Issue | Recommended fix |
|---|---|---|---|
| **P0** | `app.css:1067-1072` | At ≤860px the sidebar is hidden entirely with no hamburger / drawer replacement. Dashboard nav becomes inaccessible. iPhone-class viewports cannot navigate | Add a top-bar burger button that toggles `aria-expanded` on a drawer version of the sidebar; or keep sidebar as a slide-in `<dialog>` |
| **P1** | `index.html:24-32` (`.sb-marketing__nav`) | Padding `0 var(--sb-space-12)` (48px) at 360px viewport leaves 264px for 8 inline children (brand + spacer + 5 links + 2 CTAs). Will overflow horizontally. No `flex-wrap` on the container | Add `flex-wrap: wrap; row-gap: var(--sb-space-3)` and inside the `@media (max-width: 920px)` block, hide the 5 plain links and collapse to brand + Sign in + Open workspace |
| **P1** | `index.html:71-78` (`.sb-hero__proof`) | 3-col grid never collapses. At 360px: 360 − 16px gap × 2 − padding = ~80px per cell. The `<b>` is `--sb-text-2xl` (26px) — "$168k" fits, "4.8 min" wraps awkwardly | Inside the `max-width: 920px` block, set `grid-template-columns: 1fr; gap: var(--sb-space-4);` or use `repeat(auto-fit, minmax(140px, 1fr))` |
| **P1** | `dashboard.html:227-238` (project filter row) | 5 ghost buttons + the heading + meta line, all flex-row. At 480px they will wrap unpredictably onto multiple lines on top of the heading | Wrap filters in a `overflow-x:auto` horizontal scroller; or stack heading + filters at ≤720px |
| **P1** | `dashboard.html:65` (`.sb-kpi-grid`) | At ≤1100 collapses to 2 col; at ≤480 still 2 col — sparkline labels and `▲ 12.4% vs last month` will wrap clumsily | Add `@media (max-width: 480px) { .sb-kpi-grid { grid-template-columns: 1fr; } }` |
| **P2** | `app.css:976` (`.sb-queue-row`) | Hard-coded `grid-template-columns: 1fr auto auto 80px` with no mobile fallback — render queue page will overflow at small widths | Within an existing breakpoint, collapse `grid-template-columns: 1fr; gap: var(--sb-space-2)` |
| **P2** | `app.css:799` (`.sb-scenes`) | `grid-auto-columns: 160px` with `overflow-x: auto` is intentional horizontal scroll — fine, but on touch the scrollbar visibility is poor. Add `scroll-snap-type: x mandatory` for a nicer UX | Optional |
| **P2** | `dashboard.html:42` `<main class="sb-content">` padding | `app.css:89` uses `padding: var(--sb-space-8) var(--sb-space-10)` (32/40px). At 360px that eats 80px of width. At ≤860px reduced to `var(--sb-space-5)` (20px) — good already | OK |
| **P3** | `index.html:50-55` `.sb-hero__copy h1` | `clamp(40px, 5vw, 64px)` — at 360px viewport: 5vw=18px → 40px is the floor. Fine | OK |

---

## 6 · Copy review — **Warn**

| Sev | Location | Current | Issue | Recommended fix |
|---|---|---|---|---|
| **P1** | `index.html:213` | "the studio scripts, voices, edits, captions, and renders the cut" | "voices" as verb is awkward; parallelism breaks with "voiceovers" being a common noun in this domain | Rewrite: "the studio writes the script, records the voice, edits, captions, and renders the cut" |
| **P1** | `index.html:221-224` | `<a href="studio.html">Watch a 90-second tour</a>` | Link text promises a video; target is the Studio app. Misleading | Either change target to `#demo` (anchor + open modal) or change copy to "Open the Studio" |
| **P2** | `index.html:212` | "ShadowBlade is the AI pipeline marketing, training, and product teams run their video factory on." | Sentence is grammatically valid but reads as run-on. "Run their video factory on" is the verb phrase | Tighten: "ShadowBlade is the AI pipeline that marketing, training, and product teams run their video factory on." (add `that`); or break: "ShadowBlade is the AI pipeline behind enterprise video factories. Marketing, training, and product teams use it to ship every cut." |
| **P2** | `index.html:319` | "Trusted by enterprise teams at" | OK | Optional: "Used by enterprise teams at" reads less prescriptive |
| **P2** | `dashboard.html:50` | "6 cuts shipped this week. 2 running now. The pipeline is on schedule for the Tuesday product launch." | "Tuesday" is hardcoded; will look wrong on Wednesday. Once dynamic, fine | Mark this for the Refine ring to wire to backend |
| **P2** | `dashboard.html:111` | "In flight · pipeline run" | "In flight" is good aviation metaphor but capitalisation inconsistent with other titles ("Approvals waiting on you" — sentence case). Title-case once | "In flight · Pipeline run" |
| **P3** | `dashboard.html:216` | "2 cuts use #20D2B5 — should be #22D3B7. Auto-fix available." | Great copy. Maybe surface as `<code>` for the hex values | Wrap each hex in `<code style="font-family:var(--sb-font-mono)">…</code>` |
| **P3** | `index.html:332` | "Brand-locked output" → "Every cut is rendered against your brand kit — colour, type, voice, intro, outro, legal — so nothing off-guideline ever reaches review." | "off-guideline" reads ESL-translated; "off-brand" is the more natural English. "colour" is BrE while elsewhere "captions" (universal) — pick one variant for the doc | Either "off-brand" or "out-of-spec"; standardise on US (color) or UK (colour) site-wide |
| **P3** | `index.html:339` | "ships in the time they used to take to brief" | Cute but parses slow. Trim | "ships a first cut in the time it used to take to write the brief" |
| **P3** | `index.html:352` | "Status · all systems normal · v0.1" | "normal" is fine; some teams prefer "operational" | Optional |

---

## 7 · Performance hygiene — **Pass**

- Webfont preconnect to `fonts.googleapis.com` and `fonts.gstatic.com` is present in both pages (`index.html:11-12`, `dashboard.html:7-8`). `&display=swap` query param present.
- Scripts (`shell.js`, `charts.js`) are placed at end of `<body>` and are non-blocking by position; no `defer`/`async` attribute but order-dependence is required (`shell.js` must hydrate the sidebar) so leaving as-is is acceptable.
- Inline SVGs are reasonably small (largest is the hero art at ~80 lines; gzipped well under 4KB).
- No render-blocking external scripts.

| Sev | Location | Observation | Recommended fix (optional) |
|---|---|---|---|
| **P2** | `index.html:13-16`, `dashboard.html:9` | Google Fonts CSS is render-blocking | Add `media="print" onload="this.media='all'"` and a `<noscript>` fallback, or self-host the .woff2 in `frontend/public/fonts/` |
| **P3** | `app.css` | ~580 lines (60%) of CSS define classes (`.sb-scenes`, `.sb-scene`, `.sb-timeline`, `.sb-asset-grid`, `.sb-queue-row`, `.sb-swatch`) that the two shipped pages do not use | Acceptable while pages 3–8 are in flight; once routes stabilise, split into per-route CSS or use `postcss-discard-unused` |
| **P3** | `dashboard.html:273-286` | Six inline cover-SVG strings (~1.5KB total) live in a `<script>` block, parsed even when not all are used (each page renders 6) | Move to a fetched JSON file once project count >12, or push to backend `cover_svg` field |
| **P3** | `scripts/charts.js:21-27` | `<defs>` injected for every chart, even if multiple charts on the same page share the same gradient ids — id collision risk | Inject `<defs>` once at the top of `<body>` from `DOMContentLoaded`, drop from `inject()` |

---

## 8 · API contract sync — **Pass**

`backend/app/services/fixtures.py::projects_fixture` returns each item with:
`id, name, purpose, status, progress, aspect_ratio, duration_seconds, owner, updated_at, cover, tags`

`frontend/public/dashboard.html:288-304` (`loadProjects` fallback + render in `:320-334`) consumes:
`id, name, status, progress, aspect_ratio, duration_seconds, owner, updated_at, cover`

| Sev | Location | Observation | Recommended fix |
|---|---|---|---|
| Pass | All consumed keys match exactly | — | — |
| **P2** | `dashboard.html:322-334` | Fixture fields `purpose` and `tags` are returned by the API but unused in the UI. Either render them (chip row?) or filter to a slim DTO on the backend | Add a `tags` chip row to `.sb-project__body`, e.g. `<div class="sb-project__tags">…</div>` |
| **P2** | `dashboard.html:300` | `fetch('/api/v1/projects')` is good. Falls back silently to mock data on any error — fine for v0.1, but log to a telemetry endpoint when live | Add `console.warn` so the Refine ring can detect contract drift |
| **P2** | `dashboard.html:328` | `Math.round(p.progress * 100)` assumes `progress ∈ [0,1]`. The fixture confirms this (0.0–1.0). Add a `Math.max(0, Math.min(1, p.progress))` guard | Defensive, P3 |
| **P2** | `dashboard.html:331` | `node.querySelector('svg').innerHTML = COVERS[p.cover] || ''` — unknown `cover` slug renders blank. Backend may add new slugs (e.g. "gdpr-v2") before frontend updates | Define a `default` placeholder SVG; or send the SVG markup from the API (`cover_svg` field) |
| **P2** | `dashboard.html:289-298` | Fallback fixture in JS duplicates the backend fixture. Diverges over time. Two sources of truth | Long-term: remove client fallback; treat `/api/v1/projects` as required, show a "loading…" skeleton |

---

## 9 · Brand consistency — **Warn**

| Sev | Location | Current | Issue | Recommended fix |
|---|---|---|---|---|
| **P1** | `app.css:347` (`.sb-btn--primary`) | `linear-gradient(180deg, #2ee2c4 0%, var(--sb-accent-500) 100%)` | `#2EE2C4` is a slightly lighter teal — not in tokens. Brand voice ("on brand, on guideline") is undermined by uncoded accent variants in CSS | Add `--sb-accent-400: #2ee2c4` to tokens; use the variable |
| **P1** | `app.css:24` | `radial-gradient(circle at 92% 110%, #0b3d36 0%, transparent 60%)` | `#0B3D36` is a deep teal not in tokens; would benefit from a `--sb-accent-900` mapping (existing token `--sb-accent-900: #064f44` is a different shade) | Either remap to `var(--sb-accent-900)` (similar luminance) or add `--sb-accent-950: #0b3d36` |
| **P2** | `dashboard.html:216` | UI copy mentions `#22D3B7` accent verbatim — locks the copy to the hex | Reference `var(--sb-accent-500)` via JS templating once the brand-kit page is wired |
| **P2** | `app.css:347, app.css:255, app.css:565` | `#38BDF8` (already the `--sb-status-running` token) used directly. Semantically: a *status* colour leaking into a *gradient* on a *primary action* button (L347, via the gradient stops) and on a *meter*. Mixing status-blue with action-green dilutes the action signal | Either accept the brand convention "actions glide green→blue" (document in `tokens.css` comment) or restrict status colours to pills/dots only |
| **P3** | `index.html:241-244, components/shell.html:8-10, scripts/charts.js:24-26` | Same gradient stops `#22D3B7 → #38BDF8` repeated in 4+ inline SVGs and one CSS gradient. Single visual identity, four places to edit | Acceptable for now; if more uses appear, generate a static `sprite.svg` with shared `<defs>` |
| **P3** | `index.html:209` `<span>` inside h1 | Uses `linear-gradient(90deg, #22d3b7 0%, #38bdf8 100%)` for the headline accent — beautiful but the text-clip technique disables OS-level high-contrast modes and `forced-colors` media. Falls back to `transparent` | Add `@media (forced-colors: active) { .sb-hero__copy h1 span { color: CanvasText; background: none; -webkit-background-clip: initial; } }` |

---

## 10 · Cross-page consistency — **Pass**

| Sev | Location | Observation | Recommended fix |
|---|---|---|---|
| Pass | `index.html:179-191` vs `components/shell.html:3-19` | Brand mark + name structure identical (gradient logo + "ShadowBlade / Video Cloud" lockup). Visual parity. Good |  |
| Pass | Type scale (`--sb-text-*`) is consistent (both pages import `app.css`/`tokens.css`) | OK |  |
| **P2** | `index.html:179` `<a class="sb-brand" href="index.html">` vs `components/shell.html:3` `<div class="sb-brand">` | Marketing nav: brand is a clickable link to landing. Shell sidebar: brand is a `<div>` (not linked). Inconsistent affordance | Make sidebar brand an `<a href="dashboard.html">` (or `href="/"`) |
| **P2** | Marketing nav uses `padding: var(--sb-space-5) var(--sb-space-12)`; topbar uses `padding: 0 var(--sb-space-10)` | 48 vs 40px horizontal — barely perceptible but creates a 8px misalignment between landing-page brand x-position and dashboard sidebar-edge x-position. Acceptable, but a Refine-ring shared shell would unify | Defer; not visible at typical viewport |
| **P3** | Landing footer (`index.html:351-352`) uses `<span>` text only; dashboard footer (`dashboard.html:246-247`) uses `<span>` text only. Same style class `.sb-footer`. Consistent | OK |  |

---

## Refine ring queue

Ordered by severity (P0 first). Each entry is a single proposed Edit. Old strings are unique within the target file as verified.

### 1. **P0** · Add global `:focus-visible` token-based focus ring → `styles/app.css`

```diff
- button {
-   font: inherit;
-   color: inherit;
-   border: none;
-   background: none;
-   cursor: pointer;
- }
+ button {
+   font: inherit;
+   color: inherit;
+   border: none;
+   background: none;
+   cursor: pointer;
+ }
+
+ :focus-visible {
+   outline: 2px solid var(--sb-accent-500);
+   outline-offset: 2px;
+   border-radius: inherit;
+ }
+ .sb-nav__item:focus-visible {
+   outline-offset: -2px;
+ }
+ .sb-topbar__search:focus-within {
+   border-color: var(--sb-accent-500);
+   box-shadow: 0 0 0 3px rgba(34, 211, 183, 0.18);
+ }
+ .sb-topbar__search input:focus-visible {
+   outline: none;
+ }
```

### 2. **P0** · Add a mobile nav drawer trigger before sidebar disappears → `styles/app.css`

```diff
- @media (max-width: 860px) {
-   .sb-shell { grid-template-columns: 1fr; }
-   .sb-sidebar { display: none; }
-   .sb-content { padding: var(--sb-space-5); }
-   .sb-topbar { padding: 0 var(--sb-space-5); }
- }
+ @media (max-width: 860px) {
+   .sb-shell { grid-template-columns: 1fr; }
+   .sb-sidebar {
+     position: fixed;
+     inset: 0 auto 0 0;
+     width: var(--sb-sidebar-w);
+     transform: translateX(-100%);
+     transition: transform var(--sb-dur) var(--sb-ease-out);
+     z-index: 30;
+   }
+   .sb-sidebar[data-open="true"] { transform: translateX(0); }
+   .sb-content { padding: var(--sb-space-5); }
+   .sb-topbar { padding: 0 var(--sb-space-5); }
+ }
+ @media (max-width: 480px) {
+   .sb-kpi-grid { grid-template-columns: 1fr; }
+ }
```

(Follow-up: add a `<button class="sb-btn sb-btn--icon" aria-controls="sb-sidebar" aria-expanded="false">` to `dashboard.html:18` topbar and wire in `shell.js`.)

### 3. **P0** · Strengthen `--sb-text-faint` for AA contrast → `styles/tokens.css`

```diff
-   --sb-text-faint:   var(--sb-graphite-400);
+   --sb-text-faint:   #7d88a0; /* tightened from graphite-400 #5a667f for ≥4.5:1 on body bg */
```

### 4. **P0** · Use `--sb-text-muted` (not faint) for KPI value suffixes → `styles/app.css`

```diff
- .sb-kpi__value small {
-   font-size: var(--sb-text-md);
-   color: var(--sb-text-faint);
-   margin-left: 6px;
-   font-weight: 500;
- }
+ .sb-kpi__value small {
+   font-size: var(--sb-text-md);
+   color: var(--sb-text-muted);
+   margin-left: 6px;
+   font-weight: 500;
+ }
```

### 5. **P0** · Tighten `kbd` contrast in topbar search → `styles/app.css`

```diff
- .sb-topbar__search kbd {
-   font-family: var(--sb-font-mono);
-   font-size: 10px;
-   padding: 2px 6px;
-   border-radius: 4px;
-   background: rgba(255, 255, 255, 0.06);
-   color: var(--sb-text-faint);
- }
+ .sb-topbar__search kbd {
+   font-family: var(--sb-font-mono);
+   font-size: 10px;
+   padding: 2px 6px;
+   border-radius: 4px;
+   background: rgba(255, 255, 255, 0.10);
+   color: var(--sb-text-muted);
+ }
```

### 6. **P1** · Repair `<main>` landmark + add `<nav>` on landing → `index.html`

```diff
-   <body>
-     <main class="sb-marketing">
-       <header class="sb-marketing__nav">
+   <body>
+     <div class="sb-marketing">
+       <header class="sb-marketing__nav">
```

```diff
-         <a class="sb-brand" href="index.html">
+         <a class="sb-brand" href="index.html" aria-label="ShadowBlade home">
```

```diff
-         <span class="spacer"></span>
-         <a class="link" href="#">Product</a>
-         <a class="link" href="#">Templates</a>
-         <a class="link" href="#">Customers</a>
-         <a class="link" href="#">Pricing</a>
-         <a class="link" href="#">Docs</a>
-         <a class="sb-btn sb-btn--ghost" href="dashboard.html">Sign in</a>
-         <a class="sb-btn sb-btn--primary" href="dashboard.html">
+         <span class="spacer"></span>
+         <nav class="sb-marketing__links" aria-label="Primary">
+           <a class="link" href="#">Product</a>
+           <a class="link" href="#">Templates</a>
+           <a class="link" href="#">Customers</a>
+           <a class="link" href="#">Pricing</a>
+           <a class="link" href="#">Docs</a>
+         </nav>
+         <a class="sb-btn sb-btn--ghost" href="dashboard.html">Sign in</a>
+         <a class="sb-btn sb-btn--primary" href="dashboard.html">
```

```diff
-       </header>
-
-       <section class="sb-hero">
+       </header>
+
+       <main>
+       <section class="sb-hero">
```

```diff
-       <footer class="sb-footer">
-         <span>© 2026 ShadowBlade Labs</span>
-         <span>Status · all systems normal · v0.1</span>
-       </footer>
-     </main>
+       </main>
+
+       <footer class="sb-footer">
+         <span>© 2026 ShadowBlade Labs</span>
+         <span>Status · all systems normal · v0.1</span>
+       </footer>
+     </div>
```

### 7. **P1** · H2 inserted in feature section so heading order is monotonic → `index.html`

```diff
-       <section class="sb-features">
-         <article class="sb-feature">
+       <section class="sb-features" aria-labelledby="why-sb-heading">
+         <h2 id="why-sb-heading" class="visually-hidden">Why ShadowBlade</h2>
+         <article class="sb-feature">
```

### 8. **P1** · Rewrite hero verb list + fix misleading tour link → `index.html`

```diff
-           <p class="sb-hero__lead">
-             ShadowBlade is the AI pipeline marketing, training, and product teams
-             run their video factory on. Write a brief, choose a template, and
-             the studio scripts, voices, edits, captions, and renders the cut —
-             on brand, on guideline, on schedule.
-           </p>
+           <p class="sb-hero__lead">
+             ShadowBlade is the AI pipeline behind enterprise video factories.
+             Marketing, training, and product teams write a brief, pick a template,
+             and the studio writes the script, records the voice, edits, captions,
+             and renders the cut — on brand, on schedule.
+           </p>
```

```diff
-             <a class="sb-btn sb-btn--ghost" href="studio.html">
-               <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="6 4 20 12 6 20 6 4"/></svg>
-               Watch a 90-second tour
-             </a>
+             <a class="sb-btn sb-btn--ghost" href="studio.html">
+               <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="6 4 20 12 6 20 6 4"/></svg>
+               Open the Studio
+             </a>
```

### 9. **P1** · Add `--sb-accent-400` token, use in primary button → `styles/tokens.css`

```diff
-   --sb-accent-300: #6ee2c5;
-   --sb-accent-500: #22d3b7;     /* primary cyan-green action */
+   --sb-accent-300: #6ee2c5;
+   --sb-accent-400: #2ee2c4;
+   --sb-accent-500: #22d3b7;     /* primary cyan-green action */
```

Then in `styles/app.css`:

```diff
- .sb-btn--primary {
-   background: linear-gradient(180deg, #2ee2c4 0%, var(--sb-accent-500) 100%);
+ .sb-btn--primary {
+   background: linear-gradient(180deg, var(--sb-accent-400) 0%, var(--sb-accent-500) 100%);
```

### 10. **P1** · Replace hardcoded `#38bdf8` and `#fbbf24` with tokens → `styles/app.css`

```diff
- .sb-workspace-card__progress-bar > i {
-   display: block;
-   height: 100%;
-   background: linear-gradient(90deg, var(--sb-accent-500), #38bdf8);
-   border-radius: 99px;
- }
+ .sb-workspace-card__progress-bar > i {
+   display: block;
+   height: 100%;
+   background: linear-gradient(90deg, var(--sb-accent-500), var(--sb-status-running));
+   border-radius: 99px;
+ }
```

```diff
- .sb-meter > i {
-   display: block;
-   height: 100%;
-   border-radius: 99px;
-   background: linear-gradient(90deg, var(--sb-accent-500), #38bdf8);
-   transition: width var(--sb-dur-slow) var(--sb-ease-out);
- }
+ .sb-meter > i {
+   display: block;
+   height: 100%;
+   border-radius: 99px;
+   background: linear-gradient(90deg, var(--sb-accent-500), var(--sb-status-running));
+   transition: width var(--sb-dur-slow) var(--sb-ease-out);
+ }
```

```diff
- .sb-kpi__delta--down {
-   color: #fbbf24;
-   background: rgba(251, 191, 36, 0.12);
- }
+ .sb-kpi__delta--down {
+   color: var(--sb-status-queued);
+   background: rgba(251, 191, 36, 0.12);
+ }
```

### 11. **P1** · Marketing nav + hero proof responsive collapse → `index.html`

```diff
-       @media (max-width: 920px) {
-         .sb-hero { grid-template-columns: 1fr; padding: var(--sb-space-8); }
-         .sb-features { grid-template-columns: 1fr; padding: 0 var(--sb-space-8) var(--sb-space-12); }
-         .sb-logos__row { grid-template-columns: repeat(3, 1fr); }
-       }
+       @media (max-width: 920px) {
+         .sb-marketing__nav { flex-wrap: wrap; row-gap: var(--sb-space-3); padding: var(--sb-space-4) var(--sb-space-6); }
+         .sb-marketing__links { display: none; }
+         .sb-hero { grid-template-columns: 1fr; padding: var(--sb-space-8); gap: var(--sb-space-8); }
+         .sb-hero__proof { grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); }
+         .sb-features { grid-template-columns: 1fr; padding: 0 var(--sb-space-8) var(--sb-space-12); }
+         .sb-logos__row { grid-template-columns: repeat(3, 1fr); }
+       }
```

### 12. **P2** · Add `aria-label` to search input + fix sidebar brand link → `dashboard.html` & `components/shell.html`

```diff
-             <input type="search" placeholder="Search projects, assets, templates…" />
+             <input type="search" aria-label="Search projects, assets, templates" placeholder="Search projects, assets, templates…" />
```

```diff
-   <div class="sb-brand">
-     <div class="sb-brand__mark" aria-hidden="true">
+   <a class="sb-brand" href="dashboard.html" aria-label="ShadowBlade home">
+     <span class="sb-brand__mark" aria-hidden="true">
```

(Plus matching close-tag swap: `</div>` → `</span></a>` at the end of the brand block; the Refine ring should verify.)

### 13. **P2** · Wrap the pushpin emoji for screen readers → `dashboard.html`

```diff
-                 <div class="sb-stage">
-                   <span class="sb-stage__index">📌</span>
-                   <div class="sb-stage__body">
-                     <div class="sb-stage__title">Brand guideline drift</div>
+                 <div class="sb-stage">
+                   <span class="sb-stage__index" aria-hidden="true">📌</span>
+                   <div class="sb-stage__body">
+                     <div class="sb-stage__title"><span class="visually-hidden">Pinned: </span>Brand guideline drift</div>
```

### 14. **P2** · Standardise "off-guideline" → "off-brand" copy → `index.html`

```diff
-           <p>Every cut is rendered against your brand kit — colour, type, voice, intro, outro, legal — so nothing off-guideline ever reaches review.</p>
+           <p>Every cut is rendered against your brand kit — color, type, voice, intro, outro, legal — so nothing off-brand ever reaches review.</p>
```

### 15. **P2** · `forced-colors` fallback on the gradient-clipped headline → `index.html`

```diff
-       .sb-hero__copy h1 span {
-         background: linear-gradient(90deg, #22d3b7 0%, #38bdf8 100%);
-         -webkit-background-clip: text;
-         background-clip: text;
-         color: transparent;
-       }
+       .sb-hero__copy h1 span {
+         background: linear-gradient(90deg, var(--sb-accent-500) 0%, var(--sb-status-running) 100%);
+         -webkit-background-clip: text;
+         background-clip: text;
+         color: transparent;
+       }
+       @media (forced-colors: active) {
+         .sb-hero__copy h1 span {
+           color: CanvasText;
+           background: none;
+           -webkit-background-clip: initial;
+           background-clip: initial;
+         }
+       }
```

### 16. **P2** · Project-card render — defensive progress clamp + render `tags` → `dashboard.html`

```diff
-           node.querySelector('.sb-meter i').style.width = `${Math.round(p.progress * 100)}%`;
+           const pct = Math.max(0, Math.min(1, p.progress ?? 0));
+           node.querySelector('.sb-meter i').style.width = `${Math.round(pct * 100)}%`;
```

(Follow-up: surface `p.tags` as a chip row in the project card body; needs a Design ring pass first.)

### 17. **P3** · Lift `#22D3B7` accent in charts/sparklines from a CSS variable → `scripts/charts.js`

```diff
- (function () {
+ (function () {
+   const ACCENT = getComputedStyle(document.documentElement)
+     .getPropertyValue('--sb-accent-500').trim() || '#22D3B7';
```

Then replace the three literal `'#22D3B7'` strings at `:101, :130, :138` with `ACCENT`.

---

## Notes for the Design ring

Several "Warn" items are scaffolding for unshipped pages (queue, asset grid, scenes, timeline) — re-audit when those routes ship. Cover-SVG strings in `dashboard.html:273-286` will not scale past 12 projects (move to backend `cover_svg`). The `<main>` landmark issue on landing scores poorly on Lighthouse — high ROI for the next Refine pass.
