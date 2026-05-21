# ShadowBlade · Showcase asset index

Every asset in this folder is hand-authored SVG (≤ 50 KB) using the Design ring's shipped tokens — deep navy `#0F2A4A`, graphite `#11161F`, mist `#F7F9FC`, cyan-green accent `#22D3B7` with `#38BDF8` secondary. Type stack is Inter Display / Inter / JetBrains Mono. No raster, no remote fonts, no emojis.

The table below is the canonical map: where each asset slots into the product, and the user-action + vibe-aesthetic each visual is performing.

## Brand kit

| Asset | Path | Placement | User action | Vibe / aesthetic |
| --- | --- | --- | --- | --- |
| Primary logo | `brand/logo.svg` | Marketing site nav, footer, partner decks, signed PDFs | Recognize ShadowBlade in two seconds, trust the badge | Gradient blade in a navy shield, Inter Display wordmark — confident, instrument-grade |
| Mono logo | `brand/logo-mono.svg` | Single-colour print, embossing, partner co-marks, dark inversions | Reproduce the brand where colour is forbidden | Stripped, structural, no chrome — engineering-honest |
| Favicon | `brand/favicon.svg` | Browser tab, PWA tile, OS bookmarks | Locate the open ShadowBlade tab in a crowded window | 32-square shield mark — readable at 16×16, glows at 64×64 |
| OpenGraph card | `brand/og-image.svg` | `<meta property="og:image">` on landing + dashboard, LinkedIn, X, Slack unfurls | Stop the scroll and read one claim | 1200×630 hero — gradient headline, pipeline ring, ETA chip; reads in under 2 seconds |
| Voice & tone | `brand/voice-and-tone.md` | Writing kit for Marketing, Sales, CS, Eng changelogs | Draft on-brand copy without a review loop | Plainspoken operator voice; do/avoid table; six drop-in lines |

## Hero / social

| Asset | Path | Placement | User action | Vibe / aesthetic |
| --- | --- | --- | --- | --- |
| Hero cover | `hero/hero-cover.svg` | Landing page `og:image` (16:9), paid social, blog hero, deck cover slide | Read the promise, see the pipeline, click | 1600×900 cinematic dark cockpit — orbit ring, four step cards, live "ETA 64s" chip; same visual language as the landing hero but framed for share |

## Project thumbnails (1080×608, ~5:3 — readable at 240×135)

| Project | Path | Placement | User action | Vibe / aesthetic |
| --- | --- | --- | --- | --- |
| Spring launch — Wearable Hub | `thumbnails/wearable-hub.svg` | Dashboard project grid card, project list, launch email hero | Spot the live hero in the queue | Concentric cyan orbit + bright product mark; reads "HUB · SPRING LAUNCH" instantly |
| SE Bootcamp · Onboarding | `thumbnails/bootcamp.svg` | Dashboard card, L&D landing, training library | Recognize the modular course at a glance | Three coloured module cards (mint / sky / violet); progress meters; in-review pill |
| AI Copilot · 60s demo | `thumbnails/copilot.svg` | Dashboard card, sales-collateral cover, demo gallery | Identify the product walkthrough | Concentric ring with orbit nodes + caption card; calm, technical |
| Series C · TikTok teaser | `thumbnails/series-c.svg` | Dashboard card, social grid, PR kit | Read the announcement in a glance | Oversized gradient "Series C" wordmark + 9:16 phone frame; high-contrast, share-ready |
| Helios Logistics · case study | `thumbnails/helios.svg` | Dashboard card, customer story page hero, sales deck | Read the customer name + the metric | Sky-blue sun motif, pull quote card, two KPI badges; editorial-warm |
| GDPR refresher | `thumbnails/gdpr.svg` | Dashboard card, compliance library, internal training portal | Find the compliance module fast | Violet document stack + checklist; serious without being grim |

## Product screens (1600×1000, fullbleed authored SVG — no raster screenshots)

| Screen | Path | Placement | User action | Vibe / aesthetic |
| --- | --- | --- | --- | --- |
| Dashboard | `screens/screen-dashboard.svg` | Landing page "Inside the workspace" section, `/dashboard` og:image, sales deck slide 4, App Store listing | Believe the product is real, locate the daily home screen | Pixel-faithful clone of `dashboard.html` — sidebar, topbar, KPI row, in-flight pipeline, approvals card, project strip; same tokens, same components |
| Studio | `screens/screen-studio.svg` | Marketing "Studio" feature page hero, `/studio` og:image, demo video thumbnail | Understand the composition surface in one frame | Scene strip across top, 9:16 canvas centered, brand-check inspector right, four-track timeline along the bottom with playhead at 0:06 |
| Render queue | `screens/screen-queue.svg` | Pricing / scale page (proof of farm), `/render-queue` og:image, infra one-pager | See the rush job overtake, trust the throughput | Four KPI tiles, filterable table with priority pills (RUSH / HIGH / NORMAL / LOW), worker row with sparklines |

## Suggested HTML wiring

```html
<!-- Favicon (replace existing default in index.html / dashboard.html <head>) -->
<link rel="icon" type="image/svg+xml" href="/showcase/brand/favicon.svg" />

<!-- OpenGraph (per-page; override og:image on dashboard/studio/queue) -->
<meta property="og:image" content="/showcase/brand/og-image.svg" />
<meta property="og:image" content="/showcase/screens/screen-dashboard.svg" /> <!-- on /dashboard -->
<meta property="og:image" content="/showcase/screens/screen-studio.svg" />    <!-- on /studio -->
<meta property="og:image" content="/showcase/screens/screen-queue.svg" />     <!-- on /render-queue -->
<meta property="og:image" content="/showcase/hero/hero-cover.svg" />          <!-- on landing -->
```

> Note for the **Test** ring: every SVG is self-contained (`<defs>` per file, no shared symbols, no remote fonts). Safe to inline into emails or `<img src>`.
> Note for the **Refine** ring: thumbnails were authored against `tokens.css` palette; if you change accent `#22D3B7` you'll want to regen the gradient stops in every file.

## Pass 002 additions

Three new product pages — a Helios customer story, a Login page, and dashboard empty states — needed visuals on-brand with pass 001. All nine new files follow the same rules: self-contained `<defs>`, file-scoped gradient ids (`sb-helios-hero-…`, `sb-login-…`, `sb-empty-*-…`), tokens.css palette, Inter / Inter Display / JetBrains Mono via `font-family=`, no raster, no remote fonts. All files are well under 50 KB (largest is `login-art.svg` at 8.4 KB).

### Case study · `customer-story.html` (Helios Logistics)

| Asset | Path | Placement | User action | Vibe / aesthetic |
| --- | --- | --- | --- | --- |
| Case-study hero | `case-study/helios-hero.svg` | `customer-story.html` hero (1600×900), customer-story `og:image`, sales deck cover slide | Read the headline metric in one breath, scroll for the proof | Editorial-warm dark — sky-blue sun motif top right with rays, gradient headline (38BDF8 → 22D3B7), two KPI badges ("68% faster", "$184k saved"), right-rail mini stat dashboard with Q1 → Q3 bars |
| Pull quote | `case-study/helios-quote.svg` | Customer story mid-page section break (1200×600), social pull, sales deck quote slide | Linger on the customer's verb, trust the source | Oversized `"` glyph at 16% alpha behind 56px Inter Display 600 quote, gradient rule, monogram avatar, Inter 500 small-caps attribution, echo sun mark right side |
| KPI strip | `case-study/helios-metrics.svg` | Customer story KPI band (1200×400), email recap, exec one-pager | Compare three outcomes side-by-side | Three dark cards with file-scoped accent rules — accent (4.8 min · ▼68%), running (+128 cuts with sparkline), review (92% with R1 ring) |

### Auth · `login.html`

| Asset | Path | Placement | User action | Vibe / aesthetic |
| --- | --- | --- | --- | --- |
| Login art | `auth/login-art.svg` | Right rail of `login.html` (900×1200 vertical), invite emails, deck slide for sales | Believe the factory is humming, sign in | Dark cockpit framed vertically — "Sign in to your video factory" heading top, four concentric rings with colour-coded orbit nodes (one per pipeline stage), centered play disk, ETA 64s chip floating top-right, scene strip + composition meter floating, pipeline-stage legend bottom |

### Empty states · 640×360, monochrome-with-accent

| Asset | Path | Placement | User action | Vibe / aesthetic |
| --- | --- | --- | --- | --- |
| No projects | `empty/empty-projects.svg` | Dashboard project grid (zero state), `/projects` empty | Drop a brief and start the first cut | Graphite clapperboard outline, accent (#22D3B7) striped slate corners, "+ New project" CTA chip |
| Library empty | `empty/empty-assets.svg` | `/assets` library zero state, brand kit upload modal | Upload a logo or kit | Three stacked frame outlines fanned diagonally, front frame in `#38BDF8`, dashed `+` upload glyph on the corner |
| Queue clear | `empty/empty-queue.svg` | `/render-queue` when no jobs running, scale-up dashboard | Trust the farm is warm | 4×3 dashed slot grid for 12 workers, one accent (`#22D3B7`) IDLE slot pulsing — restful, not alarming |
| Inbox zero | `empty/empty-inbox.svg` | `/approvals` zero state, notification panel empty | Close the tab, walk away | Bell outline with violet (`#A78BFA`) check inside, soft chime arcs, "INBOX ZERO" status chip |
| No matches | `empty/empty-search.svg` | Global search modal, filtered table zero results | Loosen a filter or rephrase | Magnifier outline with amber (`#FBBF24`) ✕ inside the lens, two dismissable filter chips below to model the unblock |

> Handoff for Test/Refine: empty-state illustrations are deliberately calm (no error red) and each carries a single accent so they ladder into status semantics (`#22D3B7` action, `#38BDF8` running, `#A78BFA` review, `#FBBF24` queued). If Refine adds light theme support, the `<defs>` gradients will need a swap pass — palette stops are inline rather than via tokens.

## Pass 003 additions

Eleven new files for the latest Design wave: 5 language-flag pills, 4 abstract leader portraits, a compare-page header decoration, and a help-centre hero banner. All follow the same rules as 001/002: self-contained `<defs>`, file-scoped gradient ids (`sb-flag-es-grad`, `sb-leader-as-figure`, `sb-compare-before`, `sb-help-lens`, etc.), tokens.css palette only, Inter Display / Inter / JetBrains Mono via `font-family=`, no raster, no remote fonts, no emojis. Largest file is `help/help-hero.svg` at 7.1 KB; flag pills are all ~1–2 KB.

### Language pills · 36×26 (stylised, NOT literal national flags)

| Locale | Path | Placement | User action | Vibe / aesthetic |
| --- | --- | --- | --- | --- |
| Spanish (LATAM) | `flags/es-419.svg` | Language switcher in settings, locale picker in marketing footer, regional ad-targeting UI | Pick the LATAM Spanish locale | Warm orange→yellow→amber gradient, top sheen, Inter Display 700 "ES" centered, 95% white, soft drop shadow |
| German | `flags/de-de.svg` | Language switcher, locale picker, regional dashboard | Pick the de-DE locale | Deep slate/graphite gradient (graphite-500 → graphite-950), sheen, "DE" mark — restrained, engineering-honest |
| Japanese | `flags/ja-jp.svg` | Language switcher, locale picker | Pick the ja-JP locale | Pure white background, one cyan-green accent dot top-right (off-axis from the "JA" mark in navy), drop shadow — minimalist, the most distinctive pill in the row |
| Portuguese (BR) | `flags/pt-br.svg` | Language switcher, locale picker, LATAM dashboard | Pick the pt-BR locale | Accent green → amber gradient, sheen, "PT" mark — tropical, energetic |
| French | `flags/fr-fr.svg` | Language switcher, locale picker, EU dashboard | Pick the fr-FR locale | Stylised diagonal navy / white / red bands (not the literal vertical tricolour), text-stroke on "FR" for legibility on the white band |

### Leader portraits · 256×256 round (abstract silhouettes, no photos)

| Initials | Path | Placement | User action | Vibe / aesthetic |
| --- | --- | --- | --- | --- |
| AS | `leaders/as.svg` | About / leadership page, customer-story author byline, sales deck team slide | Recognise the leader without a photo | Accent gradient (`#2EE2C4` → `#14B59A`), top-left accent-ring, "AS" monogram in deep navy on the silhouette |
| LM | `leaders/lm.svg` | Leadership page, blog post byline, webinar host card | Recognise LM without a photo | Status-running gradient (`#38BDF8` → `#2C528F`), top-right accent-ring, "LM" monogram — diagonal energy mirroring AS |
| JR | `leaders/jr.svg` | Leadership page, council slate, governance doc author | Recognise JR without a photo | Review-violet gradient (`#A78BFA` → `#7C3AED`), bottom-left accent-ring — calmer, review-tinted |
| DM | `leaders/dm.svg` | Leadership page, customer advisory board, sponsor slide | Recognise DM without a photo | Queued-amber → orange gradient (`#FBBF24` → `#EA580C`), bottom-right accent-ring — warm, board-of-directors energy |

### Compare + Help

| Asset | Path | Placement | User action | Vibe / aesthetic |
| --- | --- | --- | --- | --- |
| Compare diff art | `compare/diff-art.svg` | `compare.html` header decoration (800×400), version-diff modal hero | Feel the "before vs after" energy before scrolling into the side-by-side | Two facing waveforms colliding at a centre seam — jittery low-amp running-blue (BEFORE) on the left, smooth high-amp accent-cyan (AFTER) on the right; collision spark + v0…v3 ticks reads as version progression |
| Help centre hero | `help/help-hero.svg` | `help.html` hero banner (1200×500), help search modal background, support email header | Drop straight into the search field | Left rail: gradient headline "Find the answer in one step", search field with `/` shortcut chip, four colour-coded category pills (Pipeline / Review / Billing / API & SDK). Right rail: magnifier with concentric pipeline rings — outer rings colour-coded by stage (running / review / queued / done), tiny "FOUND" indicator inside the lens, "240 GUIDES" floating chip |

> Handoff for Test/Refine: (1) flag pills are 36×26 by design — if Refine wants a larger surface for hover/expanded states, the gradient stops scale cleanly but the locale-code font-size needs a pass. (2) Leader portraits all share the same head+shoulders glyph and vary only by gradient direction + accent ring placement — Refine can clone the pattern for new leaders by changing the four file-scoped gradient stops and the accent position. (3) `compare/diff-art.svg` is decoration only — the actual diff table lives in the page, not in this SVG. (4) `help/help-hero.svg` has a `/` keyboard-shortcut chip in the search field; if Test wants to swap to `⌘K` semantics, only one tspan needs updating. (5) No flag uses a literal national flag for political safety — Refine should keep this constraint for any future locales.
