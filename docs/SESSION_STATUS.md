# ShadowBlade · Four-ring flywheel · Session status

**Last refresh**: 2026-05-21 (current session)

## Pages shipped · 44

### Marketing · 13
| Route | Surface |
| --- | --- |
| `index.html` | Landing — pipeline hero + 3 features |
| `features.html` | 4-stage walkthrough (Script · Storyboard · Voice · Render) |
| `pricing.html` | 4-tier plans + feature matrix |
| `customer-story.html` | Helios case study |
| `gallery.html` | Customer reel grid from showcase thumbnails |
| `changelog.html` | Date-axis timeline |
| `docs.html` | Knowledge grid + curl quickstart |
| `security.html` | Trust badges + 6 pillars + compliance docs |
| `status.html` | Statuspage — 6 services, 60-min ticks |
| `help.html` | Search + 8 categories + FAQ + contact |
| `about.html` | Manifesto + leadership + press quotes |
| `press-kit.html` | Logos + palette + screenshots + facts |
| `subscribe.html` | Email + RSS + JSON Feed + Slack |

### Auth + Onboarding · 6
| Route | Surface |
| --- | --- |
| `login.html` | SSO-first + email + branded rail |
| `signup.html` | 60-second workspace form |
| `onboarding.html` | First-launch wizard |
| `workspace-switcher.html` | Cmd-K multi-tenant picker |
| `upgrade.html` | In-product upgrade nudge |
| `review.html` | External reviewer signed-share |

### Workspace · 24
| Route | Surface |
| --- | --- |
| `dashboard.html` | KPI + pipeline + approvals + projects |
| `studio.html` | Scenes + canvas + transport + timeline + inspector |
| `projects.html` | Filter table |
| `project-detail.html` | Cover + meta + versions + perf |
| `templates.html` | 8-card gallery |
| `template-detail.html` | Preview + scenes + specs |
| `assets.html` | Folders + tags + grid |
| `asset-detail.html` | Player + metadata + usage table |
| `render-queue.html` | Cluster + workers + priorities |
| `job-detail.html` | Gantt + log stream |
| `compare.html` | Side-by-side version diff |
| `localisation.html` | 5-language variant grid |
| `analytics.html` | KPI + chart + leaderboard + drift |
| `brand-kit.html` | Swatches + type + voice/tone |
| `team.html` | Members + role matrix |
| `settings.html` | General · Render · Security · Billing · API |
| `billing.html` | Plan summary + usage meters + invoices |
| `integrations.html` | 15-card marketplace |
| `dev-console.html` | Webhooks + API keys + replay |
| `audit-log.html` | Verb-coded event stream |
| `notifications.html` | Inbox |
| `components.html` | Design system docs |
| `new-video.html` | 4-step create wizard |
| `sitemap.html` | Linked map of every page |

### Fallback · 1
- `404.html`

## Brand assets · 45 SVGs

- `showcase/brand/` — logo (primary, mono), favicon, OG card, voice spec
- `showcase/hero/` — hero cover for OG / share
- `showcase/thumbnails/` — 6 project covers (wearable, bootcamp, copilot, series-c, helios, gdpr)
- `showcase/screens/` — 3 fullbleed product screens (dashboard, studio, queue)
- `showcase/case-study/` — Helios hero + quote + 3-metric strip
- `showcase/auth/` — login art (vertical rail)
- `showcase/empty/` — 5 empty-state illustrations
- `showcase/flags/` — 5 language pills (ES, DE, JA, PT, FR)
- `showcase/leaders/` — 4 portrait monograms (AS, LM, JR, DM)
- `showcase/compare/` — diff-art header
- `showcase/help/` — help-hero banner

## Four-ring rotations

| Wave | Design | Showcase | Test | Refine |
| --- | --- | --- | --- | --- |
| 1 | landing + dashboard + 8 workspace + 2 settings · 11 pages | 16 SVGs (brand, hero, thumbs, screens, voice) | report-001 (17 findings) | log-002 (17 fixes folded) |
| 2 | 7 entity + 2 marketing + auth · 10 pages | 9 SVGs (case study + login + empties) | report-002 (17 findings) | log-002 (17 fixes folded) |
| 3 | 10 marketing + workspace · 10 pages | 11 SVGs (flags + leaders + compare + help) | report-003 (17 findings) | log-003 (17 fixes folded) |
| 4 | 3 settings + 4 longtail · 7 pages | (rotation 4 in flight) | (Test v4 in flight) | (Refine v4 in flight) |

## Backend (FastAPI)

`backend/app/` — 9 routers (auth, workspaces, projects, jobs, assets, templates, render-queue, brand-kits, analytics, health), 8 models, async SQLAlchemy 2, fixture-backed for frontend development. `make dev` runs both backend (:8000) and frontend (:3000).

## Vibe

Deep navy `#0F2A4A` + graphite `#11161F` + mist `#F7F9FC` + cyan-green accent
`#22D3B7`. Inter Display / Inter / JetBrains Mono. Dark cockpit, instrument-grade typography, status pills as the universal vocabulary.

See `components.html` for the design vocabulary in one browsable surface.
