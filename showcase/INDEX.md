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
