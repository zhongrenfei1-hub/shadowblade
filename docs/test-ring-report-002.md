# ShadowBlade · Test ring report 002
**Auditor**: Test ring (deterministic, source-only — no browser available)
**Scope**: `frontend/public/{14 in-scope HTML pages, components/shell.html, scripts/{shell,charts}.js, styles/{tokens,app}.css}` + `showcase/`
**Standards**: WCAG 2.1 AA · keyboard-navigable · responsive ≥ 360px
**Coverage delta vs pass 001**: +12 new pages audited (studio, projects, templates, assets, render-queue, analytics, brand-kit, team, settings, new-video, job-detail, pricing) plus 3 out-of-spec pages discovered (login, notifications, customer-story).

---

## Summary

| # | Category | Result | Top issue |
|---|---|---|---|
| 1 | Regression check (pass 001) | **Pass (with one drift)** | `charts.js` reads `--sb-accent-500` into `ACCENT` const but never uses it — three literal `'#22D3B7'` strings still on `:108, :137, :145` |
| 2 | New-page coverage (token integrity) | **Warn** | `studio.html:86` still hard-codes `#38BDF8` instead of `var(--sb-status-running)`; `analytics.html:19` and 6 inline-style hex strings in `dashboard.html`, `studio.html`, `analytics.html`, `new-video.html`, `job-detail.html`, `team.html` |
| 3 | Showcase wiring | **Fail (P1)** | 10 of 14 in-scope pages have **no** `<meta property="og:image">` / `<meta name="twitter:image">`; 11 of 14 lack the explicit favicon link |
| 4 | Cross-page consistency | **Pass** | Sidebar fragment is identical via loader; topbar height + breadcrumb pattern uniform across 12 workspace pages |
| 5 | Contrast on translucent backgrounds | **Pass (with one warn)** | `.sb-priority--low` `#64748b` on `rgba(100,116,139,0.12)` over body = ~3.66:1 — borderline for body, OK for ≥18px bold pill |
| 6 | Form a11y (labels + switch ARIA) | **Fail (P0)** | 4 search inputs miss `aria-label`; 3 of 4 `.sb-toggle` switches on settings page lack `role="switch"` + `aria-checked`; all `<label>` tags in studio / new-video / brand-kit forms use sibling-text pattern with no `for=` |
| 7 | Heading hierarchy | **Warn** | `brand-kit.html:233,242` jumps H1 → H4 (skips H2/H3); `new-video.html` has no `<h1>` at all (uses `.title` div on `:166`) |

---

## 1 · Regression check (pass 001) — **Pass (with one drift)**

All 17 Refine-ring fixes from pass 001 verified present:

| # | Pass-001 item | Status in pass 002 | Evidence |
|---|---|---|---|
| 1 | Global `:focus-visible` ring | **Held** | `styles/app.css:44-58` |
| 2 | Mobile sidebar drawer + `@media (max-width: 480px)` KPI collapse | **Held** | `styles/app.css:1083-1099` |
| 3 | `--sb-text-faint` tightened to `#7d88a0` | **Held** | `styles/tokens.css:58` |
| 4 | `.sb-kpi__value small` uses `--sb-text-muted` | **Held** | `styles/app.css:509` |
| 5 | `kbd` contrast tightened | **Held** | `styles/app.css:324-331` |
| 6 | `<main>` landmark repaired on landing + `<nav aria-label>` | **Held** | `index.html:194-225, 371-377` |
| 7 | `<h2 class="visually-hidden">Why ShadowBlade</h2>` | **Held** | `index.html:346-347` |
| 8 | Hero verb-list rewrite + "Open the Studio" CTA | **Held** | `index.html:230-244` |
| 9 | `--sb-accent-400` token + primary btn uses it | **Held** | `styles/tokens.css:33`; `styles/app.css:363` |
| 10 | Tokens replace `#38bdf8` / `#fbbf24` in CSS | **Held** | `styles/app.css:271, 529, 581` |
| 11 | Marketing nav + hero proof responsive collapse | **Held** | `index.html:183-190` |
| 12 | Search input `aria-label` + sidebar brand is `<a>` | **Held** | `dashboard.html:31`; `components/shell.html:3-19` |
| 13 | Pushpin emoji wrapped for SR | **Held** | `dashboard.html:219-221` |
| 14 | "off-guideline" → "off-brand" / colour → color | **Held** | `index.html:353` |
| 15 | `forced-colors` fallback for clipped headline | **Held** | `index.html:70-77` |
| 16 | Defensive `Math.max/min` clamp on project progress | **Held** | `dashboard.html:334-335` |
| 17 | Lift `'#22D3B7'` from CSS variable in `charts.js` | **Drift (P2)** | `scripts/charts.js:6-11` declares `const ACCENT = …` but the constant is **never used** — `:108`, `:137`, `:145` still pass literal `'#22D3B7'` to `setAttribute('fill', …)` / `setAttribute('stroke', …)` |

### Drift detail · `scripts/charts.js`

```js
// :108  c.setAttribute('fill', '#22D3B7');           // ← should be ACCENT
// :137  line.setAttribute('stroke', '#22D3B7');      // ← should be ACCENT
// :145  dot.setAttribute('fill', '#22D3B7');         // ← should be ACCENT
```

Recommended Edit: `replace_all '#22D3B7'` with `ACCENT` in the three `setAttribute` calls.

---

## 2 · Token integrity on new pages — **Warn**

Style-block and inline-style hex values that should reference an existing token. Inline SVGs that need literal stops for `<linearGradient>` get a pass.

| Sev | Location | Current | Recommended fix |
|---|---|---|---|
| **P1** | `studio.html:86` | `background: linear-gradient(90deg, var(--sb-accent-500), #38BDF8);` on `.sb-transport__bar i` | `var(--sb-status-running)` — same value, already a token |
| **P1** | `analytics.html:19` | `background: linear-gradient(90deg, var(--sb-accent-500), #38BDF8);` on `.sb-distribution__row .meter i` | Same fix — `var(--sb-status-running)` |
| **P1** | `analytics.html:114` | `<span class="sb-pill" style="color:#fbbf24;background:rgba(251,191,36,0.12)">Rejected 29</span>` | Use `var(--sb-status-queued)` |
| **P1** | `analytics.html:191` | `style="background:rgba(251,191,36,0.18);color:#fbbf24"` on warn glyph | `var(--sb-status-queued)` |
| **P1** | `analytics.html:199` | `style="background:rgba(248,113,113,0.18);color:#f87171"` on error glyph | `var(--sb-status-failed)` |
| **P1** | `dashboard.html:188,198,208` | Three inline `style="color:#a78bfa"` / `color:#38BDF8` / `color:#22d3b7` on `.sb-stage__index` initials | Replace with modifier classes `.sb-stage__index--review` / `--running` / `--succeeded` bound to status tokens. (Already deferred from pass 001 P2 item.) |
| **P1** | `new-video.html:235, 243, 251` | Inline `color:#38BDF8`, `color:#a78bfa`, `var(--sb-accent-300)` on three smart-suggestion glyphs | Same modifier-class pattern as above. The third one (`:251`) already uses the token — good |
| **P1** | `job-detail.html:255, 262` | `style="background:rgba(56,189,248,0.18);color:#38BDF8"` and `:262` `color:#a78bfa` on audit-trail avatars | Token: `var(--sb-status-running)` / `var(--sb-status-review)` |
| **P1** | `studio.html:434` | `<div class="sb-workspace-card__avatar" style="…color:#a78bfa">DA</div>` | Same as above — `var(--sb-status-review)` |
| **P1** | `team.html:19-22` | `.sb-role-pill--producer { color: #38BDF8; }`, `--brand { color: #a78bfa; }`, `--reviewer { color: #fbbf24; }` in a `<style>` block | All three resolve to existing tokens — `var(--sb-status-running)`, `var(--sb-status-review)`, `var(--sb-status-queued)` |
| **P1** | `team.html:134-136` | Three inline `style="…color:#a78bfa"` / `color:#fbbf24` / `color:#22D3B7` on member-row avatars | Promote to `.sb-avatar-lg--review/queued/done` classes bound to tokens |
| **P2** | `render-queue.html:69-72` | `.sb-priority--rush/--high/--normal/--low` use literal `#f87171/#fbbf24/#94a3b8/#64748b` | Three of four map to tokens (`--sb-status-failed`, `--sb-status-queued`, `--sb-status-draft`); only `--low #64748b` is new — add `--sb-status-low: #64748b` token or reuse `--sb-graphite-500` (#3a455c is too dark; #64748b is between graphite-500 and -400) |
| **P2** | `templates.html:184-185` | `pill.style.background = b === 'New' ? 'rgba(34,211,183,0.18)' : 'rgba(56,189,248,0.18)'; pill.style.color = … : '#7dd3fc';` — `#7dd3fc` is sky-300, not in tokens | Add `--sb-status-new: #7dd3fc` or reuse `--sb-accent-300` for "New" and `--sb-status-running` lighter variant for "Popular" |
| **P2** | `brand-kit.html:191-198, 259, 265, 271` | Brand-kit page hard-codes hex values inside `style="background:#...;color:#..."` on swatch cards and three logo backgrounds | **Intentional and acceptable** — this page is the *source of truth* for the brand kit. The swatches deliberately display literal hex values to teach colour. **No fix recommended.** |
| **P2** | `notifications.html:143, 195` and other notifications instances | Inline `color:#38BDF8` etc. (page out of scope but inherits the same pattern) | Apply the same modifier-class refactor when notifications is audited |
| **P3** | `styles/app.css:23-24` | `radial-gradient(... #102447 ...)` and `... #0b3d36 ...` in `body` background | Pass-001 P1 token additions still deferred — `--sb-grad-aurora-blue` / `--sb-grad-aurora-teal`. Noted but no UX impact |
| **P3** | `styles/app.css:238, 771` | `linear-gradient(135deg, #1c3868, #0a1428)` on workspace avatar and project meta avatar (×2) | Pass-001 P2 deferred — could be `--sb-grad-avatar` token |

---

## 3 · Showcase wiring — **Fail (P1)**

| Page | favicon | og:title | og:description | og:image | twitter:card | twitter:image | Verdict |
|---|---|---|---|---|---|---|---|
| `index.html` | ✓ `:11` | ✓ `:12` | ✓ `:13` | ✓ `/showcase/hero/hero-cover.svg` `:14` | ✓ `:15` | ✓ `:16` | **Complete** |
| `dashboard.html` | ✓ `:7` | ✓ `:8` | ✓ `:9` | ✓ `/showcase/screens/screen-dashboard.svg` `:10` | ✓ `:11` | ✓ `:12` | **Complete** |
| `pricing.html` | ✓ `:7` | ✗ | ✗ | ✓ `/showcase/brand/og-image.svg` `:8` | ✗ | ✗ | **Partial** — missing og:title, og:description, twitter:card, twitter:image |
| `job-detail.html` | ✓ `:7` | ✗ | ✗ | ✗ | ✗ | ✗ | **Partial** — favicon only |
| `studio.html` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **Missing** — Showcase asset exists at `/showcase/screens/screen-studio.svg` |
| `render-queue.html` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **Missing** — Showcase asset exists at `/showcase/screens/screen-queue.svg` |
| `projects.html` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **Missing** |
| `templates.html` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **Missing** |
| `assets.html` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **Missing** |
| `analytics.html` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **Missing** |
| `brand-kit.html` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **Missing** |
| `team.html` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **Missing** |
| `settings.html` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **Missing** |
| `new-video.html` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **Missing** — modal page; defensible to skip OG but favicon should land |

### Showcase-asset existence audit

All referenced assets exist on disk:

- `/showcase/brand/favicon.svg` ✓
- `/showcase/brand/og-image.svg` ✓
- `/showcase/brand/logo.svg` ✓ (unused by any page)
- `/showcase/brand/logo-mono.svg` ✓ (unused by any page)
- `/showcase/hero/hero-cover.svg` ✓
- `/showcase/screens/screen-dashboard.svg` ✓
- `/showcase/screens/screen-queue.svg` ✓ (no page references it)
- `/showcase/screens/screen-studio.svg` ✓ (no page references it)
- `/showcase/thumbnails/{wearable-hub,bootcamp,copilot,gdpr,helios,series-c}.svg` ✓ (unused — every page builds covers inline in JS instead)
- `/showcase/case-study/helios-hero.svg` + `helios-quote.svg` ✓ (referenced by out-of-scope `customer-story.html`)

**Stranded assets**: 11 of 16 showcase SVGs are not yet referenced by any page. The screens/* assets in particular are exactly the right shape for og:image and should be wired up — see recommended fixes below.

### Recommended fix · per-page block

For each workspace page (`studio, projects, templates, assets, render-queue, analytics, brand-kit, team, settings`) and the deep-dive `job-detail`, add this immediately after `<title>`:

```html
<link rel="icon" type="image/svg+xml" href="/showcase/brand/favicon.svg" />
<meta property="og:title" content="<page title> · ShadowBlade" />
<meta property="og:description" content="<one-line page description>" />
<meta property="og:image" content="/showcase/screens/screen-<route>.svg" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:image" content="/showcase/screens/screen-<route>.svg" />
```

Use `screen-studio.svg` for `studio.html`, `screen-queue.svg` for `render-queue.html` and `job-detail.html`, `screen-dashboard.svg` for the rest. Pass-001 used `og-image.svg` for `pricing.html` — keep that.

---

## 4 · Cross-page consistency — **Pass**

| Check | Result |
|---|---|
| Sidebar fragment loaded identically via `data-shell="sidebar"` slot + `scripts/shell.js` | ✓ All 12 workspace pages (everything except `index, pricing, new-video, job-detail`'s wizard-only chrome) carry the slot; `body[data-route]` attribute matches the `data-route="<route>"` on `.sb-nav__item` in `shell.html` |
| `body[data-route]` values: `dashboard, studio, projects, templates, assets, brand, queue, analytics, team, settings, wizard` | All defined in `shell.html:23,27,31,36,42,46,52,57,63,67` — matches |
| Topbar height pinned to `var(--sb-topbar-h)` via `.sb-shell__main` grid `:99-101` | ✓ Uniform |
| Breadcrumb pattern `<span>Acme</span> [chevron] [...] <b>current</b>` | ✓ Uniform on all 9 workspace pages with breadcrumbs |
| Status pills use the same `.sb-pill--*` palette from `app.css:560-568` | ✓ — and they correctly use status tokens |
| Page-head structure `.sb-eyebrow` + `<h1>` + `.sb-page-head__lead` | ✓ on all 12 workspace pages (verified in §7) |

| Sev | Location | Issue | Recommended fix |
|---|---|---|---|
| P2 | `studio.html:181`, `job-detail.html:101` | Pill placed *outside* the breadcrumb (`<span class="sb-pill" style="margin-left:var(--sb-space-3)">`) — visually fine but inconsistent with the dashboard pattern (where pills live inside `.sb-card__head-actions`) | Optional: introduce a `.sb-topbar__status` slot in the shell or accept the topbar-pill pattern on detail pages |
| P3 | `pricing.html` | Marketing pages use `<a class="sb-brand" href="index.html">` without `aria-label` on `:137`; landing already has `aria-label="ShadowBlade home"` `:196` | Add `aria-label="ShadowBlade home"` to `pricing.html:137` |
| P3 | `pricing.html:147` | `<a class="link" href="pricing.html" style="color:var(--sb-text)">Pricing</a>` uses inline color to denote active state | Introduce `.sb-marketing__nav .link.is-active` and apply class — matches the workspace nav pattern |

---

## 5 · Contrast spot-check on translucent backgrounds — **Pass (with one warn)**

WCAG 2.1 contrast computed against the page body background (`var(--sb-bg)` = `#060c1a`, plus two radial overlays). Translucent fills composite *over* the body, so effective fg/bg pairs are computed after sRGB compositing.

| Sev | Component | Pair | Effective ratio | Verdict |
|---|---|---|---|---|
| Pass | `.sb-stage--running .sb-stage__index` (`app.css:671-674`) — `#38bdf8` on `rgba(56,189,248,0.18)` over `rgba(11,18,32,0.5)` (`.sb-stage`) over body | `#38BDF8` (luminance 0.498) on ~`#0F1D2F` composite | **8.6:1** | AAA |
| Pass | `.sb-stage--succeeded .sb-stage__index` — `var(--sb-accent-300)` on `rgba(34,211,183,0.18)` | `#6EE2C5` on ~`#10231F` composite | **9.4:1** | AAA |
| Pass | `.sb-priority--rush` `#f87171` on `rgba(248,113,113,0.12)` composite | ~**5.8:1** | AA (and the pill is ≥18px bold-effect — 3:1 floor anyway) |
| Pass | `.sb-priority--high` `#fbbf24` on `rgba(251,191,36,0.12)` composite | ~**9.4:1** | AAA |
| Pass | `.sb-priority--normal` `#94a3b8` on `rgba(148,163,184,0.12)` composite | ~**4.7:1** | AA body |
| **Warn (P2)** | `.sb-priority--low` `#64748b` on `rgba(100,116,139,0.12)` composite (`render-queue.html:72`) | ~**3.0–3.3:1** | Fails 4.5:1 body; passes 3:1 UI floor. Reads "LOW" only — acceptable for an uppercase ≥10px bold pill, but tightening to `#7d88a0` (the new `--sb-text-faint`) would land 4.5:1 |
| Pass | `.sb-pill--rendering/--running` `#38bdf8` on `rgba(255,255,255,0.05)` composite | ~**8.6:1** | AAA |
| Pass | `.sb-pill--review` `#a78bfa` on `rgba(255,255,255,0.05)` composite | ~**6.4:1** | AA |
| Pass | `.sb-pill--draft` `#94a3b8` on `rgba(255,255,255,0.05)` composite | ~**4.6:1** | AA |
| Pass | log stream `.lvl-info #38bdf8` on `rgba(6,10,22,0.75)` composite (`job-detail.html:32`) | **~9.0:1** | AAA |
| Pass | `.lvl-ok` `var(--sb-accent-300)` on log bg | ~**10.5:1** | AAA |
| Pass | `.lvl-warn #fbbf24` on log bg | ~**11.0:1** | AAA |
| Pass | `.lvl-err #f87171` on log bg | ~**6.9:1** | AA |
| Pass | Approvals avatars `dashboard.html:188,198,208` — initials on `rgba(...,0.18)` composite over body | All three ≥7:1 (purple, blue, teal letters on dark) | AA+ |

---

## 6 · Form a11y — **Fail (P0)**

### 6.1 · Search input `aria-label` (P0)

4 of 5 workspace topbar `<input type="search">` lack `aria-label`. The parent `<label class="sb-topbar__search">` has no `aria-label` either, so SR users hear nothing meaningful.

| Sev | File | Line | Current | Fix |
|---|---|---|---|---|
| P0 | `projects.html` | 85 | `<input type="search" placeholder="Filter 38 projects…" />` | Add `aria-label="Filter projects"` |
| P0 | `templates.html` | 83 | `<input type="search" placeholder="Search 64 templates…" />` | `aria-label="Search templates"` |
| P0 | `assets.html` | 69 | `<input type="search" placeholder="Search 112 assets · tags, brand, source…" />` | `aria-label="Search assets"` |
| P0 | `team.html` | 79 | `<input type="search" placeholder="Find a teammate, group, or role…" />` | `aria-label="Find teammate"` |
| Pass | `dashboard.html` | 31 | Has `aria-label="Search projects, assets, templates"` | — |

### 6.2 · `<label>` not associated with input (P1)

In `studio.html`, `new-video.html`, and `brand-kit.html`, the `<label>` text lives inside a `.sb-field` div as a *sibling* of the input — not wrapping it and missing the `for=` attribute. Screen readers don't reliably associate.

| Sev | File | Lines | Form fields affected | Fix |
|---|---|---|---|---|
| P1 | `studio.html` | 232-261, 384-410 | 11 inputs/selects/textarea (Goal, Audience, Ratio, Length, Tone, Call to action, Scene script, Visual style, Pace, B-roll, On-screen caption) | Add `id="sb-f-goal"` etc. to each input/select/textarea and `for="sb-f-goal"` to the matching `<label>`. Or wrap: `<label class="sb-field">Goal <select>…</select></label>` |
| P1 | `new-video.html` | 181-216 | 5 inputs/selects/textarea (Picked template, brief, Duration, Aspect ratio, Voice, Call to action) | Same fix |
| P1 | `studio.html` | 444 | The big `<textarea class="sb-field" …placeholder="Reply, or @mention to assign…">` has no `<label>` at all | Wrap in `<label class="visually-hidden">Reply to thread <textarea …></textarea></label>` or add `aria-label="Reply to review thread"` |
| P1 | `settings.html` | 114, 118, 122, 138, 142, 171 | 6 inputs/selects in `.sb-row` rows — visual title is in `<div class="sb-row__title">`, **no `<label>` element at all** | Add `id="…"` to each input/select and `aria-labelledby="<row-title-id>"` on the field, or restructure to wrap with `<label>`. Each row's `.sb-row__title` text should be the label name |
| P1 | `pricing.html` | 158-159 | Toggle buttons "Annual · save 18%" and "Monthly" use `<button class="active">` inside `<div role="tablist">` — `role="tab"` missing, `aria-selected` missing, `aria-controls` missing | Add `role="tab"`, `aria-selected="true|false"`, and an `aria-controls` target. Or convert to a `<fieldset>` with two radio buttons |

### 6.3 · Toggle switch ARIA (P1)

`settings.html` has 4 `.sb-toggle` elements. Only the first has full ARIA.

| Sev | File | Line | Current | Fix |
|---|---|---|---|---|
| Pass | `settings.html` | 126 | `<div class="sb-toggle on" role="switch" aria-checked="true"></div>` | — |
| P1 | `settings.html` | 146 | `<div class="sb-toggle on"></div>` (Auto-render on approval) | Add `role="switch" aria-checked="true"` and a `tabindex="0"` to make it keyboard-focusable; the JS click handler at `:240-242` toggles class but should also flip `aria-checked` |
| P1 | `settings.html` | 150 | `<div class="sb-toggle"></div>` (Watermark drafts) | Add `role="switch" aria-checked="false" tabindex="0"` |
| P1 | `settings.html` | 167 | `<div class="sb-toggle on"></div>` (Require MFA) | Add `role="switch" aria-checked="true" tabindex="0"` |
| P1 | `settings.html` | 240-242 | `t.addEventListener('click', () => t.classList.toggle('on'));` | Also flip `aria-checked`: `t.setAttribute('aria-checked', t.classList.contains('on'))`. Add keydown for Space/Enter |

### 6.4 · Wizard modal a11y (P2)

`new-video.html:161` declares `role="dialog" aria-labelledby="wiz-title"` — good. Missing:

| Sev | File | Line | Issue | Fix |
|---|---|---|---|---|
| P2 | `new-video.html` | 161 | No `aria-modal="true"` | Add `aria-modal="true"` |
| P2 | `new-video.html` | 167 | Close `<button class="close" aria-label="Close">` is good — but body has no focus trap or initial focus management (no JS) | Add `<script>` to trap Tab inside `.sb-wizard` and focus the close button on load (out of scope for this report — flag for Refine) |
| P2 | `new-video.html` | — | No `<h1>` on the page at all (the wizard `.title` `:166` is a div). Acceptable for a modal **if** the wizard is meant to overlay another route; standalone, the page is hard to outline | Add `<h1 class="visually-hidden">Create new video — step 2 of 4</h1>` near the wizard root, or promote `.title` to `<h1>` |

### 6.5 · `<button>` without an accessible name (P3)

Spot checks across new pages:

- `studio.html:316, 319, 322` — three icon-only `<button>` elements have `aria-label="Previous scene/Play/Next scene"` ✓
- `new-video.html:167` — close button has `aria-label="Close"` ✓
- `dashboard.html:35, 38` — notification/help icon buttons have `aria-label` ✓

---

## 7 · Heading hierarchy — **Warn**

| Sev | File | H-tree | Issue | Fix |
|---|---|---|---|---|
| Pass | `index.html` | H1 (line 229), H2 hidden (347), H3 ×3 (352, 359, 366) | Monotonic | — |
| Pass | `dashboard.html` | H1 (53), H2 inline-styled (235) | OK; consider promoting the H2 to use a real class | Pass-001 P2 deferred |
| Pass | `pricing.html` | H1 (155), H2 inline-styled (230) | OK; class would be cleaner | — |
| Pass | `studio.html` | H1 (203); cards use `.sb-card__title` div | OK — cards use div titles, valid pattern | — |
| Pass | `projects.html` | H1 (105) | OK | — |
| Pass | `templates.html` | H1 (100) | OK | — |
| Pass | `assets.html` | H1 (89) | OK | — |
| Pass | `render-queue.html` | H1 (111) | OK | — |
| Pass | `analytics.html` | H1 (70) | OK | — |
| **Warn (P1)** | `brand-kit.html` | H1 (152), then **H4** (233, 242) — skips H2 and H3 | Two `<h4>Do</h4>` / `<h4>Avoid</h4>` jump four levels | Promote to `<h3>` (or `<h2>` if the parent card is itself a section). The card already has a `.sb-card__title` "Voice & tone" — use `<h3>` for Do/Avoid |
| Pass | `team.html` | H1 (96) | OK | — |
| Pass | `settings.html` | H1 (87); side-nav links jump to card IDs | OK | — |
| **Warn (P1)** | `new-video.html` | **No `<h1>`** — only `.title` div (`:166`) and `.sb-step b` (`:173-176`) | Modal-only page; no document outline. Lighthouse / SR users see "Heading-level-one missing" | Promote `<div id="wiz-title" class="title">Create new video</div>` to `<h1 id="wiz-title" class="title">Create new video</h1>` |
| Pass | `job-detail.html` | H1 (123) | OK | — |

---

## Refine ring queue

Ordered by severity. Each entry is a single concrete Edit. Old strings verified unique within their target.

### 1. **P0** · Add `aria-label` to 4 search inputs

```diff
- <input type="search" placeholder="Filter 38 projects…" />
+ <input type="search" aria-label="Filter projects" placeholder="Filter 38 projects…" />
```
→ `projects.html:85`

```diff
- <input type="search" placeholder="Search 64 templates…" />
+ <input type="search" aria-label="Search templates" placeholder="Search 64 templates…" />
```
→ `templates.html:83`

```diff
- <input type="search" placeholder="Search 112 assets · tags, brand, source…" />
+ <input type="search" aria-label="Search assets" placeholder="Search 112 assets · tags, brand, source…" />
```
→ `assets.html:69`

```diff
- <input type="search" placeholder="Find a teammate, group, or role…" />
+ <input type="search" aria-label="Find teammate" placeholder="Find a teammate, group, or role…" />
```
→ `team.html:79`

### 2. **P0** · Add `role="switch" aria-checked tabindex` to 3 settings toggles + fix JS

```diff
- <div class="sb-toggle on"></div>
+ <div class="sb-toggle on" role="switch" aria-checked="true" tabindex="0"></div>
```
→ `settings.html:146` (Auto-render), `:167` (Require MFA)

```diff
- <div class="sb-toggle"></div>
+ <div class="sb-toggle" role="switch" aria-checked="false" tabindex="0"></div>
```
→ `settings.html:150` (Watermark drafts)

```diff
- document.querySelectorAll('.sb-toggle').forEach((t) => {
-   t.addEventListener('click', () => t.classList.toggle('on'));
- });
+ document.querySelectorAll('.sb-toggle').forEach((t) => {
+   const flip = () => {
+     const on = t.classList.toggle('on');
+     t.setAttribute('aria-checked', String(on));
+   };
+   t.addEventListener('click', flip);
+   t.addEventListener('keydown', (e) => {
+     if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); flip(); }
+   });
+ });
```
→ `settings.html:240-242`

### 3. **P0** · Fix charts.js regression — use the `ACCENT` constant

```diff
-       c.setAttribute('fill', '#22D3B7');
+       c.setAttribute('fill', ACCENT);
```
→ `scripts/charts.js:108`

```diff
-     line.setAttribute('stroke', '#22D3B7');
+     line.setAttribute('stroke', ACCENT);
```
→ `scripts/charts.js:137`

```diff
-     dot.setAttribute('fill', '#22D3B7');
+     dot.setAttribute('fill', ACCENT);
```
→ `scripts/charts.js:145`

### 4. **P1** · Wire favicon + og:image + twitter:image into 10 workspace pages

For each of `studio.html`, `projects.html`, `templates.html`, `assets.html`, `render-queue.html`, `analytics.html`, `brand-kit.html`, `team.html`, `settings.html`, `new-video.html`: insert after the `<title>` line:

```diff
  <title>Studio · ShadowBlade</title>
+ <link rel="icon" type="image/svg+xml" href="/showcase/brand/favicon.svg" />
+ <meta property="og:title" content="Studio · ShadowBlade" />
+ <meta property="og:description" content="Edit a scene, see the timeline, review live." />
+ <meta property="og:image" content="/showcase/screens/screen-studio.svg" />
+ <meta name="twitter:card" content="summary_large_image" />
+ <meta name="twitter:image" content="/showcase/screens/screen-studio.svg" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
```

Asset choices:
- `studio.html` → `screen-studio.svg`
- `render-queue.html`, `job-detail.html` → `screen-queue.svg`
- `analytics.html`, `dashboard.html` (already wired) → `screen-dashboard.svg`
- Rest (`projects, templates, assets, brand-kit, team, settings, new-video`) → `screen-dashboard.svg` as a sensible default
- `job-detail.html` already has favicon; add og:title/description/image + twitter:card/image at `:7`

### 5. **P1** · Complete `pricing.html` social meta + job-detail social meta

```diff
  <title>Pricing · ShadowBlade</title>
  <link rel="icon" type="image/svg+xml" href="/showcase/brand/favicon.svg" />
+ <meta property="og:title" content="Pricing · ShadowBlade" />
+ <meta property="og:description" content="Studio, Growth, Scale, Enterprise. Annual contracts, per-render economics." />
  <meta property="og:image" content="/showcase/brand/og-image.svg" />
+ <meta name="twitter:card" content="summary_large_image" />
+ <meta name="twitter:image" content="/showcase/brand/og-image.svg" />
```
→ `pricing.html:6-8`

### 6. **P1** · `brand-kit.html` heading hierarchy — H4 → H3

```diff
-                     <div class="col col--do">
-                       <h4>Do</h4>
+                     <div class="col col--do">
+                       <h3>Do</h3>
```
→ `brand-kit.html:232-233`

```diff
-                     <div class="col col--avoid">
-                       <h4>Avoid</h4>
+                     <div class="col col--avoid">
+                       <h3>Avoid</h3>
```
→ `brand-kit.html:241-242`

Update CSS `.sb-tone .col h4` → `.sb-tone .col h3` (or keep h4 selectors and add h3) at `brand-kit.html:105-107, 115-116`.

### 7. **P1** · `new-video.html` H1 promotion

```diff
-         <div id="wiz-title" class="title">Create new video</div>
+         <h1 id="wiz-title" class="title" style="margin:0">Create new video</h1>
```
→ `new-video.html:166`

Also add `aria-modal="true"`:

```diff
-     <article class="sb-wizard" role="dialog" aria-labelledby="wiz-title">
+     <article class="sb-wizard" role="dialog" aria-modal="true" aria-labelledby="wiz-title">
```
→ `new-video.html:161`

### 8. **P1** · Replace `#38BDF8` with token in studio + analytics

```diff
-       .sb-transport__bar i {
-         position: absolute;
-         inset: 0 60% 0 0;
-         background: linear-gradient(90deg, var(--sb-accent-500), #38BDF8);
+       .sb-transport__bar i {
+         position: absolute;
+         inset: 0 60% 0 0;
+         background: linear-gradient(90deg, var(--sb-accent-500), var(--sb-status-running));
```
→ `studio.html:83-86`

```diff
-       .sb-distribution__row .meter i {
-         display: block; height: 100%; border-radius: 99px;
-         background: linear-gradient(90deg, var(--sb-accent-500), #38BDF8);
+       .sb-distribution__row .meter i {
+         display: block; height: 100%; border-radius: 99px;
+         background: linear-gradient(90deg, var(--sb-accent-500), var(--sb-status-running));
```
→ `analytics.html:17-19`

### 9. **P1** · Introduce `.sb-stage__index--{review|running|succeeded|queued|failed}` modifier classes

Add to `styles/app.css` after `:674`:

```css
.sb-stage__index--review    { background: rgba(167,139,250,0.18); color: var(--sb-status-review); }
.sb-stage__index--running   { background: rgba(56,189,248,0.18);  color: var(--sb-status-running); }
.sb-stage__index--succeeded { background: rgba(34,211,183,0.18);  color: var(--sb-status-done); }
.sb-stage__index--queued    { background: rgba(251,191,36,0.18);  color: var(--sb-status-queued); }
.sb-stage__index--failed    { background: rgba(248,113,113,0.18); color: var(--sb-status-failed); }
```

Then strip inline styles across:
- `dashboard.html:188, 198, 208` (3 instances)
- `analytics.html:191, 199, 207` (3 instances)
- `new-video.html:235, 243, 251` (3 instances)
- `job-detail.html:248, 255, 262` (3 instances)
- `studio.html:434` (1 instance — `.sb-workspace-card__avatar`, may need separate modifier)

Total: 13 inline-style strips, single CSS addition.

### 10. **P1** · `team.html` role-pill colours via tokens

```diff
-       .sb-role-pill--producer { color: #38BDF8;             background: rgba(56,189,248,0.12); }
-       .sb-role-pill--brand    { color: #a78bfa;             background: rgba(167,139,250,0.12); }
-       .sb-role-pill--reviewer { color: #fbbf24;             background: rgba(251,191,36,0.12); }
+       .sb-role-pill--producer { color: var(--sb-status-running); background: rgba(56,189,248,0.12); }
+       .sb-role-pill--brand    { color: var(--sb-status-review);  background: rgba(167,139,250,0.12); }
+       .sb-role-pill--reviewer { color: var(--sb-status-queued);  background: rgba(251,191,36,0.12); }
```
→ `team.html:19-21`

### 11. **P1** · `sb-field` label association in studio + new-video + brand-kit forms

Strategy: add `id` attributes to inputs, `for` to labels. Example for `studio.html:232-238`:

```diff
-                   <div class="sb-field">
-                     <label>Goal</label>
-                     <select>
+                   <div class="sb-field">
+                     <label for="sb-studio-goal">Goal</label>
+                     <select id="sb-studio-goal">
```

Repeat pattern for: studio.html (11 fields at 232-261, 384-410), new-video.html (5 fields at 181-216), settings.html (6 fields at 114, 118, 122, 138, 142, 171 — these need `aria-labelledby="<row-title-id>"` instead since `<label>` is not present).

For `studio.html:444` (orphan textarea):

```diff
-                   <textarea class="sb-field" style="..." placeholder="Reply, or @mention to assign…"></textarea>
+                   <label class="visually-hidden" for="sb-studio-reply">Reply to review thread</label>
+                   <textarea id="sb-studio-reply" class="sb-field" style="..." placeholder="Reply, or @mention to assign…"></textarea>
```

### 12. **P2** · Active marketing-nav state via class, not inline color

```diff
-         <a class="link" href="pricing.html" style="color:var(--sb-text)">Pricing</a>
+         <a class="link is-active" href="pricing.html" aria-current="page">Pricing</a>
```
→ `pricing.html:147`

Add to `pricing.html:21-22` style block:
```css
.sb-marketing__nav a.link.is-active { color: var(--sb-text); }
```

### 13. **P2** · Add `aria-label="ShadowBlade home"` to pricing brand link

```diff
-         <a class="sb-brand" href="index.html">
+         <a class="sb-brand" href="index.html" aria-label="ShadowBlade home">
```
→ `pricing.html:137`

### 14. **P2** · Tighten `.sb-priority--low` to pass AA

```diff
-       .sb-priority--low    { color: #64748b; background: rgba(100,116,139,0.12); }
+       .sb-priority--low    { color: #7d88a0; background: rgba(125,136,160,0.12); }
```
→ `render-queue.html:72`

(Or — preferred — add `--sb-status-low: #7d88a0` to `tokens.css` and reference. The value matches `--sb-text-faint`.)

### 15. **P2** · Tablist semantics on pricing toggle

```diff
-         <div class="sb-pricing-toggle" role="tablist">
-           <button class="active" type="button">Annual · save 18%</button>
-           <button type="button">Monthly</button>
+         <div class="sb-pricing-toggle" role="tablist" aria-label="Billing cycle">
+           <button class="active" type="button" role="tab" aria-selected="true">Annual · save 18%</button>
+           <button type="button" role="tab" aria-selected="false">Monthly</button>
```
→ `pricing.html:157-160`

Also extend the toggle JS at `:255-260` to flip `aria-selected` alongside the class.

### 16. **P3** · Refresh `templates.html` chip styles into class definitions

Inline styles on 8 chip spans (`templates.html:110-118`) duplicate the same 8-property style block. Hoist `.sb-tpl-filter-chip` / `.sb-tpl-filter-chip--active` into the `<style>` block — single source of truth.

### 17. **P3** · Pass-001 P3 deferred items still pending

- `styles/app.css:23-24` — `#102447` and `#0b3d36` should be `--sb-grad-aurora-blue/-teal` tokens
- `styles/app.css:238, 771` — `#1c3868, #0a1428` avatar gradients should be `--sb-grad-avatar`
- `dashboard.html:279-291`, `projects.html:174-180`, `templates.html:151-159` — three pages duplicate cover-SVG dictionaries with overlapping slugs; long-term move to backend `cover_svg` field or a shared `scripts/covers.js`

These do not block the next ring but should land before the Showcase ring's hero/landing screen-shoot.

---

## Pass-001 regressions

**One drift detected.**

- `scripts/charts.js:108, :137, :145` — pass-001 P3 item #17 declared `const ACCENT = …` on `:6-11`, but the three literal `'#22D3B7'` strings in `setAttribute('fill'|'stroke', …)` calls were never swapped to use the constant. Single-line fix per call site, see Refine queue item #3 above.

Everything else from the 17-item pass-001 Refine queue verifies intact.

---

## Out-of-scope pages discovered

The brief lists 13 in-scope pages, plus `customer-story.html`, `login.html`, and `notifications.html` exist on disk and are not covered above. Quick triage:

- `customer-story.html` — has favicon + full og/twitter wiring to `/showcase/case-study/helios-hero.svg` ✓ . Recommend including in pass 003 audit.
- `login.html` — has favicon, no og/twitter. Form fields likely need the same label-association audit as `new-video.html`.
- `notifications.html` — has favicon, no og/twitter. Carries the same inline-`color:#…` pattern as dashboard/job-detail (`:143, :195` already grep-confirmed). Should adopt the `.sb-stage__index--*` modifier classes from Refine queue item #9.

Flag these for the Design ring (confirm they are intentional pages) and add to pass-003 scope.
