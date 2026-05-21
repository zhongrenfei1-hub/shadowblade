# ShadowBlade

Enterprise AI short-video generation cloud. Brief → broadcast-ready video in
under five minutes, against your brand kit.

## Stack at a glance

| Layer        | Tech                                           |
| ------------ | ---------------------------------------------- |
| Backend      | FastAPI 0.115 · SQLAlchemy 2 async · Redis     |
| Workers      | Celery (render, TTS, b-roll, compose)          |
| Frontend     | Vanilla HTML + design tokens (Inter / JetBrains Mono) |
| Storage      | S3-compatible object store                     |
| Auth         | SAML SSO + SCIM provisioning                   |

## Surface map (34 pages shipped)

> Full clickable index lives at `sitemap.html`.


### Marketing (public, no auth)

| Route                | Page                                                     |
| -------------------- | -------------------------------------------------------- |
| `index.html`         | Landing — hero pipeline visual, logos, features          |
| `features.html`      | Pipeline walkthrough — Script / Storyboard / Voice / Render |
| `pricing.html`       | 4-tier plans, annual/monthly toggle, feature matrix      |
| `customer-story.html`| Helios case study — hero, KPIs, body, pull-quote, CTA    |
| `gallery.html`       | Customer reel grid from Showcase thumbnails              |
| `changelog.html`     | Date-axis timeline with category pills                   |
| `docs.html`          | Knowledge grid + curl example + Cmd-K search             |
| `security.html`      | Trust badges + 6 pillars + compliance doc table          |
| `status.html`        | Statuspage — 6 services, 60-min tick bars, incidents     |
| `404.html`           | Lost cut — minimal glyph + path echo + workspace nav     |

### Auth + Onboarding

| Route                | Page                                                     |
| -------------------- | -------------------------------------------------------- |
| `login.html`         | SSO-first (Okta · Entra · Google) + email + branded rail |
| `signup.html`        | Split-screen marketing rail + 60-second workspace form   |
| `onboarding.html`    | First-launch wizard — brand kit source picker            |
| `review.html`        | External reviewer signed-share preview surface           |

### Workspace (app shell + sidebar nav)

| Route                  | Page                                                  |
| ---------------------- | ----------------------------------------------------- |
| `dashboard.html`       | KPIs · in-flight pipeline · approvals · projects      |
| `studio.html`          | Scene nav + 9:16 canvas + transport + 4-track timeline + inspector + reviews |
| `projects.html`        | Filter chips + dense project table                    |
| `project-detail.html`  | Cinematic cover + meta + KPIs + version history       |
| `templates.html`       | 8-card template gallery with hover-reveal play        |
| `assets.html`          | Folders + tag filters + drop-zone + content grid      |
| `render-queue.html`    | Cluster utilisation + 4-worker grid + prioritised queue |
| `job-detail.html`      | Gantt timeline + live GPU chart + colour-coded log    |
| `compare.html`         | Side-by-side version diff with change-set list        |
| `analytics.html`       | KPI strip + 7-day bar + leaderboard + drift alerts    |
| `brand-kit.html`       | Kit picker + swatches + type + voice/tone + logo lockups |
| `team.html`            | Members + role/permission matrix + SSO badges         |
| `settings.html`        | General + Render + Security + Billing + API + Toggles |
| `integrations.html`    | 15-card marketplace (Slack/Notion/Figma/YouTube/…)    |
| `audit-log.html`       | Tamper-evident event stream with verb-coded chips     |
| `notifications.html`   | Inbox with category tabs + glyph categories + inline actions |
| `components.html`      | Design system docs — every component in one surface   |
| `new-video.html`       | 4-step create wizard with ETA + smart suggestions     |
| `sitemap.html`         | 34-page categorised link map (auto-generated)         |

## Run locally

```bash
make install        # one-time
make dev            # backend on :8000, frontend on :3000
```

Open `http://localhost:3000` for the marketing landing, then click "Open
workspace" to enter the cockpit. The frontend will hit `/api/v1/projects` on
the backend through the CORS-enabled FastAPI app and gracefully fall back to
local fixture data if the backend is offline.

## Four-ring flywheel

This repo is being built by four concurrent rings:

1. **Design** — backend + UI design system + every workspace page. Six waves shipped (v1 → v6).
2. **Showcase** — brand assets, marketing visuals, product screens, voice spec, empty-state illustrations. Two passes shipped (25 SVGs in `/showcase/`).
3. **Test** — a11y, contrast, copy, responsive, brand consistency audit. Two passes shipped (`docs/test-ring-report-00{1,2}.md`).
4. **Refine** — applies Test findings + wires Showcase assets back in. Two passes shipped (17 + 17 fixes folded back).

Outputs live under `frontend/`, `backend/`, `showcase/`, `docs/`. The cycle
runs concurrently — each ring commits its own work, and rings 2–4 re-trigger
themselves after every Design wave.

## Vibe

Deep navy `#0F2A4A` + graphite `#11161F` + mist `#F7F9FC` + cyan-green accent
`#22D3B7`. Inter Display for display; Inter for body; JetBrains Mono for
numerics. Dark cockpit, instrument-grade typography, status pills as the
universal vocabulary.

See `components.html` for the full design vocabulary in one browsable surface.
